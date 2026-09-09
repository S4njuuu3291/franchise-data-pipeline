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
DROP TABLE IF EXISTS
    payments,
    order_items,
    orders,
    customers,
    employees,
    menu_master,
    outlet_master
CASCADE;

DROP TYPE IF EXISTS order_status CASCADE;
DROP TYPE IF EXISTS payment_method CASCADE;
DROP TYPE IF EXISTS payment_status CASCADE;
DROP TYPE IF EXISTS employee_role CASCADE;
DROP TYPE IF EXISTS employment_status CASCADE;

CREATE TYPE order_status AS ENUM (
    'PENDING', 'COMPLETED', 'CANCELLED', 'REFUNDED'
);

CREATE TYPE payment_method AS ENUM (
    'CASH', 'QRIS', 'DEBIT_CARD', 'CREDIT_CARD', 'E_WALLET'
);

CREATE TYPE payment_status AS ENUM (
    'PENDING', 'SUCCESS', 'FAILED', 'REFUNDED'
);

CREATE TYPE employee_role AS ENUM (
    'CASHIER', 'MANAGER', 'STAFF'
);

CREATE TYPE employment_status AS ENUM (
    'ACTIVE', 'INACTIVE'
);

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
-- 3. customers — Data master pelanggan
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    customer_id   SERIAL        NOT NULL PRIMARY KEY,
    customer_name VARCHAR(150)  NOT NULL,
    email         VARCHAR(255)  NOT NULL UNIQUE,
    phone         VARCHAR(30)   NOT NULL,
    created_at    TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP     NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 4. employees — Data master karyawan operasional
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employees (
    employee_id        SERIAL        NOT NULL PRIMARY KEY,
    employee_name      VARCHAR(150)  NOT NULL,
    employee_role               employee_role NOT NULL,
    outlet_id          INTEGER       NOT NULL,
    employment_status  employment_status NOT NULL DEFAULT 'ACTIVE',
    created_at         TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMP     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_employees_outlet
        FOREIGN KEY (outlet_id)
        REFERENCES outlet_master (outlet_id)
);

-- ---------------------------------------------------------------------------
-- 5. orders — Header transaksi pesanan
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    order_id       SERIAL       NOT NULL PRIMARY KEY,
    customer_id    INTEGER,
    outlet_id      INTEGER      NOT NULL,
    cashier_id     INTEGER      NOT NULL,
    total_amount   NUMERIC(14,2) NOT NULL,
    payment_method VARCHAR(30)  NOT NULL,
    order_status   order_status NOT NULL DEFAULT 'PENDING',
    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_orders_outlet
        FOREIGN KEY (outlet_id)
        REFERENCES outlet_master (outlet_id),

    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers (customer_id),

    CONSTRAINT fk_orders_cashier
        FOREIGN KEY (cashier_id)
        REFERENCES employees (employee_id)
);

-- Walk-in transaction tidak wajib memiliki customer.
ALTER TABLE orders
    ALTER COLUMN customer_id DROP NOT NULL;

-- ---------------------------------------------------------------------------
-- 6. order_items — Detail baris item dalam pesanan
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

CREATE TABLE IF NOT EXISTS payments (
    payment_id          SERIAL        NOT NULL PRIMARY KEY,
    order_id            INTEGER       NOT NULL,
    payment_method      payment_method NOT NULL,
    payment_status      payment_status NOT NULL,
    amount              NUMERIC(14,2) NOT NULL,
    paid_at             TIMESTAMP     NOT NULL DEFAULT NOW(),
    provider_reference  VARCHAR(100),

    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id)
        REFERENCES orders (order_id)
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

DROP TRIGGER IF EXISTS trg_menu_master_updated_at ON menu_master;

CREATE TRIGGER trg_menu_master_updated_at
    BEFORE UPDATE ON menu_master
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_outlet_master_updated_at ON outlet_master;

CREATE TRIGGER trg_outlet_master_updated_at
    BEFORE UPDATE ON outlet_master
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_customers_updated_at ON customers;

CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_employees_updated_at ON employees;

CREATE TRIGGER trg_employees_updated_at
    BEFORE UPDATE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ---------------------------------------------------------------------------
-- DUMMY DATA — Data awal untuk eksperimen schema dev
-- ---------------------------------------------------------------------------

-- INSERT INTO outlet_master
--     (outlet_id, outlet_name, city, region_tier, created_at, updated_at)
-- VALUES
--     (1, 'Outlet Bandung Dago', 'Bandung', 'tier_1', '2026-01-01 08:00:00', '2026-01-01 08:00:00'),
--     (2, 'Outlet Jakarta Selatan', 'Jakarta', 'tier_1', '2026-01-02 08:00:00', '2026-01-02 08:00:00'),
--     (3, 'Outlet Surabaya Tunjungan', 'Surabaya', 'tier_2', '2026-01-03 08:00:00', '2026-01-03 08:00:00')
-- ON CONFLICT (outlet_id) DO NOTHING;

