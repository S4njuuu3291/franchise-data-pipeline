### RENEW: Rencana Perubahan Data Generator

**1. Sinkronisasi Data Master pada seedmaster.py** 

* Berdasarkan dokumen **adr004** dan **schema dev**, lakukan pembaruan pada kode seedmaster.py untuk menambahkan fitur *seeding* data employees dan customer.
* Pastikan adanya sinkronisasi yang valid antara employee_id dan customer_id. Seluruh ID yang dihasilkan secara acak saat proses *seeding* harus terintegrasi dengan benar sebagai referensi (*foreign key*) pada tabel orders.
* **Catatan Penting:** Transaksi yang digenerate tidak boleh menggunakan ID yang tidak terdaftar atau tidak eksis di dalam tabel master.

**2. Penyesuaian Generator Transaksi dan Implementasi ENUM** 

* Berdasarkan **adr004** dan **schema dev**, ubah kode generator transaksi untuk mengakomodasi sintesis data pada tabel-tabel baru, serta menambahkan atribut baru pada tabel orders.
* Implementasikan struktur data **ENUM** untuk tabel dan atribut berikut: 

  * **orders.order_status** 

    * PENDING
    * COMPLETED
    * CANCELLED
    * REFUNDED
  * **payments.payment_method** 

    * CASH
    * QRIS
    * DEBIT_CARD
    * CREDIT_CARD
    * E_WALLET
  * **payments.payment_status** 

    * PENDING
    * SUCCESS
    * FAILED
    * REFUNDED
  * **employees.employee_role** 

    * CASHIER
    * MANAGER
    * STAFF
  * **employees.employment_status** 

    * ACTIVE
    * INACTIVE
* **Catatan:** Untuk atribut menu_master.category, pertahankan konfigurasi dan data yang berjalan saat ini.

**3. Pembaruan Unit Testing** 

* Setelah perubahan kode di atas selesai, lakukan pembaruan (*update*) pada seluruh skrip *unit testing* terkait untuk mengakomodasi struktur baru.
* Pastikan pengujian berjalan dengan baik (*pass*) untuk menjamin fungsionalitas dan validitas kode yang baru.