package main

import (
	"context"
	"encoding/csv"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/feature/s3/transfermanager"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"gopkg.in/yaml.v3"
)

// ── Config structs ──────────────────────────────────────────────────────────
type BucketConfig struct {
	Bronze     string `yaml:"bronze"`
	Silver     string `yaml:"silver"`
	Quarantine string `yaml:"quarantine"`
}

type PipelineConfig struct {
	Storage BucketConfig `yaml:"storage"`
}

func loadBucketConfig() (BucketConfig, error) {
	cfgPath := os.Getenv("PIPELINE_CONFIG_PATH")
	if cfgPath == "" {
		// Fallback: cari di beberapa kemungkinan lokasi
		candidates := []string{
			"config/pipeline-config.yaml",
			"../../config/pipeline-config.yaml",
			"/opt/airflow/config/pipeline-config.yaml",
		}
		for _, p := range candidates {
			if _, err := os.Stat(p); err == nil {
				cfgPath = p
				break
			}
		}
	}
	if cfgPath == "" {
		return BucketConfig{}, fmt.Errorf("tidak menemukan pipeline-config.yaml. Set env PIPELINE_CONFIG_PATH")
	}
	data, err := os.ReadFile(cfgPath)
	if err != nil {
		return BucketConfig{}, fmt.Errorf("baca file config: %w", err)
	}
	var cfg PipelineConfig
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return BucketConfig{}, fmt.Errorf("parse yaml: %w", err)
	}
	return cfg.Storage, nil
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

type QueryFileName struct {
	Query    string
	FileName string
	Header   []string
	Args     []interface{}
	IsMaster bool // Tambahkan flag untuk membedakan perlakuan S3 Key dan Loop
}

func InitS3Client(ctx context.Context) (*s3.Client, error) {
	cfg, err := config.LoadDefaultConfig(ctx, config.WithRegion("ap-southeast-1"))
	if err != nil {
		return nil, err
	}
	return s3.NewFromConfig(cfg), nil
}

type DBPool interface {
	Query(ctx context.Context, sql string, args ...interface{}) (pgx.Rows, error)
}

func newPool(ctx context.Context, connStr string) *pgxpool.Pool {
	dbConfig, err := pgxpool.ParseConfig(connStr)
	if err != nil {
		log.Fatalf("Gagal parse config: %v", err)
	}
	pool, err := pgxpool.NewWithConfig(ctx, dbConfig)
	if err != nil {
		log.Fatalf("Gagal membuat connection pool: %v", err)
	}
	log.Printf("Berhasil membuat connection pool ke database")
	return pool

}

