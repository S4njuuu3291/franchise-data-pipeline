# ADR: Database Schema Evolution

- **Status:** Accepted
- **Date:** 2026-09-08
- **Deciders:** Sanju

## Context

Source transactional database saat ini menggunakan schema yang relatif sederhana dan belum sepenuhnya merepresentasikan proses operasional franchise restaurant.

Untuk meningkatkan realism dan memperluas data domain yang dapat diproses oleh pipeline, source schema akan dikembangkan dengan menambahkan beberapa entity dan atribut baru.

Perubahan schema mencakup:

- Penambahan tabel `customers`
- Penambahan tabel `employees`
- Penambahan tabel `payments`
- Penambahan kolom baru pada tabel `orders`
- Penambahan kolom baru pada tabel `order_items`

Perubahan pada source schema akan mempengaruhi beberapa komponen downstream, termasuk data generator, extraction process, data quality validation, transformation logic, data modeling, dan database schema documentation.

## Decision

Mengadopsi schema evolution pada source transactional database dan menyesuaikan komponen pipeline yang terdampak oleh perubahan schema.

Perubahan mencakup:

- Memperbarui PostgreSQL source schema.
- Memperbarui data generator untuk menghasilkan data berdasarkan schema baru.
- Menyesuaikan extraction logic untuk mengekstrak tabel dan kolom baru.
- Memperbarui Great Expectations validation rules untuk mengakomodasi tabel, kolom, dan data quality requirements baru.
- Menyesuaikan transformation logic yang terdampak oleh perubahan schema.
- Menyesuaikan downstream data model dan transformation apabila diperlukan.
- Memperbarui ERD, architecture documentation, dan dokumentasi schema untuk mencerminkan schema baru.

## Alternatives Considered

### 1. Mempertahankan schema yang ada

**Rejected.**

Mempertahankan schema saat ini membutuhkan perubahan minimal pada pipeline, tetapi schema existing relatif sederhana dan membatasi representasi proses operasional serta domain data yang dapat diproses.

### 2. Menambahkan banyak domain bisnis sekaligus

**Rejected.**

Menambahkan domain seperti inventory, supplier, promotion, warehouse, dan purchase order secara bersamaan akan meningkatkan kompleksitas source system dan pipeline secara signifikan.

Pendekatan ini dianggap terlalu besar untuk scope schema evolution saat ini.

### 3. Incremental schema evolution

**Accepted.**

Menambahkan domain `customers`, `employees`, dan `payments` secara bertahap meningkatkan realism source transactional database tanpa memperluas scope menjadi sistem operasional restoran atau ERP yang terlalu kompleks.

## Consequences

### Positive

- Source schema menjadi lebih representatif terhadap transactional system franchise restaurant.
- Pipeline dapat memproses entity dan relationship baru seperti customer, employee, dan payment data.
- Data quality validation dapat mencakup additional schema, referential integrity, completeness, dan business rules baru.
- Analytical model dapat dikembangkan untuk mendukung analisis customer, employee, dan payment.
- Relationship antara transaksi dan proses operasional menjadi lebih kaya dan realistis.

### Negative

- Perubahan schema memerlukan perubahan pada beberapa komponen pipeline.
- Validation rules dan business rules perlu diperbarui.
- Data generator perlu menghasilkan relationship yang valid antar entity baru.
- Testing dan dokumentasi perlu diperbarui untuk memastikan pipeline tetap berjalan dengan schema baru.
- Schema evolution meningkatkan kompleksitas pipeline dibandingkan schema sebelumnya.

## References

- infrastructure/database/sql/SOURCE-SCHEMA_v2.sql
- assets/struktur-oltp.mmd
- assets/architecture.mmd

## Implementation Status

Implemented across the source schema, data generator, Go extractor, GX Bronze/Silver quality gates, Glue/PySpark transformation, dbt snapshots and marts, Athena catalog, and project documentation.
- Data Generator
- Go Extractor
- Great Expectations Validation Suites
