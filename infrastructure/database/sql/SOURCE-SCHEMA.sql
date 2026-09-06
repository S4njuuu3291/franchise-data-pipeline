-- =============================================================================
-- SOURCE-SCHEMA.sql
-- Database : franchise_oltp (PostgreSQL)
-- Schema   : public
-- =============================================================================
-- Tabel-tabel ini menjadi sumber data (source/primary) untuk pipeline ETL.
-- Struktur ini merupakan database transaksional OLTP tempat kasir mencatat
-- seluruh transaksi penjualan franchise restoran.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. outlet_master — Data master cabang restoran
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outlet_master (
    outlet_id   SERIAL       NOT NULL PRIMARY KEY,
    outlet_name VARCHAR(150) NOT NULL,
    city        VARCHAR(100) NOT NULL,
    region_tier VARCHAR(50)  NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 2. menu_master — Data master menu produk
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS menu_master (
    menu_id         SERIAL        NOT NULL PRIMARY KEY,
    menu_name       VARCHAR(200)  NOT NULL,
    category        VARCHAR(50)   NOT NULL,
    base_price      NUMERIC(12,2) NOT NULL,
    price_tier_1    NUMERIC(12,2) NOT NULL,
    price_tier_2    NUMERIC(12,2) NOT NULL,
    price_tier_3    NUMERIC(12,2) NOT NULL,
    is_promo_active BOOLEAN       NOT NULL DEFAULT FALSE,
    updated_at      TIMESTAMP     NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 3. orders — Header transaksi pesanan
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    order_id       SERIAL       NOT NULL PRIMARY KEY,
    outlet_id      INTEGER      NOT NULL,
    cashier_id     INTEGER      NOT NULL,
    total_amount   NUMERIC(14,2) NOT NULL,
    payment_method VARCHAR(30)  NOT NULL,
    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_orders_outlet
        FOREIGN KEY (outlet_id)
        REFERENCES outlet_master (outlet_id)
);

-- ---------------------------------------------------------------------------
-- 4. order_items — Detail baris item dalam pesanan
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
    item_id        SERIAL        NOT NULL PRIMARY KEY,
    order_id       INTEGER       NOT NULL,
    menu_id        INTEGER       NOT NULL,
    quantity       INTEGER       NOT NULL DEFAULT 1,
    price_per_item NUMERIC(12,2) NOT NULL,
    subtotal       NUMERIC(14,2) NOT NULL,

    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders (order_id),

    CONSTRAINT fk_order_items_menu
        FOREIGN KEY (menu_id)
        REFERENCES menu_master (menu_id)
);

-- ---------------------------------------------------------------------------
-- TRIGGER: Auto-update updated_at untuk tabel master
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_menu_master_updated_at
    BEFORE UPDATE ON menu_master
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_outlet_master_updated_at
    BEFORE UPDATE ON outlet_master
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


