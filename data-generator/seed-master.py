import os
import random
from datetime import datetime
from faker import Faker
import psycopg2
from psycopg2.extras import execute_values

# =========================================================================
# 1. KONSTANTA DATA MASTER (ENTERPRISE COLUMNAR STANDARD)
# =========================================================================

REGION_CITY_POOL = {
    "Tier 1": ["Jakarta", "Surabaya", "Medan", "Tangerang", "Semarang"],
    "Tier 2": ["Bandung", "Malang", "Makassar", "Yogyakarta", "Palembang"],
    "Tier 3": ["Bogor", "Jember", "Binjai", "Sidoarjo", "Cirebon"]
}

# Menu mengunci harga dasar dan variasi harga per kolom tier
MENU_TEMPLATES = [
    # === CATEGORY: COFFEE (15 MENUS) ===
    {"name": "Es Kopi Susu Aren", "category": "Coffee", "base_price": 11000.00, "t1": 24000.00, "t2": 20000.00, "t3": 16000.00},
    {"name": "Cafe Latte Ice", "category": "Coffee", "base_price": 13000.00, "t1": 28000.00, "t2": 24000.00, "t3": 19000.00},
    {"name": "Americano Ice", "category": "Coffee", "base_price": 9000.00, "t1": 22000.00, "t2": 18000.00, "t3": 15000.00},
    {"name": "Caramel Macchiato", "category": "Coffee", "base_price": 16000.00, "t1": 36000.00, "t2": 32000.00, "t3": 26000.00},
    {"name": "Vanilla Latte Ice", "category": "Coffee", "base_price": 14000.00, "t1": 32000.00, "t2": 28000.00, "t3": 22000.00},
    {"name": "Hazelnut Latte", "category": "Coffee", "base_price": 14000.00, "t1": 32000.00, "t2": 28000.00, "t3": 22000.00},
    {"name": "Cappuccino Hot", "category": "Coffee", "base_price": 12000.00, "t1": 26000.00, "t2": 22000.00, "t3": 18000.00},
    {"name": "Mocha Latte Ice", "category": "Coffee", "base_price": 15000.00, "t1": 34000.00, "t2": 30000.00, "t3": 24000.00},
    {"name": "Espresso Shot", "category": "Coffee", "base_price": 6000.00, "t1": 15000.00, "t2": 12000.00, "t3": 10000.00},
    {"name": "Cold Brew Original", "category": "Coffee", "base_price": 13000.00, "t1": 29000.00, "t2": 25000.00, "t3": 20000.00},
    {"name": "Avocado Coffee Float", "category": "Coffee", "base_price": 18000.00, "t1": 39000.00, "t2": 35000.00, "t3": 29000.00},
    {"name": "Spanish Latte", "category": "Coffee", "base_price": 14000.00, "t1": 30000.00, "t2": 26000.00, "t3": 21000.00},
    {"name": "Kopi Susu Kampong Hot", "category": "Coffee", "base_price": 8000.00, "t1": 19000.00, "t2": 16000.00, "t3": 13000.00},
    {"name": "Affogato Style", "category": "Coffee", "base_price": 11000.00, "t1": 25000.00, "t2": 21000.00, "t3": 17000.00},
    {"name": "Salted Caramel Cold Foam", "category": "Coffee", "base_price": 17000.00, "t1": 38000.00, "t2": 34000.00, "t3": 28000.00},

    # === CATEGORY: NON-COFFEE (12 MENUS) ===
    {"name": "Matcha Latte Premium", "category": "Non-Coffee", "base_price": 14000.00, "t1": 29000.00, "t2": 25000.00, "t3": 21000.00},
    {"name": "Chocolate Signature Ice", "category": "Non-Coffee", "base_price": 13000.00, "t1": 28000.00, "t2": 24000.00, "t3": 19000.00},
    {"name": "Red Velvet Latte Ice", "category": "Non-Coffee", "base_price": 13000.00, "t1": 28000.00, "t2": 24000.00, "t3": 19000.00},
    {"name": "Taro Milk Tea", "category": "Non-Coffee", "base_price": 12000.00, "t1": 26000.00, "t2": 22000.00, "t3": 18000.00},
    {"name": "Earl Grey Milk Tea", "category": "Non-Coffee", "base_price": 11000.00, "t1": 25000.00, "t2": 21000.00, "t3": 17000.00},
    {"name": "Iced Lychee Tea", "category": "Non-Coffee", "base_price": 9000.00, "t1": 22000.00, "t2": 19000.00, "t3": 15000.00},
    {"name": "Iced Lemon Tea", "category": "Non-Coffee", "base_price": 7000.00, "t1": 18000.00, "t2": 15000.00, "t3": 12000.00},
    {"name": "Mango Yakult Smoothie", "category": "Non-Coffee", "base_price": 15000.00, "t1": 32000.00, "t2": 28000.00, "t3": 23000.00},
    {"name": "Strawberry Mojito Ice", "category": "Non-Coffee", "base_price": 12000.00, "t1": 27000.00, "t2": 23000.00, "t3": 18000.00},
    {"name": "Cookies and Cream Frappe", "category": "Non-Coffee", "base_price": 16000.00, "t1": 35000.00, "t2": 31000.00, "t3": 25000.00},
    {"name": "Mineral Water 600ml", "category": "Non-Coffee", "base_price": 3000.00, "t1": 9000.00, "t2": 7000.00, "t3": 5000.00},
    {"name": "Thai Tea Original", "category": "Non-Coffee", "base_price": 9000.00, "t1": 20000.00, "t2": 17000.00, "t3": 14000.00},

    # === CATEGORY: PASTRY (7 MENUS) ===
    {"name": "Butter Croissant", "category": "Pastry", "base_price": 12000.00, "t1": 25000.00, "t2": 21000.00, "t3": 18000.00},
    {"name": "Chocolate Danish", "category": "Pastry", "base_price": 14000.00, "t1": 28000.00, "t2": 24000.00, "t3": 20000.00},
    {"name": "Cinnamon Roll", "category": "Pastry", "base_price": 13000.00, "t1": 26000.00, "t2": 22000.00, "t3": 19000.00},
    {"name": "Almond Croissant", "category": "Pastry", "base_price": 16000.00, "t1": 32000.00, "t2": 28000.00, "t3": 23000.00},
    {"name": "Fudgy Brownie Bar", "category": "Pastry", "base_price": 11000.00, "t1": 22000.00, "t2": 18000.00, "t3": 15000.00},
    {"name": "Cheese Choux Pastry", "category": "Pastry", "base_price": 10000.00, "t1": 20000.00, "t2": 17000.00, "t3": 14000.00},
    {"name": "Smoked Beef Croissant", "category": "Pastry", "base_price": 17000.00, "t1": 34000.00, "t2": 30000.00, "t3": 25000.00},

    # === CATEGORY: HEAVY MEAL (6 MENUS) ===
    {"name": "Nasi Goreng Kampoeng", "category": "Heavy Meal", "base_price": 18000.00, "t1": 38000.00, "t2": 32000.00, "t3": 27000.00},
    {"name": "Spaghetti Carbonara", "category": "Heavy Meal", "base_price": 22000.00, "t1": 45000.00, "t2": 39000.00, "t3": 32000.00},
    {"name": "Spaghetti Aglio Olio", "category": "Heavy Meal", "base_price": 19000.00, "t1": 40000.00, "t2": 35000.00, "t3": 29000.00},
    {"name": "Chicken Katsu Don", "category": "Heavy Meal", "base_price": 20000.00, "t1": 42000.00, "t2": 36000.00, "t3": 30000.00},
    {"name": "Club Sandwich & Fries", "category": "Heavy Meal", "base_price": 17000.00, "t1": 36000.00, "t2": 31000.00, "t3": 25000.00},
    {"name": "Mie Goreng Tek-Tek Premium", "category": "Heavy Meal", "base_price": 15000.00, "t1": 32000.00, "t2": 27000.00, "t3": 22000.00}
]

