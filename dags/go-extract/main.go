package main

import (
	"context"
	"crypto/tls"
	"encoding/csv"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/feature/s3/transfermanager"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type QueryFileName struct {
	Query    string
	FileName string
	Header   []string
	Args     []interface{}
	IsMaster bool // Tambahkan flag untuk membedakan perlakuan S3 Key dan Loop
}

func InitS3Client(ctx context.Context, useMinIO bool) (*s3.Client, error) {
	if useMinIO {
		cfg, err := config.LoadDefaultConfig(ctx,
			config.WithBaseEndpoint("http://localhost:9000"),
			config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider("minioadmin", "minioadmin", "")),
			config.WithRegion("ap-southeast-1"),
		)
		if err != nil {
			return nil, err
		}

		tr := &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		}
		client := s3.NewFromConfig(cfg, func(o *s3.Options) {
			o.HTTPClient = &http.Client{Transport: tr}
			o.UsePathStyle = true
		})
		return client, nil
	}

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

	connStr := "postgres://replicator_user:supersecretpassword@localhost:5432/main_db?sslmode=disable"
	pool := newPool(ctx, connStr)
	defer pool.Close()

	startDate := time.Date(2026, 2, 25, 0, 0, 0, 0, time.UTC)
	cutoffDate := time.Date(2026, 2, 25, 0, 0, 0, 0, time.UTC)
	log.Printf("Rentang incremental load: %s → %s",
		startDate.Format("2006-01-02"), cutoffDate.Format("2006-01-02"))

	s3Client, err := InitS3Client(ctx, true)
	if err != nil {
		log.Fatalf("Gagal inisialisasi S3: %v", err)
	}

	bucket_name := "franchise-pipeline-data-lake-bronze"

	// =========================================================================
	// PARSED 1: AMBIL DATA MASTER (Hanya diekstrak sekali, flat di S3 root)
	// =========================================================================
	master_queries := []QueryFileName{
		{
			Query: "SELECT menu_id, menu_name, category, CAST(base_price AS VARCHAR), CAST(price_tier_1 AS VARCHAR), " +
				"CAST(price_tier_2 AS VARCHAR), CAST(price_tier_3 AS VARCHAR), CAST(is_promo_active AS VARCHAR), CAST(updated_at AS VARCHAR) FROM menu_master",
			FileName: "menu_master/menu_master.csv", // Folder mandiri
			Header:   []string{"menu_id", "menu_name", "category", "base_price", "price_tier_1", "price_tier_2", "price_tier_3", "is_promo_active", "updated_at"},
			IsMaster: true,
		},
		{
			Query:    "SELECT outlet_id, outlet_name, city, region_tier, CAST(created_at AS VARCHAR), CAST(updated_at AS VARCHAR) FROM outlet_master",
			FileName: "outlet_master/outlet_master.csv", // Folder mandiri
			Header:   []string{"outlet_id", "outlet_name", "city", "region_tier", "created_at", "updated_at"},
			IsMaster: true,
		},
	}

	log.Println("━━━ Memproses Sinkronisasi Data Master ━━━")
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
					"FROM orders WHERE created_at::date = $1 LIMIT 1000", // Menggunakan format date matching cast
				FileName: "orders.csv",
				Header:   []string{"order_id", "outlet_id", "cashier_id", "total_amount", "payment_method", "created_at"},
				Args:     []interface{}{d.Format("2006-01-02")},
				IsMaster: false,
			},
			{
				Query: "SELECT oi.item_id, oi.order_id, oi.menu_id, oi.quantity, CAST(oi.price_per_item AS VARCHAR), CAST(oi.subtotal AS VARCHAR) " +
					"FROM order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE o.created_at::date = $1 LIMIT 1000",
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

	var key string
	if q.IsMaster {
		key = q.FileName // e.g., menu_master/menu_master.csv
	} else {
		// Hive partition: table_name/year=YYYY/month=MM/day=DD/table_name.csv
		tableName := strings.TrimSuffix(q.FileName, ".csv")
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
