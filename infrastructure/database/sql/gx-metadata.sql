-- Pastikan dijalankan di dalam database 'gx_metadata'
CREATE TABLE IF NOT EXISTS public.data_quality_ledger (
    id SERIAL PRIMARY KEY,
    validation_id VARCHAR(255) NOT NULL,   -- ID validation result dari GX
    execution_date DATE NOT NULL,          -- Tanggal batch daily pipeline Anda
    stage VARCHAR(50) NOT NULL,             -- 'Bronze' atau 'Silver'
    asset_name VARCHAR(150) NOT NULL,       -- 'menu_master_asset', 'orders_silver_asset', dll
    volume INTEGER NOT NULL,                -- Angka baris data (Row Count) hasil tangkapan GX
    success_rate NUMERIC(5,2) NOT NULL,      -- Persentase sukses pengujian (misal: 100.00 atau 95.50)
    status VARCHAR(20) NOT NULL,            -- 'SUCCESS' atau 'FAILED'
    created_at TIMESTAMP DEFAULT NOW()      -- Log waktu audit otomatis dari sistem
);

ALTER TABLE public.data_quality_ledger
    ADD COLUMN IF NOT EXISTS validation_id VARCHAR(255);

-- Buat indeks agar query Grafana di masa mendatang tetap instan (Sangat Pro!)
CREATE INDEX IF NOT EXISTS idx_dq_ledger_date ON public.data_quality_ledger(execution_date);
CREATE INDEX IF NOT EXISTS idx_dq_ledger_asset ON public.data_quality_ledger(asset_name);
