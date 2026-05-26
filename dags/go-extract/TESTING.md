# Testing — `go-extract`

## Daftar Test

### `main_test.go` — Unit Test (tanpa dependency eksternal)

| Test | Cara Kerja |
|------|-----------|
| `TestS3KeyGeneration_Master` | Verifikasi key untuk tabel master (`menu_master/menu_master.csv`) — tanpa Hive partition |
| `TestS3KeyGeneration_OrdersHivePartition` | Verifikasi key untuk tabel transaksi — format `orders/year=2026/month=03/day=02/orders.csv` |
| `TestS3KeyGeneration_AllMasterTables` | Verifikasi semua tabel master menghasilkan key yang benar |
| `TestCutoffDateLoop` | Verifikasi loop dari `startDate` ke `cutoffDate` menghasilkan 6 hari |
| `TestCutoffDatePartitions` | Verifikasi prefix Hive partition tiap hari dalam rentang tanggal |
| `TestQueryHeaderCount` | Verifikasi jumlah kolom header CSV sesuai dengan query SQL |

> **Jalankan:** `make go-test` atau `go test -v -short`

---

### `integration_test.go` — Integration Test (butuh DB PostgreSQL running)

Test ini terkoneksi langsung ke database `main_db` untuk memverifikasi query SQL berjalan dengan benar.

#### `TestIntegration_DBConnection`
- **Tujuan:** Pastikan koneksi ke PostgreSQL berhasil
- **Cara kerja:** Buat `pgxpool`, lalu `Ping()` ke database
- **Gagal kalau:** DB mati, credential salah, atau network blok

#### `TestIntegration_QueryColumnCount`
- **Tujuan:** Pastikan setiap query mengembalikan jumlah kolom yang sesuai dengan header CSV
- **Cara kerja:** Eksekusi tiap query (`menu_master`, `orders`, `order_items`, `outlet_master`) dengan `LIMIT 1`, lalu hitung `len(values)` dari hasil `rows.Values()`
- **Gagal kalau:** Query berubah (kolom ditambah/dihapus) tapi `Header` di struct tidak diupdate
- **Rincian per query:**
  - `menu_master` → 9 kolom (menu_id s.d. updated_at)
  - `orders incremental` → 6 kolom, pakai `WHERE created_at::date = $1` (parameterized)
  - `order_items incremental` → 6 kolom, JOIN dengan `orders`, filter via `o.created_at::date = $1`
  - `outlet_master` → 6 kolom (outlet_id s.d. updated_at)

#### `TestIntegration_DBHasData`
- **Tujuan:** Pastikan tabel tidak kosong sebelum ekstraksi
- **Cara kerja:** `SELECT COUNT(*)` dari tiap tabel (`menu_master`, `outlet_master`, `orders`, `order_items`)
- **Gagal kalau:** Data generator belum dijalankan, atau tabel di-truncate
- **Note:** Menampilkan jumlah row tiap tabel di log

> **Jalankan:** `make go-test-all` atau `go test -v`
>
> **Catatan:** Test ini di-skip otomatis kalau pakai `-short`.

---

## Cara Eksekusi

```bash
# 1. Pastikan docker services running
make docker-up

# 2. Inject schema & generate data
make init-schema
cd data-generator && python seed-master.py && cd ..
cd data-generator && python run_all_simulations.py && cd ..

# 3. Unit test
make go-test

# 4. Integration test (butuh DB running)
make go-test-all

# 5. Coverage
make go-test-cover
```