func main() {
	ctx := context.Background()
	startTime := time.Now()

	// =========================================================================
	// CLI ARGUMENTS — Parsing tanggal start & cutoff
	//   - Tanpa argumen           → hari ini (today)
	//   - 1 argumen (--date)      → tanggal tersebut (start == cutoff)
	//   - 2 argumen (--start-date & --end-date) → range tanggal
	// =========================================================================
	var (
		startDateStr string
		endDateStr   string
		singleDate   string
	)
	flag.StringVar(&singleDate, "date", "", "Tanggal tunggal (YYYY-MM-DD). Jika diisi, --start-date dan --end-date diabaikan.")
	flag.StringVar(&startDateStr, "start-date", "", "Tanggal mulai (YYYY-MM-DD)")
	flag.StringVar(&endDateStr, "end-date", "", "Tanggal selesai (YYYY-MM-DD)")
	flag.Parse()

	today := time.Now().UTC().Truncate(24 * time.Hour)

	var startDate, cutoffDate time.Time

	switch {
	case singleDate != "":
		// 1 argumen: jalankan untuk hari itu saja
		parsed, err := time.Parse("2006-01-02", singleDate)
		if err != nil {
			log.Fatalf("Format --date tidak valid: %v. Gunakan YYYY-MM-DD", err)
		}
		startDate = parsed
		cutoffDate = parsed

	case startDateStr != "" && endDateStr != "":
		// 2 argumen: range tanggal
		var err error
		startDate, err = time.Parse("2006-01-02", startDateStr)
		if err != nil {
			log.Fatalf("Format --start-date tidak valid: %v. Gunakan YYYY-MM-DD", err)
		}
		cutoffDate, err = time.Parse("2006-01-02", endDateStr)
		if err != nil {
			log.Fatalf("Format --end-date tidak valid: %v. Gunakan YYYY-MM-DD", err)
		}

	case startDateStr != "" && endDateStr == "":
		// Hanya --start-date diisi → jalankan untuk hari itu saja
		parsed, err := time.Parse("2006-01-02", startDateStr)
		if err != nil {
			log.Fatalf("Format --start-date tidak valid: %v. Gunakan YYYY-MM-DD", err)
		}
		startDate = parsed
		cutoffDate = parsed

	default:
		// Tanpa argumen → hari ini
		startDate = today
		cutoffDate = today
	}

	log.Printf("Rentang incremental load: %s → %s",
		startDate.Format("2006-01-02"), cutoffDate.Format("2006-01-02"))

	dbHost := getEnv("PG_HOST", "localhost")
	dbPort := getEnv("PG_PORT", "5432")
	connStr := fmt.Sprintf("postgres://replicator_user:supersecretpassword@%s:%s/main_db?sslmode=disable", dbHost, dbPort)
	pool := newPool(ctx, connStr)
	defer pool.Close()

	// Load bucket config dari YAML
	bucketConfig, err := loadBucketConfig()
	if err != nil {
		log.Fatalf("Gagal load bucket config: %v", err)
	}
	log.Printf("Bucket bronze: %s", bucketConfig.Bronze)

	s3Client, err := InitS3Client(ctx)
	if err != nil {
		log.Fatalf("Gagal inisialisasi S3: %v", err)
	}

	bucket_name := bucketConfig.Bronze

	// =========================================================================
	// MASTER DATA — Flat load (tanpa partisi), cukup sekali
	// =========================================================================
	log.Printf("━━━ Memuat master data (flat) ━━━")

	master_queries := []QueryFileName{
		{
			Query: "SELECT menu_id, menu_name, category, CAST(base_price AS VARCHAR), CAST(price_tier_1 AS VARCHAR), " +
				"CAST(price_tier_2 AS VARCHAR), CAST(price_tier_3 AS VARCHAR), CAST(is_promo_active AS VARCHAR), CAST(updated_at AS VARCHAR) FROM menu_master",
			FileName: "menu_master.csv",
			Header:   []string{"menu_id", "menu_name", "category", "base_price", "price_tier_1", "price_tier_2", "price_tier_3", "is_promo_active", "updated_at"},
			IsMaster: true,
		},
		{
			Query:    "SELECT outlet_id, outlet_name, city, region_tier, CAST(created_at AS VARCHAR), CAST(updated_at AS VARCHAR) FROM outlet_master",
			FileName: "outlet_master.csv",
			Header:   []string{"outlet_id", "outlet_name", "city", "region_tier", "created_at", "updated_at"},
			IsMaster: true,
		},
	}

	for _, q := range master_queries {
		executeStreamingUpload(ctx, pool, s3Client, bucket_name, "", q)
	}

	// =========================================================================
	// PARSED 2: LOOP INCREMENTAL TRANSAKSI (Dipisah per partisi Hive)
	// =========================================================================
	for d := startDate; !d.After(cutoffDate); d = d.AddDate(0, 0, 1) {
		partitionPrefix := fmt.Sprintf("year=%d/month=%02d/day=%02d", d.Year(), d.Month(), d.Day())
		log.Printf("━━━ [%s] Memproses partition: %s ━━━", d.Format("2006-01-02"), partitionPrefix)

		tx_queries := []QueryFileName{
			{
				Query: "SELECT order_id, outlet_id, cashier_id, CAST(total_amount AS VARCHAR), payment_method, CAST(created_at AS VARCHAR) " +
					"FROM orders WHERE created_at::date = $1",
				FileName: "orders.csv",
				Header:   []string{"order_id", "outlet_id", "cashier_id", "total_amount", "payment_method", "created_at"},
				Args:     []interface{}{d.Format("2006-01-02")},
				IsMaster: false,
			},
			{
				Query: "SELECT oi.item_id, oi.order_id, oi.menu_id, oi.quantity, CAST(oi.price_per_item AS VARCHAR), CAST(oi.subtotal AS VARCHAR) " +
					"FROM order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE o.created_at::date = $1",
				FileName: "order_items.csv",
				Header:   []string{"item_id", "order_id", "menu_id", "quantity", "price_per_item", "subtotal"},
				Args:     []interface{}{d.Format("2006-01-02")},
				IsMaster: false,
			},
		}

		for _, q := range tx_queries {
			executeStreamingUpload(ctx, pool, s3Client, bucket_name, partitionPrefix, q)
		}
	}

	fmt.Printf("\n======================================================\n")
	fmt.Printf("=== SUCCESS: ALL STREAMING BATCH INGESTION COMPLETE ===\n")
	fmt.Printf("Total Waktu Eksekusi: %.2f s\n", time.Since(startTime).Seconds())
	fmt.Printf("======================================================\n")
}

