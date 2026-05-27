"""
transform.py — Bronze → Silver pipeline.

Membaca data Parquet dari MinIO Bronze bucket, melakukan transformasi,
lalu menyimpan hasil ke Silver bucket.
"""

import sys
import logging
import time
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
sys.path.insert(0, "..")
from schemas import outlet_schema, menu_master_schema, orders_schema, order_items_schema

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────
BRONZE_BUCKET = "s3a://franchise-pipeline-data-lake-bronze"
SILVER_BUCKET = "s3a://franchise-pipeline-data-lake-silver"
QUARANTINE_BUCKET = "s3a://franchise-pipeline-data-lake-quarantine"


def bronze_to_silver(spark, date):
    """Load Parquet dari Bronze → transform → write ke Silver."""
    partition = f"year={date[:4]}/month={date[5:7]}/day={date[8:10]}"

    # ── Master tables (full load, flat path) ──────────────────────────
    outlet_df = spark.read.csv(f"{BRONZE_BUCKET}/outlet_master/{partition}/", header=True, schema=outlet_schema)
    menu_df   = spark.read.csv(f"{BRONZE_BUCKET}/menu_master/{partition}/", header=True, schema=menu_master_schema)

    # ── Transaction tables (partitioned path) ─────────────────────────
    orders_df = spark.read.csv(
        f"{BRONZE_BUCKET}/orders/{partition}/", header=True, schema=orders_schema)

    order_items_df = spark.read.csv(
        f"{BRONZE_BUCKET}/order_items/{partition}/", header=True, schema=order_items_schema)
    

    # Check orders total_amount vs sum of order_items subtotal
    order_items_agg = order_items_df.groupBy("order_id").sum("subtotal").withColumnRenamed("sum(subtotal)", "calculated_total")
    orders_with_calc = orders_df.join(order_items_agg, on="order_id", how="left")
    discrepancies = orders_with_calc.filter(orders_with_calc.total_amount != orders_with_calc.calculated_total)
    if discrepancies.count() > 0:
        log.warning(f"⚠️ Ditemukan {discrepancies.count()} order dengan total_amount tidak sesuai dengan sum(subtotal) di order_items.")
    else:
        log.info("✅ Semua order memiliki total_amount yang sesuai dengan sum(subtotal) di order_items.")

    # ── Business Logic: Validasi Referential Integrity ─────────────────

    # 1. Cek menu_id di order_items apakah ada di menu_master
    orphan_items = order_items_df \
        .join(menu_df.select("menu_id"), on="menu_id", how="left_anti")
    orphan_count = orphan_items.count()
    if orphan_count > 0:
        log.warning(f"⚠️ Ditemukan {orphan_count} order_items dengan menu_id tidak ada di menu_master.")
        orphan_items.write \
            .mode("overwrite") \
            .parquet(f"{QUARANTINE_BUCKET}/orphan_items/{partition}/")
        log.info(f"📤 Orphan items → {QUARANTINE_BUCKET}/orphan_items/{partition}/")
    else:
        log.info("✅ Semua menu_id di order_items valid (ada di menu_master).")

    # 2. Cek outlet_id di orders apakah ada di outlet_master
    orphan_orders = orders_df \
        .join(outlet_df.select("outlet_id"), on="outlet_id", how="left_anti")
    if orphan_orders.count() > 0:
        log.warning(f"⚠️ Ditemukan {orphan_orders.count()} orders dengan outlet_id tidak ada di outlet_master.")
    else:
        log.info("✅ Semua outlet_id di orders valid (ada di outlet_master).")

    # 3. Cek payment_method apakah nilai yang valid
    valid_payments = ["Cash", "Credit Card", "Debit Card", "GoPay", "OVO", "QRIS"]
    invalid_payments = orders_df.filter(~F.col("payment_method").isin(valid_payments))
    invalid_count = invalid_payments.count()
    if invalid_count > 0:
        log.warning(f"⚠️ Ditemukan {invalid_count} orders dengan payment_method tidak dikenal.")
        invalid_payments.select("order_id", "payment_method").show(5, truncate=False)
        invalid_payments.write \
            .mode("overwrite") \
            .parquet(f"{QUARANTINE_BUCKET}/invalid_payments/{partition}/")
        log.info(f"📤 Invalid payments → {QUARANTINE_BUCKET}/invalid_payments/{partition}/")
    else:
        log.info("✅ Semua payment_method valid.")

    # 4. Cek harga sesuai tier: price_per_item harus cocok dengan salah satu tier di menu_master
    items_with_menu = order_items_df \
        .join(menu_df.select("menu_id", "base_price", "price_tier_1", "price_tier_2", "price_tier_3"),
              on="menu_id", how="left") \
        .withColumn("price_valid",
                    (F.col("price_per_item") == F.col("base_price")) |
                    (F.col("price_per_item") == F.col("price_tier_1")) |
                    (F.col("price_per_item") == F.col("price_tier_2")) |
                    (F.col("price_per_item") == F.col("price_tier_3")))
    invalid_prices = items_with_menu.filter(~F.col("price_valid"))
    invalid_price_count = invalid_prices.count()
    if invalid_price_count > 0:
        log.warning(f"⚠️ Ditemukan {invalid_price_count} order_items dengan harga tidak sesuai tier.")
        invalid_prices.select("item_id", "menu_id", "price_per_item", "base_price",
                              "price_tier_1", "price_tier_2", "price_tier_3").show(5, truncate=False)
        invalid_prices.write \
            .mode("overwrite") \
            .parquet(f"{QUARANTINE_BUCKET}/invalid_prices/{partition}/")
        log.info(f"📤 Invalid prices → {QUARANTINE_BUCKET}/invalid_prices/{partition}/")
    else:
        log.info("✅ Semua price_per_item sesuai dengan tier yang tersedia.")

    # 5. Cek duplicate order_id
    dup_orders = orders_df.groupBy("order_id").count().filter(F.col("count") > 1)
    dup_count = dup_orders.count()
    if dup_count > 0:
        log.warning(f"⚠️ Ditemukan {dup_count} order_id yang duplikat.")
        dup_orders.write \
            .mode("overwrite") \
            .parquet(f"{QUARANTINE_BUCKET}/duplicate_orders/{partition}/")
        log.info(f"📤 Duplicate orders → {QUARANTINE_BUCKET}/duplicate_orders/{partition}/")
    else:
        log.info("✅ Tidak ada order_id duplikat.")

    # 6. Cek cashier anomaly — cashier dengan jumlah transaksi ekstrem (z-score > 3)
    cashier_stats = orders_df.groupBy("cashier_id") \
        .agg(F.count("order_id").alias("tx_count"))
    stats = cashier_stats.select(
        F.mean("tx_count").alias("mean"),
        F.stddev("tx_count").alias("stddev")
    ).collect()[0]
    mean_tx = stats["mean"]
    stddev_tx = stats["stddev"] if stats["stddev"] is not None else 0
    if stddev_tx > 0:
        threshold = mean_tx + 3 * stddev_tx
        anomaly_cashiers = cashier_stats.filter(F.col("tx_count") > threshold)
        anomaly_count = anomaly_cashiers.count()
        if anomaly_count > 0:
            log.warning(f"⚠️ Ditemukan {anomaly_count} cashier dengan transaksi mencurigakan (> {threshold:.0f} tx).")
            anomaly_cashiers.show(5, truncate=False)
            anomaly_cashiers.write \
                .mode("overwrite") \
                .parquet(f"{QUARANTINE_BUCKET}/anomaly_cashiers/{partition}/")
            log.info(f"📤 Anomaly cashiers → {QUARANTINE_BUCKET}/anomaly_cashiers/{partition}/")
        else:
            log.info("✅ Tidak ada cashier anomaly.")
    else:
        log.info("✅ Data terlalu sedikit untuk deteksi anomaly cashier.")

    silver_orders_df = orders_with_calc \
        .withColumn("data_quality_status",
                    F.when(F.col("total_amount") == F.col("calculated_total"), "valid")
                     .otherwise("MISMATCH TOTAL AMOUNT")) \
        .select("order_id", "outlet_id", "cashier_id", "total_amount",
                "payment_method", "created_at", "data_quality_status")

    # ── Write to Silver ───────────────────────────────────────────────
    outlet_df.write \
        .mode("overwrite") \
        .parquet(f"{SILVER_BUCKET}/outlet_master/{partition}/")
    log.info(f"📤 outlet_master → {SILVER_BUCKET}/outlet_master")
    
    menu_df.write \
        .mode("overwrite") \
        .parquet(f"{SILVER_BUCKET}/menu_master/{partition}/")
    log.info(f"📤 menu_master → {SILVER_BUCKET}/menu_master/{partition}/")

    silver_orders_df.write \
        .mode("overwrite") \
        .parquet(f"{SILVER_BUCKET}/orders/{partition}/")
    log.info(f"📤 orders → {SILVER_BUCKET}/orders/{partition}/")
    
    order_items_df.write \
        .mode("overwrite") \
        .parquet(f"{SILVER_BUCKET}/order_items/{partition}/")

    # ── Quarantine Write (jika ada data tidak valid) ───────────────────────────────
    if discrepancies.count() > 0:
        discrepancies.write \
            .mode("overwrite") \
            .parquet(f"{QUARANTINE_BUCKET}/orders_discrepancies/{partition}/")
        log.info(f"📤 Discrepancies orders → {QUARANTINE_BUCKET}/orders_discrepancies/{partition}/")

def main():
    spark = SparkSession.builder.remote("sc://localhost:15002").appName("Bronze-To-Silver-Transform").getOrCreate()
    log.info(f"✅ Spark ready — v{spark.version}")

    start_date = "2026-02-25"
    end_date   = "2026-02-25"

    total_start = time.time()

    for date in [start_date, end_date]:
        log.info(f"━━━ Processing date: {date} ━━━")
        bronze_to_silver(spark, date)

        break

    elapsed = time.time() - total_start
    log.info(f"✅ All done in {elapsed:.2f}s")
    spark.stop()


if __name__ == "__main__":
    main()
