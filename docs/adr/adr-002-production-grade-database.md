# ADR: Upgrade database configuration to production-grade

* **Status:** Accepted
* **Date:** 2026-09-06
* **Deciders:** Sanju

## Context
Saat ini database sumber, yakni PostgreSQL, menggunakan konfigurasi standar belajar yang belum mencerminkan praktik keamanan dan profesionalitas database yang baik.
Beberapa hal yang perlu diperhatikan antara lain:
- database tidak menggunakan SSL untuk koneksi, sehingga data yang dikirimkan dari client ke server tidak terenkripsi.
- kredensial database hardcoded di dalam kode, sehingga berpotensi terekspos jika kode dibagikan.
- database belum menerapkan prinsip least privilege, sehingga user yang digunakan untuk koneksi memiliki hak akses yang lebih dari yang dibutuhkan. Dalam hal ini, pipeline Airflow menggunakan superuser sehingga memiliki akses yang terlalu luas.
- database belum menerapkan security group, sehingga tidak ada pembatasan akses berdasarkan IP atau jaringan tertentu.

## Decision
- Mengaktifkan SSL untuk koneksi database, sehingga data yang dikirimkan dari client ke server terenkripsi dengan sertifikat, TLS, dan konfigurasi yang sesuai.
- Menggunakan folder secret dengan file `.txt` yang di-ignore, bukan `.env`, serta menggunakan secret di Docker Compose sehingga kredensial database tidak hardcoded di dalam kode dan lebih aman.
- Membuat user khusus untuk pipeline Airflow dengan hak akses yang sesuai, sehingga prinsip least privilege diterapkan.
- Menerapkan security group untuk membatasi akses ke database hanya dari IP atau jaringan tertentu, sehingga meningkatkan keamanan database.

## Alternatives Considered
- Tidak melakukan upgrade database configuration, tetap menggunakan konfigurasi standar belajar.
**Rejected:** pendekatan ini meningkatkan risiko keamanan dan profesionalitas database yang buruk, sehingga tidak sesuai dengan praktik terbaik dalam pengelolaan database.

## Consequences
- Meningkatkan keamanan dan profesionalitas database, sehingga lebih sesuai dengan praktik terbaik dalam pengelolaan database.

### Positive
- Meningkatkan keamanan database dengan mengaktifkan SSL untuk koneksi, sehingga data yang dikirimkan dari client ke server terenkripsi.
- Meningkatkan keamanan kredensial database dengan menggunakan folder secret dan tidak hardcoded di dalam kode, sehingga lebih aman.
- Menerapkan prinsip least privilege dengan membuat user khusus untuk pipeline airflow dengan hak akses yang sesuai, sehingga mengurangi risiko akses yang tidak sah.
- Menerapkan security group untuk membatasi akses ke database hanya dari IP atau jaringan tertentu, sehingga meningkatkan keamanan database.

### Negative
- Meningkatkan kompleksitas pengelolaan database, karena perlu mengelola sertifikat SSL, kredensial database, hak akses user, dan security group.

## References
