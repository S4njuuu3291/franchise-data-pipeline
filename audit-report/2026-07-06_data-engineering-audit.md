# Audit Data Engineering — Franchise Data Pipeline

**Tanggal:** 2026-07-06
**Proyek:** `04-franchise-data-pipeline`
**Tipe Audit:** Full (7 Dimensi)
**Auditor:** GitHub Copilot (DeepSeek V4 Flash)

---

## Ringkasan Eksekutif

Proyek **Franchise Data Pipeline** adalah pipeline ETL end-to-end yang sangat baik untuk level portfolio. Arsitektur Medallion (Bronze → Silver → Gold) diimplementasikan dengan bersih menggunakan tech stack modern: **Go → AWS Glue (PySpark) → dbt + Athena**, diorkestrasi oleh **Apache Airflow 3.2.1**.

| Dimensi | Skor | Status |
|---|---|---|
| 1. Pipeline Architecture & Design | **9/10** | ✅ Best Practice |
| 2. Data Modeling | **8.5/10** | ✅ Best Practice |
| 3. Code Quality & Maintainability | **9/10** | ✅ Best Practice |
| 4. Data Quality & Testing | **7/10** | ⚠️ Needs Improvement |
| 5. Security & Compliance | **6/10** | ⚠️ Needs Improvement |
| 6. Performance & Scalability | **8/10** | ✅ Best Practice |
| 7. Documentation & Observability | **7.5/10** | ✅ Best Practice |
| **Overall** | **7.9/10** | **Siap Produksi dengan Catatan** |

---

## 1. Pipeline Architecture & Design — 9/10

### Sub-item Assessment

| # | Item | Nilai | Detail |
|---|---|---|---|
| 1.1 | Modularity — Extract, Transform, Load terpisah | ✅ | Go extractor (`dags/go-extract/main.go`), Glue transform (`dags/spark-transform/transform_glue.py`), dbt modeling (`dbt_pipeline/`) — komponen independen |
| 1.2 | ELT paradigm — Load raw dulu, baru transform | ✅ | Bronze = CSV mentah → Silver = Parquet divalidasi → Gold = Star schema via dbt. ELT murni. |
| 1.3 | Idempotency — Re-run tanpa duplikasi | ✅ | `mode("overwrite")` di Spark untuk master. Insert-overwrite incremental di dbt `fact_order_items`. Go extractor ganti file per partisi. |
| 1.4 | Backfill capability — Proses historical data | ✅ | Go extractor dukung `--start-date` & `--end-date` (baris 60-80 `main.go`). Glue transform juga dukung date range. |
| 1.5 | Orchestration — Workflow definition | ✅ | Satu DAG `sales_data_dbt_pipeline` dengan task chain jelas: `start → extract → transform → dbt → end`. CeleryExecutor. |

### Strengths
- **Streaming upload** ke S3 via `io.Pipe()` di Go — tanpa file intermediate, sangat efisien.
- **Primary-Replica PostgreSQL** — extract dari replica, beban transaksional tidak terganggu.
- **Task dependency jelas** di DAG — visual graph yang mudah dipahami.

### Critical Findings
- **Tidak ada.** Arsitektur sudah sangat matang.

### Recommendations
- ❌ *Minor:* Pertimbangkan menambah `depends_on_past=True` untuk mencegah DAG tumpang tindih jika pipeline harian molor.

---

## 2. Data Modeling — 8.5/10

### Sub-item Assessment

| # | Item | Nilai | Detail |
|---|---|---|---|
| 2.1 | Grain definition — Tiap table punya grain jelas | ✅ | `fact_order_items` grain = item_id. `dim_date` grain = date. `dim_menu` grain = menu_id + row_start_date (SCD). |
| 2.2 | Business key — Unique key teridentifikasi | ✅ | `order_id`, `menu_id`, `outlet_id`, `item_id` semua jelas. |
| 2.3 | SCD — Dimensional data pakai SCD type tepat | ✅ | **SCD Type 2** via dbt snapshots untuk `menu_master` dan `outlet_master` (`dbt_pipeline/snapshots/`). Flag `is_current_active` ditambahkan. |
| 2.4 | Normalization balance — Sesuai use case | ⚠️ | Staging views (`stg_orders`, `stg_order_items`) hanya `SELECT *` tanpa transformasi — bisa diperkaya. `fact_order_items` mengandung denormalized fields (total_amount, payment_method) — tepat untuk fact table. |
| 2.5 | Surrogate keys — Digunakan tepat | ⚠️ | Tidak ada surrogate keys di dimension tables. Natural keys digunakan langsung. Acceptable karena source ID integer stabil, tapi best practice menggunakan surrogate key untuk ketahanan referensi. |

