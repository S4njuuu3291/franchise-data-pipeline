package main

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/testcontainers/testcontainers-go"
	"github.com/testcontainers/testcontainers-go/modules/postgres"
	"github.com/testcontainers/testcontainers-go/wait"
)

func getTestDSN() string {
	dsn := os.Getenv("DB_TEST_DSN")
	if dsn == "" {
		return "postgres://replicator_user:supersecretpassword@localhost:5432/main_db?sslmode=disable"
	}
	return dsn
}

func TestIntegration_DBConnection(t *testing.T) {
	if testing.Short() {
		t.Skip("skip integration test")
	}

	ctx := context.Background()
	pool, err := pgxpool.New(ctx, getTestDSN())
	if err != nil {
		require.NoError(t, err, "gagal buat pool")
	}
	defer pool.Close()

	err = pool.Ping(ctx)
	assert.NoError(t, err, "gagal ping db")
}

func TestIntegration_QueryColumnCount(t *testing.T) {
	if testing.Short() {
		t.Skip("skip integration test")
	}

	ctx := context.Background()
	pool, err := pgxpool.New(ctx, getTestDSN())
	if err != nil {
		t.Fatalf("gagal buat pool: %v", err)
	}
	defer pool.Close()

	tests := []struct {
		name     string
		query    string
		args     []interface{}
		wantCols int
	}{
		{
			name: "menu_master",
			query: "SELECT menu_id, menu_name, category, CAST(base_price AS VARCHAR), " +
				"CAST(price_tier_1 AS VARCHAR), CAST(price_tier_2 AS VARCHAR), " +
				"CAST(price_tier_3 AS VARCHAR), CAST(is_promo_active AS VARCHAR), " +
				"CAST(updated_at AS VARCHAR) FROM menu_master LIMIT 1",
			wantCols: 9,
		},
		{
			name:     "orders incremental",
			query:    "SELECT order_id, outlet_id, cashier_id, CAST(total_amount AS VARCHAR), payment_method, CAST(created_at AS VARCHAR) FROM orders WHERE created_at::date = $1 LIMIT 1",
			args:     []interface{}{"2026-03-02"},
			wantCols: 6,
		},
		{
			name: "order_items incremental via join",
			query: "SELECT oi.item_id, oi.order_id, oi.menu_id, oi.quantity, " +
				"CAST(oi.price_per_item AS VARCHAR), CAST(oi.subtotal AS VARCHAR) " +
				"FROM order_items oi JOIN orders o ON oi.order_id = o.order_id " +
				"WHERE o.created_at::date = $1 LIMIT 1",
			args:     []interface{}{"2026-03-02"},
			wantCols: 6,
		},
		{
			name:     "outlet_master",
			query:    "SELECT outlet_id, outlet_name, city, region_tier, CAST(created_at AS VARCHAR), CAST(updated_at AS VARCHAR) FROM outlet_master LIMIT 1",
			wantCols: 6,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rows, err := pool.Query(ctx, tt.query, tt.args...)
			require.NoError(t, err, "query error")
			defer rows.Close()

			for rows.Next() {
				values, err := rows.Values()
				require.NoError(t, err, "scan error")
				assert.Len(t, values, tt.wantCols)
			}
		})
	}
}

func TestIntegration_DBHasData(t *testing.T) {
	if testing.Short() {
		t.Skip("skip integration test")
	}

	ctx := context.Background()
	pool, err := pgxpool.New(ctx, getTestDSN())
	if err != nil {
		t.Fatalf("gagal buat pool: %v", err)
	}
	defer pool.Close()

	tables := []string{"menu_master", "outlet_master", "orders", "order_items"}
	for _, table := range tables {
		t.Run(fmt.Sprintf("table_%s_has_rows", table), func(t *testing.T) {
			var count int
			err := pool.QueryRow(ctx, fmt.Sprintf("SELECT COUNT(*) FROM %s", table)).Scan(&count)
			require.NoError(t, err, "count error")
			assert.Greater(t, count, 0, "table %s is empty", table)
			t.Logf("  %s: %d rows", table, count)
		})
	}
}

func TestQueryAndWriteCSV(t *testing.T) {
	if testing.Short() {
		t.Skip("skip integration test")
	}

	ctx := context.Background()
	pgContainer, err := postgres.Run(ctx,
		"postgres:15-alpine",
		postgres.WithDatabase("test_db"),
		postgres.WithUsername("test_user"),
		postgres.WithPassword("test_password"),
		// Tunggu sampai Postgres benar-benar siap menerima koneksi sebelum test dimulai
		testcontainers.WithWaitStrategy(
			wait.ForLog("database system is ready to accept connections").
				WithOccurrence(2).
				WithStartupTimeout(30*time.Second)),
	)

	assert.NoError(t, err)

	// Wajib dipanggil di akhir agar container hancur otomatis setelah test selesai
	defer func() {
		err := pgContainer.Terminate(ctx)
		assert.NoError(t, err)
	}()

	// 2. AMBIL CONNECTION STRING DINAMIS DARI CONTAINER
	connStr, err := pgContainer.ConnectionString(ctx, "sslmode=disable")
	assert.NoError(t, err)

	// 3. BUAT KONEKSI NYATA MENGGUNAKAN PGXPOOL ASLI
	pool, err := pgxpool.New(ctx, connStr)
	assert.NoError(t, err)
	defer pool.Close()

	// 4. SETUP DATA NYATA: Buat tabel dan isi data langsung ke container docker tadi
	_, err = pool.Exec(ctx, `
		CREATE TABLE orders (order_id SERIAL PRIMARY KEY, outlet_id INTEGER, cashier_id INTEGER, total_amount NUMERIC(14,2), payment_method VARCHAR(30), created_at TIMESTAMP);
		INSERT INTO orders (outlet_id, cashier_id, total_amount, payment_method, created_at) VALUES
		(1, 101, 250.00, 'cash', '2026-03-02 10:00:00'),
		(2, 102, 150.50, 'credit_card', '2026-03-02 11:00:00');
	`)
	assert.NoError(t, err)

	q := QueryFileName{
		Query:    "SELECT order_id, outlet_id, cashier_id, CAST(total_amount AS VARCHAR), payment_method, CAST(created_at AS VARCHAR) FROM orders WHERE created_at::date = $1",
		FileName: "orders/orders_2026-03-02.csv",
		Header:   []string{"order_id", "outlet_id", "cashier_id", "total_amount", "payment_method", "created_at"},
		Args:     []interface{}{"2026-03-02"},
		IsMaster: false,
	}

	var buf bytes.Buffer
	totalRows, err := queryAndWriteCSV(ctx, pool, q, &buf)

	assert.NoError(t, err)
	assert.Equal(t, 2, totalRows)
}