// queryAndWriteCSV — Eksekusi query DB lalu tulis hasilnya sebagai CSV ke writer.
// Fungsi ini reusable: dipakai production (streaming ke S3) dan integration test (streaming ke file/buffer).
func queryAndWriteCSV(ctx context.Context, pool DBPool, q QueryFileName, w io.Writer) (int, error) {
	rows, err := pool.Query(ctx, q.Query, q.Args...)
	if err != nil {
		return 0, fmt.Errorf("query error: %w", err)
	}
	defer rows.Close()

	writer := csv.NewWriter(w)

	if err := writer.Write(q.Header); err != nil {
		return 0, fmt.Errorf("header write error: %w", err)
	}

	var totalRows int = 0
	for rows.Next() {
		values, err := rows.Values()
		if err != nil {
			return totalRows, fmt.Errorf("scan error at row %d: %w", totalRows, err)
		}

		row := make([]string, len(values))
		for i, val := range values {
			row[i] = fmt.Sprintf("%v", val)
		}

		if err := writer.Write(row); err != nil {
			return totalRows, fmt.Errorf("csv write error at row %d: %w", totalRows, err)
		}
		totalRows++
	}

	writer.Flush()
	return totalRows, nil
}

// executeStreamingUpload — Tarik data dari DB → streaming CSV → upload ke S3
func executeStreamingUpload(ctx context.Context, pool DBPool, s3Client *s3.Client, bucket, prefix string, q QueryFileName) error {
	pr, pw := io.Pipe()

	go func() {
		_, err := queryAndWriteCSV(ctx, pool, q, pw)
		if err != nil {
			log.Printf("Gagal query & tulis CSV: %v", err)
			pw.CloseWithError(err)
		} else {
			pw.Close()
		}
	}()

	tableName := strings.TrimSuffix(q.FileName, ".csv")

	var key string
	if q.IsMaster {
		// Flat path — tanpa partisi (master data)
		key = fmt.Sprintf("%s/%s", tableName, q.FileName)
	} else {
		// Hive partition: table_name/year=YYYY/month=MM/day=DD/table_name.csv
		key = fmt.Sprintf("%s/%s/%s", tableName, prefix, q.FileName)
	}

	uploader := transfermanager.New(s3Client, func(o *transfermanager.Options) {
		o.PartSizeBytes = 32 * 1024 * 1024
		o.Concurrency = 3
	})

	_, err := uploader.UploadObject(ctx, &transfermanager.UploadObjectInput{
		Bucket: &bucket,
		Key:    &key,
		Body:   pr,
	})
	if err != nil {
		log.Fatalf("Gagal upload %s ke S3: %v", key, err)
	}
	log.Printf("✓ Sukses streaming upload: s3://%s/%s", bucket, key)
	return nil
}
