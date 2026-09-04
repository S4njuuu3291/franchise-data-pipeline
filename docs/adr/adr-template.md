# ADR: Penambahan Data Quality Validation Layer

* **Status:** Accepted
* **Date:** 2026-09-04
* **Deciders:** Sanju

## Context

Pipeline ETL saat ini belum memiliki validation layer yang secara khusus memvalidasi data setelah proses extraction dan sebelum data diproses lebih lanjut.

Data yang diekstrak dari database dapat mengalami masalah seperti jumlah record yang tidak wajar, kolom yang tidak sesuai dengan schema yang diharapkan, nilai yang kosong pada kolom wajib, atau ketidaksesuaian karakteristik dataset lainnya. Tanpa validasi pada tahap ini, data yang bermasalah dapat diteruskan ke proses transformation dan berpotensi mempengaruhi kualitas data pada downstream layer.

Diperlukan sebuah validation layer yang dapat melakukan pemeriksaan terhadap dataset hasil extraction sebelum memasuki tahap transformation.

## Decision

Menambahkan **Great Expectations (GX)** sebagai data quality validation layer setelah proses extraction dan sebelum tahap transformation.

Alur pipeline menjadi:

**PostgreSQL → Go Extractor → Bronze (S3) → Great Expectations → Glue/PySpark → Silver → dbt → Gold**

GX akan digunakan sebagai **quality gate** untuk memvalidasi dataset yang telah diekstrak dan disimpan pada Bronze layer.

Validasi akan berfokus pada karakteristik dataset yang dapat menentukan apakah data layak diproses lebih lanjut, termasuk:

* **Volume:** memastikan jumlah record berada dalam rentang yang wajar.
* **Completeness:** memastikan kolom atau field yang wajib tersedia dan tidak memiliki missing value yang tidak diperbolehkan.
* **Validity:** memastikan struktur, schema, dan nilai data memenuhi expectation yang telah ditentukan.
* **Consistency:** memastikan karakteristik dataset konsisten dengan kontrak atau expectation yang telah ditetapkan.

Jika validation berhasil, pipeline dapat melanjutkan ke tahap transformation menggunakan Glue/PySpark.

Jika validation gagal, pipeline akan menandai validation sebagai failed dan mencegah data yang tidak memenuhi expectation untuk diproses lebih lanjut sampai masalahnya ditangani.

GX tidak menggantikan business-level data quality validation yang telah dilakukan pada Glue/PySpark maupun model-level testing yang dilakukan menggunakan dbt. Masing-masing layer tetap memiliki tanggung jawab yang berbeda.

## Alternatives Considered

### 1. Tidak menambahkan validation layer

Mempertahankan kondisi pipeline saat ini tanpa validasi khusus setelah extraction.

**Rejected:** pendekatan ini meningkatkan risiko data yang bermasalah diteruskan ke downstream processing tanpa terdeteksi sejak awal.

### 2. Menggunakan Great Expectations

Menambahkan Great Expectations sebagai framework untuk melakukan automated data validation setelah extraction.

**Selected:** GX menyediakan framework terstruktur untuk mendefinisikan, menjalankan, dan mendokumentasikan data expectations tanpa harus membangun seluruh validation framework secara custom.

Trade-off-nya adalah tambahan kompleksitas dan effort implementasi.

### 3. Menggunakan custom validation

Membangun validation menggunakan script atau logic custom.

**Rejected:** meskipun memberikan fleksibilitas tinggi, pendekatan ini membutuhkan lebih banyak logic yang harus dikembangkan dan dipelihara sendiri serta berpotensi menghasilkan validation framework yang tidak konsisten.

## Consequences

### Positive

1. **Early detection:** masalah pada dataset hasil extraction dapat dideteksi sebelum memasuki tahap transformation.
2. **Improved data quality:** mengurangi risiko dataset yang tidak memenuhi expectation diteruskan ke downstream processing.
3. **Improved traceability:** hasil validation dapat dicatat dan ditinjau kembali untuk mengetahui apakah suatu batch memenuhi expectation.
4. **Maintainability:** data quality expectations dapat didefinisikan secara terstruktur menggunakan framework khusus.
5. **Clear separation of responsibilities:** validation pada extraction boundary, business validation pada transformation layer, dan model validation pada dbt dapat dipisahkan dengan lebih jelas.

### Negative

1. **Increased pipeline complexity:** pipeline memiliki tambahan validation layer yang harus dikonfigurasi dan dipelihara.
2. **Additional execution time:** proses validation menambah overhead terhadap waktu eksekusi pipeline.
3. **Additional failure point:** pipeline dapat berhenti ketika dataset tidak memenuhi expectation, sehingga diperlukan prosedur untuk menangani validation failure.
4. **Implementation effort:** diperlukan waktu tambahan untuk mendefinisikan expectations, mengintegrasikan GX dengan orchestration, dan menguji validation behavior.

## References

* Great Expectations Documentation
* Franchise Data Pipeline Architecture