### Strengths
- **SCD Type 2 dengan snapshot** — implementasi yang benar menggunakan `updated_at` timestamp, `dbt_valid_from`/`dbt_valid_to`.
- **Dim_date** — lengkap dengan year, month, day, quarter, week, day_of_week, day_name, month_name, weekend flag.
- **Enrichment** di `dim_menu` — category_group, price_segment, promo_status. Memudahkan analisis BI.

### Critical Findings
- **⚠️ Staging views terlalu tipis** (`dbt_pipeline/models/staging/stg_orders.sql`, `stg_order_items.sql`). Hanya `SELECT *` tanpa casting, filtering, atau cleansing. Meskipun valid untuk ELT, ini missed opportunity untuk data quality checks di layer staging.

### Recommendations
1. **Tambah surrogate keys** (`dim_menu_sk`, `dim_outlet_sk`) di dimension tables untuk referensi yang lebih stabil.
2. **Enrich staging views** — tambahkan casting tipe data, filtering null, dan kolom audit (loaded_at, source_file).

---

## 3. Code Quality & Maintainability — 9/10

### Sub-item Assessment

| # | Item | Nilai | Detail |
|---|---|---|---|
| 3.1 | Naming conventions — Konsisten & bermakna | ✅ | snake_case konsisten di Go, Python, SQL, dbt. Nama file deskriptif (`transform_glue.py`, `snp_menu_master.sql`). |
| 3.2 | DRY — Tidak ada duplikasi tidak perlu | ✅ | Schema definitions reusable di `modules/schemas.py`. Config YAML dibagikan antara Go dan Python. Fungsi `queryAndWriteCSV` reusable. |
| 3.3 | Comments & docstrings — Business logic terdokumentasi | ✅ | Go code: komentar Bahasa Indonesia jelas. Python: docstring detail di setiap fungsi. dbt YAML: column descriptions lengkap. |
| 3.4 | Modular functions — ETL steps dipisah | ✅ | Go: `queryAndWriteCSV`, `executeStreamingUpload`, `InitS3Client`, `newPool`. PySpark: `bronze_master_to_silver()`, `bronze_to_silver()`, `date_range()`. |
| 3.5 | Meaningful commits | ✅ | Struktur proyek dan file menunjukkan development yang terencana. |

### Strengths
- **Go error handling** — `log.Fatalf` untuk fatal error, error wrapping dengan `%w`.
- **Config YAML terpusat** — `config/pipeline-config.yaml` digunakan bersama Go dan Python (via env var fallback).
- **Go module caching** di `Dockerfile.airflow` — pre-cache Go modules agar `go run` cepat di Airflow.

### Critical Findings
- **Tidak ada major issues.** Code quality sangat baik.

### Recommendations
- ❌ *Minor:* File `transform.py` (lokal) bisa dihapus atau di-refactor menjadi import dari `transform_glue.py` untuk menghindari duplikasi kode.
- ❌ *Minor:* Pertimbangkan type hints di Python untuk parameter fungsi.

---

## 4. Data Quality & Testing — 7/10

### Sub-item Assessment

