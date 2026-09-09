import argparse
import random
import yaml
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import sql

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

if DB_SCHEMA not in {"public", "dev"}:
    raise ValueError("DB_SCHEMA hanya boleh bernilai 'public' atau 'dev'")

def normalize_tier(value):
    """Normalize database tier labels to the internal tier key format."""
    return value.strip().lower().replace(" ", "_")


def get_secret_or_env(env_name, secret_path):
    value = os.getenv(env_name)
    if value:
        return value

    with open(os.path.join(PROJECT_ROOT, secret_path), encoding="utf-8") as secret_file:
        return secret_file.read().strip()

# =========================================================================
# Load Konfigurasi dari YAML
# =========================================================================
_config_path = os.path.join(os.path.dirname(__file__), "simulation_config.yaml")
with open(_config_path, "r") as _f:
    _config = yaml.safe_load(_f)

_sim = _config["simulation"]
VOLUME_SCALE = _sim.get("volume_scale", 1.0)
TX_RANGES = _sim["tx_ranges_per_outlet"]

# =========================================================================
# 1. KONSTANTA KONTROL DISTRIBUSI & ANOMALI
# =========================================================================

# Pembagian jam operasional dan bobot probabilitas terjadinya transaksi (Peak Hours)
HOURLY_TRAFFIC_WEIGHTS = {
    6: 5,    # 06.00 - 07.00 (Trafik rendah)
    7: 25,   # 07.00 - 08.00 (Peak 1 - Morning Coffee Rush)
    8: 30,   # 08.00 - 09.00 (Peak 1)
    9: 20,   # 09.00 - 10.00 (Peak 1)
    10: 10,  # 10.00 - 11.00
    11: 15,  # 11.00 - 12.00
    12: 40,  # 12.00 - 13.00 (Peak 2 - Lunch Break)
    13: 35,  # 13.00 - 14.00 (Peak 2)
    14: 15,  # 14.00 - 15.00
    15: 15,  # 15.00 - 16.00
    16: 20,  # 16.00 - 17.00
    17: 30,  # 17.00 - 18.00 (Dinner & Hangout)
    18: 35,  # 18.00 - 19.00 (Dinner)
    19: 30,  # 19.00 - 20.00 (Dinner)
    20: 15,  # 20.00 - 21.00
    21: 8    # 21.00 - 22.00 (Menuju Closing)
}

PAYMENT_METHODS = ["QRIS", "E_WALLET", "DEBIT_CARD", "CREDIT_CARD", "CASH"]
PAYMENT_WEIGHTS = [40, 20, 15, 12, 13] # Mayoritas cashless sesuai realitas urban
ORDER_STATUSES = ["PENDING", "COMPLETED", "CANCELLED", "REFUNDED"]
ORDER_STATUS_WEIGHTS = [5, 88, 4, 3]

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USER", "primary_user"),
        password=get_secret_or_env("DB_PASSWORD", "docker/secrets/postgres_primary_password.txt"),
        database=os.getenv("DB_NAME", "main_db"),
        sslmode=os.getenv("DB_SSLMODE", "verify-full"),
        sslrootcert=os.getenv(
            "DB_SSLROOTCERT",
            os.path.join(PROJECT_ROOT, "docker/certs/ca.crt"),
        ),
    )

# =========================================================================
# 2. CORE ENGINE GENERATOR
# =========================================================================

def fetch_master_data(cursor):
    """Mengambil data master dari DB untuk disimpan di memori Python (Caching)"""
    # Load Outlets
    cursor.execute(sql.SQL("SELECT outlet_id, region_tier FROM {};").format(
        sql.Identifier(DB_SCHEMA, "outlet_master")
    ))
    outlets = [{
        "id": row[0],
        "tier": normalize_tier(row[1])
    } for row in cursor.fetchall()]
    
    # Load Menus
    cursor.execute(sql.SQL("SELECT menu_id, category, price_tier_1, price_tier_2, price_tier_3 FROM {};").format(
        sql.Identifier(DB_SCHEMA, "menu_master")
    ))
    menus = [{
        "id": row[0], 
        "category": row[1],
        "tier_1": float(row[2]),
        "tier_2": float(row[3]),
        "tier_3": float(row[4])
    } for row in cursor.fetchall()]
    
    cursor.execute(sql.SQL("SELECT employee_id, outlet_id FROM {} WHERE employee_role = 'CASHIER' AND employment_status = 'ACTIVE';").format(
        sql.Identifier(DB_SCHEMA, "employees")
    ))
    employees_by_outlet = {}
    for employee_id, outlet_id in cursor.fetchall():
        employees_by_outlet.setdefault(outlet_id, []).append(employee_id)

    cursor.execute(sql.SQL("SELECT customer_id FROM {};").format(
        sql.Identifier(DB_SCHEMA, "customers")
    ))
    customer_ids = [row[0] for row in cursor.fetchall()]

    return outlets, menus, employees_by_outlet, customer_ids