START_TIMESTAMP = datetime(2026, 2, 25, 6, 0, 0)

# =========================================================================
# 2. FUNGSI UTAMA SEEDING
# =========================================================================

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port="5431",
        user="replicator_user",
        password="supersecretpassword",
        database="main_db"
    )

def seed_outlets(cursor):
    print("-> Men-generate 1.000 data outlet_master...")
    fake = Faker('id_ID')
    outlets_data = []

    for i in range(1, 1001):
        if i <= 400:
            tier = "Tier 1"
        elif i <= 800:
            tier = "Tier 2"
        else:
            tier = "Tier 3"
            
        city = random.choice(REGION_CITY_POOL[tier])
        outlet_name = f"Cafe {fake.street_name()}"
        
        outlets_data.append((i, outlet_name, city, tier, START_TIMESTAMP, START_TIMESTAMP))

    query = """
        INSERT INTO outlet_master (outlet_id, outlet_name, city, region_tier, created_at, updated_at)
        VALUES %s
        ON CONFLICT (outlet_id) DO NOTHING;
    """
    execute_values(cursor, query, outlets_data)
    print("SUCCESS: 1.000 outlet berhasil ditanam.")

def seed_menu_master(cursor):
    print("-> Men-generate 40 data menu_master dengan skema Columnar Pricing...")
    menus_data = []
    
    for idx, menu in enumerate(MENU_TEMPLATES, start=1):
        menus_data.append((
            idx, 
            menu["name"], 
            menu["category"], 
            menu["base_price"], 
            menu["t1"], # price_tier_1
            menu["t2"], # price_tier_2
            menu["t3"], # price_tier_3
            False,      # is_promo_active
            START_TIMESTAMP
        ))
        
    query = """
        INSERT INTO menu_master (menu_id, menu_name, category, base_price, price_tier_1, price_tier_2, price_tier_3, is_promo_active, updated_at)
        VALUES %s
        ON CONFLICT (menu_id) DO NOTHING;
    """
    execute_values(cursor, query, menus_data)
    print(f"SUCCESS: {len(menus_data)} baris menu master berhasil ditanam.")

def main():
    print("=== MEMULAI PROSES SEEDING DATA MASTER HULU ===")
    start_time = datetime.now()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            seed_outlets(cursor)
            seed_menu_master(cursor)
            conn.commit()
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"=== SEEDING SELESAI: DATABASE UTAMA SIAP ===")
            print(f"⏱  Waktu eksekusi: {duration:.2f} detik")
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"CRITICAL ERROR: Proses seeding gagal akibat: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()