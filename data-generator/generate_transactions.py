import argparse
import random
import yaml
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

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

PAYMENT_METHODS = ["QRIS", "GoPay", "OVO", "Debit Card", "Credit Card", "Cash"]
PAYMENT_WEIGHTS = [40, 20, 15, 12, 8, 5] # Mayoritas cashless sesuai realitas urban

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port="5431",
        user="replicator_user",
        password="supersecretpassword",
        database="main_db"
    )

# =========================================================================
# 2. CORE ENGINE GENERATOR
# =========================================================================

def fetch_master_data(cursor):
    """Mengambil data master dari DB untuk disimpan di memori Python (Caching)"""
    # Load Outlets
    cursor.execute("SELECT outlet_id, region_tier FROM outlet_master;")
    outlets = [{"id": row[0], "tier": row[1]} for row in cursor.fetchall()]
    
    # Load Menus
    cursor.execute("SELECT menu_id, category, price_tier_1, price_tier_2, price_tier_3 FROM menu_master;")
    menus = [{
        "id": row[0], 
        "category": row[1],
        "Tier 1": float(row[2]),
        "Tier 2": float(row[3]),
        "Tier 3": float(row[4])
    } for row in cursor.fetchall()]
    
    return outlets, menus

def generate_daily_data(target_date_str):
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    is_weekend = target_date.weekday() in [5, 6] # 5 = Sabtu, 6 = Minggu
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    outlets, menus = fetch_master_data(cursor)
    if not outlets or not menus:
        print("CRITICAL: Data master kosong. Jalankan seed_master.py terlebih dahulu!")
        return

    # Ambil last order_id untuk kelanjutan sequence transaksi agar tidak tabrakan PK
    cursor.execute("SELECT COALESCE(MAX(order_id), 0) FROM orders;")
    current_order_id = cursor.fetchone()[0] if cursor.description else 0
    if current_order_id is None: current_order_id = 0
    
    cursor.execute("SELECT COALESCE(MAX(item_id), 0) FROM order_items;")
    current_item_id = cursor.fetchone()[0] if cursor.description else 0
    if current_item_id is None: current_item_id = 0

    orders_buffer = []
    items_buffer = []
    
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
                
            cashier_id = random.randint(101, 108) # Simulasi 8 kasir bergantian per outlet
            payment_method = random.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS, k=1)[0]
            
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
                outlet["id"],
                cashier_id,
                final_total_amount,
                payment_method,
                tx_timestamp
            ))

    # =========================================================================
    # 3. BULK INGESTION INTO POSTGRESQL
    # =========================================================================
    print(f"-> Memulai injeksi ke Postgres ({len(orders_buffer)} orders, {len(items_buffer)} items)...")
    try:
        query_orders = """
            INSERT INTO orders (order_id, outlet_id, cashier_id, total_amount, payment_method, created_at)
            VALUES %s ON CONFLICT (order_id) DO NOTHING;
        """
        query_items = """
            INSERT INTO order_items (item_id, order_id, menu_id, quantity, price_per_item, subtotal)
            VALUES %s ON CONFLICT (item_id) DO NOTHING;
        """
        
        execute_values(cursor, query_orders, orders_buffer)
        execute_values(cursor, query_items, items_buffer)
        conn.commit()
        
        print(f"SUCCESS: [{target_date_str}] Tanam {len(orders_buffer)} Struk & {len(items_buffer)} Item Baris Selesai.")
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