def generate_daily_data(target_date_str):
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    is_weekend = target_date.weekday() in [5, 6] # 5 = Sabtu, 6 = Minggu
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    outlets, menus, employees_by_outlet, customer_ids = fetch_master_data(cursor)
    if not outlets or not menus or not employees_by_outlet or not customer_ids:
        print("CRITICAL: Data master belum lengkap. Jalankan seed-master.py terlebih dahulu!")
        return

    # Ambil last order_id untuk kelanjutan sequence transaksi agar tidak tabrakan PK
    cursor.execute(sql.SQL("SELECT COALESCE(MAX(order_id), 0) FROM {};").format(
        sql.Identifier(DB_SCHEMA, "orders")
    ))
    current_order_id = cursor.fetchone()[0] if cursor.description else 0
    if current_order_id is None: current_order_id = 0
    
    cursor.execute(sql.SQL("SELECT COALESCE(MAX(item_id), 0) FROM {};").format(
        sql.Identifier(DB_SCHEMA, "order_items")
    ))
    current_item_id = cursor.fetchone()[0] if cursor.description else 0
    if current_item_id is None: current_item_id = 0

    cursor.execute(sql.SQL("SELECT COALESCE(MAX(payment_id), 0) FROM {};").format(
        sql.Identifier(DB_SCHEMA, "payments")
    ))
    current_payment_id = cursor.fetchone()[0] or 0

    orders_buffer = []
    items_buffer = []
    payments_buffer = []
    
    # --- ANOMALI 2: Tentukan 1 Outlet acak untuk terkena DATA SKEW (Spike 5x lipat) ---
    skewed_outlet_id = random.choice(outlets)["id"]
    
    print(f"-> Memproses simulasi transaksi untuk tanggal: {target_date_str} (Weekend: {is_weekend})")
    
    # Loop Utama melewati 1.000 Outlet
    for outlet in outlets:
        # Determine base volume based on tier (from config, then apply volume_scale)
        tier_key = outlet["tier"].lower().replace(" ", "_")
        tx_min, tx_max = TX_RANGES.get(tier_key, [70, 150])
        tx_count = max(1, int(random.randint(tx_min, tx_max) * VOLUME_SCALE))
            
        # Terapkan Weekend Surge (Multiplier 1.3 - 1.5)
        if is_weekend:
            tx_count = int(tx_count * random.uniform(1.3, 1.5))
            
        # Terapkan Efek Anomali 2 (Data Skew Spike) jika outlet ini terpilih
        if outlet["id"] == skewed_outlet_id:
            tx_count = tx_count * 5
            
        # Loop Transaksi per Toko
        for _ in range(tx_count):
            current_order_id += 1
            
            # Tentukan Jam Transaksi berdasarkan pembobotan Peak Hours
            hours_pool = list(HOURLY_TRAFFIC_WEIGHTS.keys())
            weights_pool = list(HOURLY_TRAFFIC_WEIGHTS.values())
            chosen_hour = random.choices(hours_pool, weights=weights_pool, k=1)[0]
            
            # Buat timestamp transaksi final
            tx_timestamp = datetime(
                target_date.year, target_date.month, target_date.day,
                chosen_hour, random.randint(0, 59), random.randint(0, 59)
            )
            
            # --- ANOMALI 1: Late-Arriving Data (1% Peluang Data Terlambat Mundur 1-2 Hari) ---
            if random.random() < 0.01:
                days_lag = random.choice([1, 2])
                tx_timestamp = tx_timestamp - timedelta(days=days_lag)
                
            cashier_candidates = employees_by_outlet.get(outlet["id"], [])
            if not cashier_candidates:
                raise ValueError(
                    f"Tidak ada cashier aktif untuk outlet_id={outlet['id']}"
                )
            cashier_id = random.choice(cashier_candidates)
            customer_id = random.choice(customer_ids) if random.random() >= 0.15 else None
            payment_method = random.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS, k=1)[0]
            order_status = random.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS, k=1)[0]
            
            # Tentukan berapa banyak variasi item dalam 1 struk belanja (1 s.d 4 menu)
            item_loop_count = random.randint(1, 4)
            
            # Pakai weighted categories untuk market share penjualan produk
            # Coffee: 60%, Non-Coffee: 20%, Pastry: 15%, Heavy Meal: 5%
            menu_weights = []
            for m in menus:
                if m["category"] == "Coffee": menu_weights.append(60)
                elif m["category"] == "Non-Coffee": menu_weights.append(20)
                elif m["category"] == "Pastry": menu_weights.append(15)
                else: menu_weights.append(5)
                
            chosen_menus = random.choices(menus, weights=menu_weights, k=item_loop_count)
            # Hilangkan duplikasi jika dalam 1 struk tidak sengaja memilih menu id yang sama
            chosen_menus = {m["id"]: m for m in chosen_menus}.values()
            
            total_computed_amount = 0.0
            
            # Loop Detail Item (Order Items)
            for menu in chosen_menus:
                current_item_id += 1
                qty = random.randint(1, 3)
                price_per_item = menu[outlet["tier"]] # Ambil harga columnar yang sesuai tier outlet
                subtotal = qty * price_per_item
                total_computed_amount += subtotal
                
                items_buffer.append((
                    current_item_id,
                    current_order_id,
                    menu["id"],
                    qty,
                    price_per_item,
                    subtotal
                ))
                
            # --- ANOMALI 3: Finansial Rounding Error (5% Peluang Ada Selisih Rp1 - Rp5) ---
            final_total_amount = total_computed_amount
            if random.random() < 0.05:
                rounding_delta = random.choice([-5, -3, -1, 1, 3, 5])
                final_total_amount = max(0.0, total_computed_amount + rounding_delta)
                
            orders_buffer.append((
                current_order_id,
                customer_id,
                outlet["id"],
                cashier_id,
                final_total_amount,
                payment_method,
                order_status,
                tx_timestamp
            ))

            current_payment_id += 1
            payment_status = {
                "COMPLETED": "SUCCESS",
                "PENDING": "PENDING",
                "CANCELLED": "FAILED",
                "REFUNDED": "REFUNDED",
            }[order_status]
            payments_buffer.append((
                current_payment_id,
                current_order_id,
                payment_method,
                payment_status,
                final_total_amount,
                tx_timestamp,
                None if payment_method == "CASH" else f"{payment_method}-{current_order_id}",
            ))

    # =========================================================================
    # 3. BULK INGESTION INTO POSTGRESQL
    # =========================================================================
    print(f"-> Memulai injeksi ke Postgres ({len(orders_buffer)} orders, {len(items_buffer)} items)...")
    try:
        query_orders = sql.SQL("""
            INSERT INTO {} (order_id, customer_id, outlet_id, cashier_id, total_amount, payment_method, order_status, created_at)
            VALUES %s ON CONFLICT (order_id) DO NOTHING;
        """).format(sql.Identifier(DB_SCHEMA, "orders"))
        query_items = sql.SQL("""
            INSERT INTO {} (item_id, order_id, menu_id, quantity, price_per_item, subtotal)
            VALUES %s ON CONFLICT (item_id) DO NOTHING;
        """).format(sql.Identifier(DB_SCHEMA, "order_items"))
        query_payments = sql.SQL("""
            INSERT INTO {} (payment_id, order_id, payment_method, payment_status, amount, paid_at, provider_reference)
            VALUES %s ON CONFLICT (payment_id) DO NOTHING;
        """).format(sql.Identifier(DB_SCHEMA, "payments"))
        
        execute_values(cursor, query_orders, orders_buffer)
        execute_values(cursor, query_items, items_buffer)
        execute_values(cursor, query_payments, payments_buffer)
        conn.commit()
        
        print(f"SUCCESS: [{target_date_str}] Tanam {len(orders_buffer)} orders, {len(items_buffer)} items, dan {len(payments_buffer)} payments.")
        print(f"INFO: Outlet ID {skewed_outlet_id} mengalami lonjakan (Skew Spike) hari ini.\n")
        
    except Exception as e:
        conn.rollback()
        print(f"ERROR: Gagal memproses transaksi pada {target_date_str}: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enterprise Transaction Data Generator CLI")
    parser.add_argument("--date", required=True, help="Format tanggal target: YYYY-MM-DD")
    args = parser.parse_args()
    
    generate_daily_data(args.date)
