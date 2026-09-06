-- =============================================================================
-- AMANKAN TABEL EKSISTING DI SKEMA PUBLIC
-- =============================================================================

-- Pastikan grup readonly HANYA bisa melakukan SELECT pada tabel-tabel sistem asli Anda
GRANT SELECT ON TABLE public.outlet_master TO oltp_readonly;
GRANT SELECT ON TABLE public.menu_master   TO oltp_readonly;
GRANT SELECT ON TABLE public.orders        TO oltp_readonly;
GRANT SELECT ON TABLE public.order_items   TO oltp_readonly;

-- =============================================================================
-- ANTISIPASI TABEL MASA DEPAN (DEFAULT PRIVILEGES)
-- =============================================================================
-- Jika di masa depan sistem OLTP membuat tabel baru (misal: 'voucher_master') 
-- menggunakan user 'replicator_user', user Airflow otomatis langsung bisa membaca.
ALTER DEFAULT PRIVILEGES 
FOR ROLE replicator_user 
IN SCHEMA public 
GRANT SELECT ON TABLES TO oltp_readonly;
