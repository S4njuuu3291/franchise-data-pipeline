# Failure Injection Results

> **Correction:** Setelah log task diperiksa, FI-001 dan FI-002 pada DAG run
> sebelumnya tidak mencapai Go extractor. Keduanya gagal saat Airflow merender
> `{{ ds }}` dengan `UndefinedError: 'ds' is undefined`. Hasil di bawah tetap
> disimpan sebagai evidence, tetapi decision eksperimen tersebut dibatalkan.

## FI-001 — Source PostgreSQL unavailable

Failure injected:

- DAG run: `manual__2026-08-13T09:33:10.507704+00:00`
- `PG_HOST=fi-001-postgres-unavailable` diteruskan sementara ke `extract_data` melalui `dag_run.conf`.
- Fault injection kemudian dihapus dari DAG.

Expected:

- `extract_data` gagal.
- Airflow melakukan satu retry setelah 5 menit.
- Glue dan dbt tidak dijalankan.

Observed:

- Attempt pertama berjalan sekitar 5 detik dan masuk `up_for_retry`.
- Retry dijadwalkan setelah `retry_delay=5 minutes`.
- Attempt kedua gagal sekitar 4 detik kemudian.
- Final state `extract_data`: `failed`.
- Final state DAG downstream: `upstream_failed`.

Airflow state:

- `start_pipeline`: `success`
- `extract_data`: `failed` setelah 1 retry
- `bronze_to_silver`: `upstream_failed`
- Seluruh task dbt/Cosmos: `upstream_failed`
- `end_pipeline`: `upstream_failed`

Data state:

- Bronze: tidak ada object baru dari run FI-001.
- Silver: tidak disentuh.
- Gold: tidak disentuh.
- Quarantine: tidak disentuh.

Retry behavior:

- Sesuai konfigurasi: 1 retry dengan jeda 5 menit.
- Retry tidak langsung; task tetap `up_for_retry` selama periode jeda.

Recovery attempted:

- Fault injection dihapus dari DAG.
- DAG siap dijalankan ulang dengan host PostgreSQL normal.

Recovery result:

- Belum menjalankan recovery run normal.
- Tidak ada data yang perlu dibersihkan dari FI-001.

Finding (dikoreksi):

- Failure terjadi di tahap template rendering Airflow, sebelum extractor dijalankan.
- PostgreSQL connectivity behavior belum teruji.
- Retry Airflow dan downstream propagation terobservasi, tetapi bukan untuk source failure.

Decision:

`INVESTIGATE`

## FI-002 — Bronze/S3 write failure

Failure injected:

- DAG run: `manual__2026-08-13T09:52:12.272696+00:00`
- AWS credentials palsu diteruskan sementara hanya ke `extract_data`.
- PostgreSQL dan nama bucket Bronze tetap normal.
- Fault injection kemudian dihapus dari DAG.

Expected:

- Query PostgreSQL dapat dimulai.
- Upload Bronze gagal karena kredensial AWS invalid.
- Airflow retry satu kali.
- Glue dan dbt tidak berjalan.

Observed:

- Attempt pertama selesai sekitar 4 detik dan masuk `up_for_retry`.
- Attempt kedua berjalan sekitar 4 detik dan berakhir `failed`.
- Retry terjadi setelah sekitar 5 menit.
- Worker mencatat kedua attempt sebagai selesai dengan final state yang sesuai.
- Log aplikasi Go tidak tersedia melalui CLI Airflow 3 pada environment ini, sehingga query database tidak dapat dibuktikan sukses secara langsung dari log task.

Airflow state:

- `start_pipeline`: `success`
- `extract_data`: `failed` setelah 1 retry
- `bronze_to_silver`: `upstream_failed`
- Seluruh task dbt/Cosmos: `upstream_failed`
- `end_pipeline`: `upstream_failed`

Data state:

- Bronze: tidak ada object baru yang dapat diatribusikan ke FI-002; object lama tidak dihapus.
- Silver: tidak disentuh.
- Gold: tidak disentuh.
- Quarantine: tidak disentuh.
- Partial object: tidak teramati.

Retry behavior:

- Sesuai konfigurasi: 1 retry dengan jeda 5 menit.
- Retry mengulang seluruh extractor, bukan hanya upload S3.

Recovery attempted:

- Fault injection dihapus dari DAG.
- Belum menjalankan recovery run normal.

Recovery result:

- Belum diverifikasi dengan rerun normal.

Finding (dikoreksi):

- Failure terjadi saat Airflow merender `{{ ds }}`, bukan saat query PostgreSQL atau upload S3.
- Query success, S3 write failure, dan partial object belum teruji.
- Eksperimen perlu diulang setelah template date pada DAG diperbaiki atau tanggal
  diberikan melalui context yang benar.

Decision:

`INVESTIGATE`

## Infrastructure finding

Fault injection melalui `env` memicu task rendering pada Airflow 3 environment ini,
tetapi `ds` tidak tersedia di context task. Ini adalah failure terpisah yang perlu
diperbaiki sebelum FI-001/FI-002 dapat dianggap valid.