-- INSERT INTO menu_master
--     (menu_id, menu_name, category, base_price, price_tier_1, price_tier_2,
--      price_tier_3, is_promo_active, updated_at)
-- VALUES
--     (1, 'Nasi Ayam Original', 'main_course', 25000.00, 25000.00, 23000.00, 21000.00, FALSE, '2026-01-01 09:00:00'),
--     (2, 'Mie Goreng Spesial', 'main_course', 22000.00, 22000.00, 20000.00, 18000.00, TRUE,  '2026-01-02 09:00:00'),
--     (3, 'Es Teh Manis',      'beverage',     8000.00,  8000.00,  7000.00,  6000.00, FALSE, '2026-01-03 09:00:00')
-- ON CONFLICT (menu_id) DO NOTHING;

-- INSERT INTO customers
--     (customer_id, customer_name, email, phone, created_at, updated_at)
-- VALUES
--     (1, 'Andi Pratama', 'andi.pratama@example.com', '+628111000001', '2026-01-01 07:30:00', '2026-01-01 07:30:00'),
--     (2, 'Siti Rahma',   'siti.rahma@example.com',   '+628111000002', '2026-01-02 07:45:00', '2026-01-02 07:45:00'),
--     (3, 'Budi Santoso', 'budi.santoso@example.com', '+628111000003', '2026-01-03 08:15:00', '2026-01-03 08:15:00')
-- ON CONFLICT (customer_id) DO NOTHING;

-- INSERT INTO employees
--     (employee_id, employee_name, employee_role, outlet_id, employment_status, created_at, updated_at)
-- VALUES
--     (101, 'Rina Wijaya',  'CASHIER', 1, 'ACTIVE', '2026-01-01 07:00:00', '2026-01-01 07:00:00'),
--     (102, 'Dimas Saputra','CASHIER', 2, 'ACTIVE', '2026-01-02 07:00:00', '2026-01-02 07:00:00'),
--     (103, 'Lina Permata', 'CASHIER', 3, 'ACTIVE', '2026-01-03 07:00:00', '2026-01-03 07:00:00')
-- ON CONFLICT (employee_id) DO NOTHING;

-- INSERT INTO orders
--     (order_id, customer_id, outlet_id, cashier_id, total_amount, payment_method, order_status, created_at)
-- VALUES
--     (1, 1,    1, 101, 58000.00, 'CASH', 'COMPLETED', '2026-01-05 10:15:00'),
--     (2, NULL, 2, 102, 40000.00, 'QRIS', 'COMPLETED', '2026-01-05 12:30:00'),
--     (3, 3,    3, 103, 29000.00, 'DEBIT_CARD', 'PENDING', '2026-01-06 18:45:00')
-- ON CONFLICT (order_id) DO NOTHING;

-- INSERT INTO payments
--     (payment_id, order_id, payment_method, payment_status, amount, paid_at, provider_reference)
-- VALUES
--     (1, 1, 'CASH', 'SUCCESS', 58000.00, '2026-01-05 10:16:00', NULL),
--     (2, 2, 'QRIS', 'SUCCESS', 40000.00, '2026-01-05 12:31:00', 'QRIS-DEV-000001'),
--     (3, 3, 'DEBIT_CARD', 'PENDING', 29000.00, '2026-01-06 18:46:00', 'DEBIT-DEV-000001')
-- ON CONFLICT (payment_id) DO NOTHING;

-- INSERT INTO order_items
--     (item_id, order_id, menu_id, quantity, price_per_item, subtotal)
-- VALUES
--     (1, 1, 1, 2, 25000.00, 50000.00),
--     (2, 1, 3, 1,  8000.00,  8000.00),
--     (3, 2, 2, 2, 20000.00, 40000.00)
-- ON CONFLICT (item_id) DO NOTHING;

-- -- Sinkronisasi sequence setelah insert dengan ID eksplisit.
-- SELECT setval(
--     pg_get_serial_sequence('outlet_master', 'outlet_id'),
--     COALESCE((SELECT MAX(outlet_id) FROM outlet_master), 1),
--     true
-- );

-- SELECT setval(
--     pg_get_serial_sequence('menu_master', 'menu_id'),
--     COALESCE((SELECT MAX(menu_id) FROM menu_master), 1),
--     true
-- );

-- SELECT setval(
--     pg_get_serial_sequence('customers', 'customer_id'),
--     COALESCE((SELECT MAX(customer_id) FROM customers), 1),
--     true
-- );

-- SELECT setval(
--     pg_get_serial_sequence('employees', 'employee_id'),
--     COALESCE((SELECT MAX(employee_id) FROM employees), 1),
--     true
-- );

-- SELECT setval(
--     pg_get_serial_sequence('orders', 'order_id'),
--     COALESCE((SELECT MAX(order_id) FROM orders), 1),
--     true
-- );

-- SELECT setval(
--     pg_get_serial_sequence('payments', 'payment_id'),
--     COALESCE((SELECT MAX(payment_id) FROM payments), 1),
--     true
-- );

-- SELECT setval(
--     pg_get_serial_sequence('order_items', 'item_id'),
--     COALESCE((SELECT MAX(item_id) FROM order_items), 1),
--     true
-- );
