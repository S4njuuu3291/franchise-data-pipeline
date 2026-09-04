# Failure Behavior dan Recovery

**Owner:** Data Engineering  
**Status:** Observed from repository  
**Environment:** dev  
**Last updated:** 2026-08-13

Dokumen ini memetakan perilaku failure berdasarkan kode dan konfigurasi saat ini.
Ini adalah baseline sebelum perubahan reliability dilakukan.

## Ringkasan

| Komponen | Failure menjadi | Retry | Timeout eksplisit | Downstream berhenti? | Recovery unit |
|---|---|---:|---|---|---|
| Airflow | Task failed | 1 retry, jeda 5 menit | Tidak ada pada task | Ya, karena dependency | Satu task / satu DAG run |
| Go extractor | Process exit non-zero melalui `log.Fatalf` | Dilakukan Airflow | Tidak ada context timeout | Ya, task extractor gagal | Satu task extract, tetapi rerun dapat mengulang upload |
| Glue job | Exception Spark/Python atau job gagal | Tidak diatur di Terraform; Airflow dapat retry task | Tidak ada `execution_timeout` Airflow | Ya, dbt menunggu Glue selesai | Satu job untuk logical date |
| dbt/Cosmos | dbt command/test gagal | Mengikuti retry Airflow | Tidak ada `execution_timeout` task | Ya, `end_pipeline` tidak berjalan | Satu model/task dbt atau satu task group |

## Airflow

Airflow mendefinisikan `retries: 1` dan `retry_delay: 5 menit` pada `default_args`
([dags/dbt_sales_dag.py:22-27](../dags/dbt_sales_dag.py#L22-L27)). Failure pada
`extract_data`, `bronze_to_silver`, atau task dbt membuat task gagal. Karena dependency
bersifat linear, downstream tidak dijalankan sampai upstream berhasil.

`GlueJobOperator` memakai `wait_for_completion=True`
([dags/dbt_sales_dag.py:47-56](../dags/dbt_sales_dag.py#L47-L56)), sehingga Airflow
menunggu status job Glue. Tidak ada `execution_timeout` pada task dan konfigurasi
default Airflow juga kosong ([config/airflow.cfg:290-296](../config/airflow.cfg#L290-L296)).

Airflow menjadi lapisan retry utama: maksimal satu retry setelah attempt awal.

## Go extractor

Extractor menggunakan `context.Background()` tanpa deadline
([dags/go-extract/main.go:104-105](../dags/go-extract/main.go#L104-L105)). Parsing argumen,
koneksi database, konfigurasi bucket, inisialisasi S3, query, dan upload yang fatal dapat
mengakhiri process dengan `log.Fatalf` ([dags/go-extract/main.go:90-100](../dags/go-extract/main.go#L90-L100),
[main.go:179-189](../dags/go-extract/main.go#L179-L189),
[main.go:322-329](../dags/go-extract/main.go#L322-L329)).

Query dan CSV ditulis melalui `io.Pipe`; error query dikirim ke pipe
([dags/go-extract/main.go:292-304](../dags/go-extract/main.go#L292-L304)), lalu upload
dianggap gagal dan process berhenti. Tidak ada retry internal dan tidak ada timeout
database/S3 yang ditetapkan di kode.

### Prediksi: PostgreSQL tidak merespons lama

Query dapat menunggu lama karena context tidak memiliki deadline. Selama process masih
hidup, Airflow melihat task masih running; retry Airflow belum dimulai. Jika process
akhirnya error/berhenti, task menjadi failed dan Airflow melakukan satu retry.

### Prediksi: S3 gagal setelah query menghasilkan data

Data hasil query mengalir ke pipe, bukan disimpan sebagai file lokal. Jika upload gagal,
object Bronze bisa tidak terbentuk atau hanya menjadi upload multipart yang dibatalkan,
tetapi proses sudah mengonsumsi hasil query. Database tidak berubah. Jika beberapa upload
sebelumnya sudah berhasil, state menjadi parsial: sebagian object/partition sudah ada,
sebagian belum. Airflow kemudian me-retry seluruh extractor, termasuk master dan tanggal
yang sama.

## Glue job

Glue membaca Bronze, melakukan validasi, menulis quarantine, lalu menulis Silver
([transform_glue.py:30-46](../dags/spark-transform/transform_glue.py#L30-L46),
[transform_glue.py:183-196](../dags/spark-transform/transform_glue.py#L183-L196)). Exception pada read, transform, atau write membuat job gagal dan `job.commit()` tidak
tercapai. Tidak ada retry job yang didefinisikan di Terraform; retry yang terlihat dari
pipeline berasal dari Airflow.

Side effect dapat terjadi sebelum failure: master Silver ditulis lebih dulu, quarantine
untuk beberapa kategori dapat sudah tersedia, dan output Silver transaksi dapat sudah
ditulis. Karena banyak write memakai `mode("overwrite")`, rerun tanggal yang sama adalah
unit recovery yang paling aman untuk mengganti partition yang sedang diproses.

## dbt/Cosmos

Cosmos menjalankan model dbt lokal melalui manifest
([dags/dbt_sales_dag.py:58-89](../dags/dbt_sales_dag.py#L58-L89)). Failure query Athena,
compile, materialization, atau test membuat task dbt failed. Karena dbt berada setelah
Glue, downstream `end_pipeline` berhenti dan tidak dijalankan. Retry mengikuti Airflow:
satu retry dengan jeda lima menit.

Model dimension memakai table, sedangkan fact memakai incremental `insert_overwrite` dan
partisi tanggal. Recovery unit yang disarankan adalah rerun logical date/model yang gagal;
hindari full refresh kecuali memang dibutuhkan.

## Kesimpulan operasional

Unit recovery saat ini adalah satu logical date melalui rerun DAG. Sistem memiliki
idempotency parsial: Glue memakai overwrite per output, tetapi extractor tidak melakukan
rollback dan dapat meninggalkan state parsial ketika salah satu upload gagal. Belum ada
timeout aplikasi pada koneksi PostgreSQL, upload S3, Glue task, atau dbt task; ini adalah
risiko utama untuk diuji pada reliability test berikutnya.
