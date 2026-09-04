# IDEMPOTENCY AUDIT

==============================================================

## Component: Go Extractor

**Input identity:**
Query terhadap PostgreSQL replica dengan filter tanggal (`created_at::date = $1` untuk transaksi; full table untuk master). Setiap run menghasilkan CSV yang isinya ditentukan oleh state DB untuk tanggal yang sama.

**Write target:**
- Master (flat): s3://{bronze}/outlet_master/outlet_master.csv , s3://{bronze}/menu_master/menu_master.csv
- Transaksi (Hive partition): s3://{bronze}/orders/year=YYYY/month=MM/day=DD/orders.csv , s3://{bronze}/order_items/year=YYYY/month=MM/day=DD/order_items.csv
- Key digenerate di executeStreamingUpload(): IsMaster=true -> flat, IsMaster=false -> partition

**Write mode:**
Upload via transfermanager.UploadObject(...) = S3 PutObject (overwrite/replace). Tidak ada mode append; setiap upload ke key yang sama MENIMPA objek sebelumnya.

**What happens on same-date rerun:**
Dengan key S3 yang sama dan query yang sama (filter tanggal sama), file CSV lama DITIMPA dengan konten identik. Hasil akhir di S3 sama persis — tidak ada file ganda (selama state DB untuk tanggal itu tidak berubah).

**Potential duplicate:**
Tidak ada. PutObject menimpa key yang sama, jadi tidak pernah ada dua file untuk satu tanggal/tabel yang sama.

**Potential data loss:**
Tidak ada. Overwrite hanya menimpa file yang sama dengan hasil query ulang yang identik. Tidak ada DELETE; key per tanggal/partisi unik sehingga tidak ada race condition.

**Idempotent:**
YES

**Reason:**
Karena untuk tanggal/input yang sama, Go extractor menulis ke key S3 yang sama persis menggunakan PutObject (overwrite). Re-run menghasilkan file identik di lokasi sama — deterministik, tanpa akumulasi duplikat atau kehilangan data. Catatan: idempotensi berlaku pada level object/file di S3 dan bergantung pada query DB yang deterministik untuk tanggal yang sama.

==============================================================

## Component: Glue Silver

**Input identity:**
Baca CSV dari Bronze pada partisi tanggal tertentu (orders + order_items), join dengan master data (menu_master, outlet_master), lalu terapkan 7 rule validasi. Deterministik terhadap isi Bronze untuk tanggal yang sama.

**Write target:**
- Master (full load, flat): s3://{silver}/outlet_master/ , s3://{silver}/menu_master/
- Transaksi (Hive partition per tanggal): s3://{silver}/orders/year=YYYY/month=MM/day=DD/ , s3://{silver}/order_items/year=YYYY/month=MM/day=DD/
- Quarantine: s3://{quarantine}/orphan_items/ , invalid_payments/ , invalid_prices/ , duplicate_orders/ , anomaly_cashiers/ , orders_discrepancies/ (masing-masing berpartition tahun/bulan/hari)

**Write mode:**
Semua write memakai .mode("overwrite") — menimpa direktori partisi/table yang sama. Tidak ada mode append. Master full overwrite, transaksi overwrite per partisi tanggal, quarantine overwrite per partisi.

**What happens on same-date rerun:**
Dengan isi Bronze yang sama, Glue membaca partisi yang sama, menerapkan transformasi yang sama, lalu overwrite direktori partisi Silver yang sama dengan konten identik. Hasil akhir tidak berubah (selama input Bronze tidak berubah).

**Potential duplicate:**
Tidak ada. .mode("overwrite") menghapus dan menulis ulang isi direktori partisi yang sama, jadi tidak ada akumulasi file duplikat untuk satu partisi.

**Potential data loss:**
Tidak ada (untuk re-run dengan input sama). Overwrite hanya menimpa partisi yang sedang diproses. Catatan: master table full-overwrite tiap run, aman karena isinya full load data yang sama dari Bronze.

**Idempotent:**
YES

**Reason:**
Karena semua write memakai .mode("overwrite") ke partisi/path yang sama, dan transformasi deterministik terhadap input Bronze yang sama. Re-run menghasilkan output Silver yang identik di lokasi yang sama. Idempotensi berlaku pada level partisi direktori S3 dan bergantung pada input Bronze yang deterministik untuk tanggal yang sama.