| # | Item | Nilai | Detail |
|---|---|---|---|
| 4.1 | Validation checks — Nulls, uniqueness, referential integrity | ✅ | **7 validation rules** di Glue transform (`transform_glue.py`): referential integrity (menu_id, outlet_id), payment_method, price tiers, duplicate order_id, cashier anomaly (z-score > 3), total mismatch. **Excellent coverage.** |
| 4.2 | Testing framework — dbt tests, Great Expectations, atau custom | ⚠️ | dbt tests: 8 not_null, 2 unique, 1 relationships, 1 freshness. Coverage terbatas — hanya ~12 tests untuk 8+ models. Tidak ada test untuk snapshots. |
| 4.3 | Freshness monitoring — Cek data staleness | ✅ | Source freshness di `silver_data.orders` (warn: 24h, error: 48h) — terdefinisi di dbt. |
| 4.4 | Row count validation — Ekspektasi volume dicek | ❌ | **Tidak ada** row count validation. Pipeline tidak punya mekanisme untuk alert jika jumlah record drastis berubah. |
| 4.5 | Unit tests — Transformasi di-test dengan subset data | ✅ | Go: unit tests untuk S3 key generation + integration tests dengan testcontainers (`main_test.go`, `integration_test.go`). **Tidak ada** unit tests untuk PySpark transform. |

### Strengths
- **7 validation rules** di Silver layer sangat komprehensif — termasuk statistical anomaly detection (z-score).
- **Go integration tests** menggunakan testcontainers — proper database testing.
- **Quarantine mechanism** — data invalid tetap disimpan untuk investigasi.

### Critical Findings
- **❌ Row count validation** tidak ada. Pipeline bisa sukses tapi data kosong tanpa alert.
- **⚠️ dbt test coverage** masih minimal. Hanya 12 tests untuk pipeline dengan 6+ models.

### Recommendations
1. **Tambah row count check** — di Glue transform, compare row count input vs output, alert jika < 90% ekspektasi.
2. **Ekspansi dbt tests** — minimal tambahkan:
   - `not_null` untuk `dim_outlet.outlet_id`, `dim_menu.menu_id`
   - `unique` test untuk fact grain
   - `accepted_values` untuk `payment_method`, `category`, `region_tier`
   - `relationships` test untuk fact → dim foreign keys
3. **Tambah PySpark unit tests** — gunakan `chispa` library untuk menguji logika transformasi.

---

## 5. Security & Compliance — 6/10

### Sub-item Assessment

| # | Item | Nilai | Detail |
|---|---|---|---|
| 5.1 | Secrets management — Tidak ada hardcoded credentials | ⚠️ | **Hardcoded password** di `dags/go-extract/main.go` baris ~78: `supersecretpassword`. Juga di `data-generator/generate_transactions.py` baris ~37. `.env.example` menunjukkan template yang benar. |
| 5.2 | PII handling — Data sensitif dimasking/dianonimasi | ⚠️ | Tidak ada PII explicit (nama pelanggan, email, dll). Tapi tidak ada masking untuk `outlet_name` atau `cashier_id`. |
| 5.3 | SQL injection — Parameterized queries | ✅ | Go: semua query pakai `$1` placeholders. No string concatenation. |
| 5.4 | Access control — IAM / RBAC | ✅ | Terraform mendefinisikan IAM role Glue dengan least-privilege S3 access. S3 public access blocks diaktifkan. |
| 5.5 | Safe logging — Tidak ada data sensitif di logs | ✅ | Logging hanya untuk metadata (counts, warnings), tidak ada data nilai transaksi atau identitas. |

### Strengths
- **IAM least-privilege** — Glue role hanya punya akses ke bucket yang diperlukan.
- **S3 public access blocks** — semua bucket dikonfigurasi dengan `block_public_acls = true`.
- **Parameterized queries** — aman dari SQL injection.

### Critical Findings
- **❌ Hardcoded password** `supersecretpassword` di source code (Go + Python). Ini **critical** untuk production.
- **⚠️ AWS credentials** di env variables via `.env` — lebih baik gunakan IAM Role untuk EC2/ECS atau IRSA untuk EKS.

### Recommendations
1. **Segera hapus hardcoded password** — gunakan environment variables atau secret manager (AWS Secrets Manager / HashiCorp Vault).
2. **Ganti koneksi DB** di Go extractor: baca dari env vars `PG_PASSWORD`, bukan hardcode.
3. **Implementasi PII classification** — audit data apa yang termasuk PII dan terapkan masking jika diperlukan.
4. **Pertimbangkan AWS IRSA** atau instance profile untuk menggantikan access key di env variables.

---

## 6. Performance & Scalability — 8/10

### Sub-item Assessment

