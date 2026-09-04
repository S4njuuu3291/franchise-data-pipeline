# Reliability Test Results

## RT-001 — Normal Run

- **Scenario:** Menjalankan pipeline untuk satu tanggal baru
- **Logical date:** `2026-05-01`
- **Airflow run ID:** `manual__2026-08-10T13:34:16.888540+00:00`
- **Tasks executed:**
  - `extract_data`
  - `process_silver`
  - `build_gold`

### Expected

- Bronze untuk `date=2026-05-01` berhasil dibuat
- Silver untuk `date=2026-05-01` berhasil dibuat
- Gold berhasil dibuat
- Tidak ada duplicate record
- dbt tests passed

### Actual Result

- Bronze: `PASS` — partition `orders/year=2026/month=05/day=01/` tersedia
- Silver: `PASS` — partition `orders/year=2026/month=05/day=01/` tersedia
- Gold: `PASS` — `fact_order_items` berisi `105770` rows
- Orders: `PASS` — query `SELECT * FROM orders` menghasilkan `46101` rows
- Duplicate: `PASS` — tidak ditemukan
- Quarantine: `PASS` — tersedia
- dbt tests: `PASS`

### Status

`PASS`

### Notes

Pipeline berhasil diproses dari Bronze sampai Gold untuk logical date
`2026-05-01`. Data orders tersedia di Bronze dan Silver, sedangkan model
Gold `fact_order_items` menghasilkan `105770` rows.

## RT-002 — Rerun Same Date

- **Scenario:** Menjalankan ulang pipeline untuk tanggal yang sama
- **Logical date:** `2026-05-01`
- **Airflow run ID:** `manual__2026-08-10T13:34:16.888540+00:00`
- **Rerun ID:** `manual__2026-08-10T13:34:16.888540+00:00`
- **Tasks executed:**
  - `extract_data`
  - `process_silver`
  - `build_gold`

### Comparison

| Evidence | Before rerun | After rerun | Result |
|---|---:|---:|---|
| Bronze row count | 46101 orders | 46101 orders | PASS |
| Silver row count | 46101 orders | 46101 orders | PASS |
| Gold row count | 105770 fact rows | 105770 fact rows | PASS |
| Bronze partitions | `orders/year=2026/month=05/day=01/` | `orders/year=2026/month=05/day=01/` | PASS |
| Silver partitions | `orders/year=2026/month=05/day=01/` | `orders/year=2026/month=05/day=01/` | PASS |
| Duplicate records | Tidak ada | Tidak ada | PASS |
| Quarantine records | Ada | Ada | PASS |
| dbt tests | PASS | PASS | PASS |

### Expected

Rerun tanggal `2026-05-01` mengganti output tanggal tersebut,
bukan menambah data atau partition baru.

### Status

`PASS`

### Notes

Tulis perbedaan yang ditemukan. Kalau tidak ada perbedaan, tulis:

> Output sebelum dan sesudah rerun tetap konsisten. Tidak ditemukan
> duplicate record maupun partition tambahan.
