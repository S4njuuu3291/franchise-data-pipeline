## ADR: Monitoring Pipeline & Data Quality (Fase 1)

* Status: Proposed
* Date: 2026-09-06
* Deciders: Sanju

## Context
Pipeline data saat ini sudah berjalan stabil dan punya sistem cek kualitas data (GX). Namun, prosesnya masih bersifat blackbox (tidak terlihat). Kita tidak tahu secara instan jika data telat, jumlahnya anomali, atau ada error sebelum ada komplain dari pengguna.
## Decision
Untuk menghemat waktu dan infrastruktur, kita fokus pada Monitoring & Dasbor Terpusat terlebih dahulu:

   1. Metadata GX ke DB: Hasil cek kualitas data dan jumlah baris data otomatis disimpan ke database.
   2. Dasbor Grafana: Grafana akan membaca data dari DB tersebut untuk menampilkan tren kualitas data dan volume harian dalam satu layar.
   3. Fitur Lain Ditunda: Penggunaan Prometheus (metrik spek server) dan OpenLineage (peta aliran data) ditunda sampai pipeline menjadi lebih kompleks.

## Consequences

* (+) Mudah Dipantau: Kesehatan data langsung kelihatan di dasbor tanpa perlu cek log manual.
* (+) Ringan: Tidak perlu sewa server monitoring baru, cukup pakai database yang sudah ada.
* (-) Minim Metrik Server: Belum bisa memantau detail penggunaan CPU/Memory server Airflow di Grafana.
* (-) Aliran Data Manual: Pelacakan hubungan antar-tabel jika ada eror masih harus dicek manual.

------------------------------