| # | Item | Nilai | Detail |
|---|---|---|---|
| 6.1 | Partitioning — Large tables dipartisi | ✅ | Hive-style partitioning (year/month/day) untuk `orders`, `order_items`. Master data full load (fine untuk ukuran kecil). |
| 6.2 | Join optimization — Complexity bisa dikurangi | ✅ | Spark joins master-to-transaction: master tables di-broadcast (small). Glue job menggunakan Spark SQL optimized. |
| 6.3 | Incremental processing — Full refresh hanya kalau perlu | ✅ | Bronze: extract per tanggal. Silver: proses per partisi. Gold: `insert_overwrite` incremental. |
| 6.4 | Resource efficiency — Optimalisasi resource | ✅ | Go streaming upload (no local buffer). Glue managed resource. Transfer manager dengan `PartSizeBytes=32MB`, `Concurrency=3`. |
| 6.5 | Monitoring — SLA, alerting, query tracking | ⚠️ | Tidak ada monitoring performance yang eksplisit. Hanya logging dasar. Tidak ada query performance tracking atau SLA. |

### Strengths
- **Go streaming upload** — `io.Pipe()` + `transfermanager.UploadObject` = zero intermediate file.
- **Transfer manager optimization** — part size 32MB, concurrency 3.
- **Insert-overwrite incremental** — hanya proses partisi yang berubah, efisien.

### Critical Findings
- **⚠️ No performance monitoring** — tidak ada mekanisme untuk tracking durasi pipeline, data volume per partisi, atau SLA alerting.

### Recommendations
1. **Tambah Airflow SLA monitoring** — gunakan `sla_miss_callback` di DAG.
2. **Implementasi Data Volume Tracking** — catat row count per table per run di monitoring DB atau CloudWatch.
3. **Optimasi dbt** — untuk `fact_order_items` incremental, partition pruning bisa ditingkatkan dengan macro yang lebih dinamis.

---

## 7. Documentation & Observability — 7.5/10

### Sub-item Assessment

| # | Item | Nilai | Detail |
|---|---|---|---|
| 7.1 | README — Jelas cara run, requirements, output | ✅ | README.md sangat komprehensif: tech stack badges, arsitektur, setup instructions, Makefile commands, project structure. |
| 7.2 | Data lineage — Alur dari source → mart | ✅ | Architecture diagram (assets/architecture.png), dbt DAG (assets/dbt-dag.png), ERD (assets/erd.png). Jelas. |
| 7.3 | Data contracts — Ekspektasi antar tim/consumer | ⚠️ | dbt YAML punya column descriptions tapi tidak ada formal data contracts (schema versioning, SLA, owner). |
| 7.4 | Incident plan — Apa dilakukan kalau data error | ❌ | **Tidak ada.** Tidak ada dokumentasi tentang apa yang harus dilakukan jika pipeline error, data discrepancy, atau SLA miss. |
| 7.5 | Schema docs — Deskripsi kolom, tipe data, contoh nilai | ✅ | dbt docs generate (catalog.json, index.html). Column descriptions di YAML. `struktur-oltp.yaml` menjelaskan schema OLTP. |

### Strengths
- **README very polished** — cocok untuk portfolio. Tech stack badges, clear architecture, quick start.
- **Multiple visualization assets** — architecture diagram, DAG graph, ERD, dbt lineage.
- **PLAN.md exists** — development roadmap terdokumentasi.

### Critical Findings
- **❌ Incident response plan** tidak ada — critical untuk production readiness.
- **⚠️ Data contracts** belum formal — tidak ada owner/schema versioning/SLA documented.

### Recommendations
1. **Buat INCIDENT-RESPONSE.md** — step-by-step apa yang dilakukan jika: DAG gagal, data kosong, data discrepancy, SLA miss.
2. **Formalize data contracts** — tambahkan `contract` config di dbt YAML, definisikan owner, freshness SLA, dan expected volume range.
3. **Tambah `sources.yml`** di dbt dengan freshness, loaded_at, dan description.

---

## Learning Roadmap

Berdasarkan **Critical Findings**, berikut rekomendasi prioritas:

### Priority 1: 🔴 Security Fix (Immediate)

| Item | Detail |
|---|---|
| **Konsep** | Secrets Management — jangan pernah hardcode credentials di source code |
| **Resource** | Baca tentang AWS Secrets Manager, HashiCorp Vault, atau environment variables |
| **Praktek** | Refactor `main.go` dan `generate_transactions.py` untuk baca password dari env var |
| **Priority** | **Critical** — harus diperbaiki sebelum production |

### Priority 2: 🟠 Data Quality Monitoring (1-2 Minggu)

| Item | Detail |
|---|---|
| **Konsep** | Data observability — row count validation, schema drift detection |
| **Resource** | Pelajari Great Expectations, dbt-expectations package, atau custom validation |
| **Praktek** | Implementasi row count check di Glue transform + tambah dbt tests |
| **Priority** | **High** — pipeline tanpa validation riskan data corruption tidak terdeteksi |

### Priority 3: 🟡 Test Coverage Expansion (2-3 Minggu)

| Item | Detail |
|---|---|
| **Konsep** | Data pipeline testing strategy — unit test untuk transform, integration test untuk end-to-end |
| **Resource** | `chispa` (PySpark testing), dbt test documentation, `pytest` dengan Spark |
| **Praktek** | Tambah PySpark unit tests + expand dbt tests ke 25+ tests |
| **Priority** | **Medium** — memperkuat reliability |

### Priority 4: 🟢 Observability & Incident Response (3-4 Minggu)

| Item | Detail |
|---|---|
| **Konsep** | Data observability, SLA monitoring, incident management |
| **Resource** | DataDog, Monte Carlo, atau custom Airflow SLAs + CloudWatch alarms |
| **Praktek** | Buat INCIDENT-RESPONSE.md + setup SLA monitoring di Airflow |
| **Priority** | **Medium** — penting untuk production readiness |

---

## Detail Temuan per File

| File | Baris | Temuan | Severity | Dimensi |
|---|---|---|---|---|
| `dags/go-extract/main.go` | ~78 | Hardcoded password `supersecretpassword` | 🔴 Critical | Security |
| `data-generator/generate_transactions.py` | ~37 | Hardcoded password `supersecretpassword` | 🔴 Critical | Security |
| `data-generator/generate_transactions.py` | ~35 | DB host hardcoded `localhost` | 🟡 Medium | Security |
| `dbt_pipeline/models/staging/stg_orders.sql` | 1 | Hanya `SELECT *`, tanpa cleansing/casting | 🟡 Medium | Data Modeling |
| `dbt_pipeline/models/staging/stg_order_items.sql` | 1 | Hanya `SELECT *`, tanpa cleansing/casting | 🟡 Medium | Data Modeling |
| `dbt_pipeline/models/marts/__marts__models_.yml` | — | Test coverage minimal (12 tests) | 🟡 Medium | Data Quality |
| `dags/spark-transform/transform.py` | — | Duplikasi kode dengan `transform_glue.py` | 🟢 Low | Code Quality |
| — | — | Tidak ada row count validation | 🟡 Medium | Data Quality |
| — | — | Tidak ada incident response plan | 🟡 Medium | Documentation |
| — | — | Tidak ada surrogate keys di dimensi | 🟢 Low | Data Modeling |

---

## Kesimpulan

**Skor Akhir: 7.9/10 — Siap Produksi dengan Catatan**

Proyek **Franchise Data Pipeline** menunjukkan kualitas engineering yang sangat baik untuk level portfolio. Arsitektur Medallion diimplementasikan dengan benar, code quality bersih, data modeling matang (SCD Type 2, star schema), dan dokumentasi komprehensif.

**3 Hal Paling Kuat:**
1. 🏆 **Arsitektur** — ELT murni, modular, streaming upload, backfill capability
2. 🏆 **Data Quality Rules** — 7 validasi termasuk anomaly detection statistik
3. 🏆 **Dokumentasi** — README, diagram arsitektur, column-level docs

**3 Hal Perlu Diperbaiki:**
1. 🔴 **Hardcoded password** — critical security issue
2. 🟡 **Test coverage** — perlu ditambah (row count, dbt tests, PySpark unit tests)
3. 🟡 **Incident plan & monitoring** — belum ada

---

*Laporan digenerate oleh GitHub Copilot (DeepSeek V4 Flash) pada 2026-07-06*
