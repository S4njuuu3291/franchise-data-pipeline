"""
transform_glue.py — Bronze → Silver pipeline (AWS Glue version).

Membaca data dari S3 Bronze bucket, melakukan transformasi & validasi,
lalu menyimpan hasil ke Silver & Quarantine bucket.
"""

import sys
import logging
import time
import os
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.errors import AnalysisException
from pyspark import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from modules.schemas import (
    outlet_schema,
    menu_master_schema,
    orders_schema,
    order_items_schema,
    payments_schema,
    customers_schema,
    employees_schema,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────
# Utama: dari Glue job args (--bronze-bucket, --silver-bucket, --quarantine-bucket)
# Fallback: dari YAML config (development lokal) atau env var
BRONZE_BUCKET = os.environ.get("BRONZE_BUCKET") or "s3a://franchise-pipeline-dev-data-lake-bronze"
SILVER_BUCKET = os.environ.get("SILVER_BUCKET") or "s3a://franchise-pipeline-dev-data-lake-silver"
QUARANTINE_BUCKET = os.environ.get("QUARANTINE_BUCKET") or "s3a://franchise-pipeline-dev-data-lake-quarantine"

def bronze_master_to_silver(spark):
    # ── Master tables (full load, flat path) ──────────────────────────
    outlet_df = spark.read.csv(f"{BRONZE_BUCKET}/outlet_master/", header=True, schema=outlet_schema)
    menu_df   = spark.read.csv(f"{BRONZE_BUCKET}/menu_master/", header=True, schema=menu_master_schema)
    customers_df = spark.read.csv(
        f"{BRONZE_BUCKET}/customers/", header=True, schema=customers_schema
    )
    employees_df = spark.read.csv(
        f"{BRONZE_BUCKET}/employees/", header=True, schema=employees_schema
    )
    
    # ── Write to Silver ───────────────────────────────────────────────
    outlet_df.write \
        .mode("overwrite") \
        .parquet(f"{SILVER_BUCKET}/outlet_master/")
    log.info(f"📤 outlet_master → {SILVER_BUCKET}/outlet_master")
    
    menu_df.write \
        .mode("overwrite") \
        .parquet(f"{SILVER_BUCKET}/menu_master/")
    log.info(f"📤 menu_master → {SILVER_BUCKET}/menu_master/")

    # ── Customers: normalize + semantic validation ───────────────────
    normalized_customers = (
        customers_df
        .withColumn("customer_name", F.trim(F.col("customer_name")))
        .withColumn("email", F.lower(F.trim(F.col("email"))))
        .withColumn(
            "phone",
            F.regexp_replace(F.trim(F.col("phone")), r"[\s().-]", ""),
        )
    )
    valid_email = F.col("email").rlike(
        r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    )
    valid_customer_timestamps = (
        F.col("created_at").isNotNull()
        & F.col("updated_at").isNotNull()
        & (F.col("created_at") <= F.col("updated_at"))
    )
    invalid_customers = normalized_customers.filter(
        ~valid_email | ~valid_customer_timestamps
    )
    valid_customers = normalized_customers.filter(
        valid_email & valid_customer_timestamps
    )
    invalid_customer_count = invalid_customers.count()
    if invalid_customer_count > 0:
        invalid_customers.write \
            .mode("overwrite") \
            .parquet(f"{QUARANTINE_BUCKET}/customers/")
        log.warning(
            "⚠️ %d customers memiliki email atau timestamp tidak valid; "
            "dipindahkan ke quarantine.",
            invalid_customer_count,
        )
    valid_customers.write \
        .mode("overwrite") \
        .parquet(f"{SILVER_BUCKET}/customers/")
    log.info(f"📤 customers → {SILVER_BUCKET}/customers/")

    # ── Employees: normalize + referential/business validation ───────
    normalized_employees = (
        employees_df
        .withColumn("employee_name", F.trim(F.col("employee_name")))
        .withColumn("employee_role", F.upper(F.trim(F.col("employee_role"))))
        .withColumn(
            "employment_status",
            F.upper(F.trim(F.col("employment_status"))),
        )
    )
    valid_employee_status = F.col("employment_status").isin("ACTIVE", "INACTIVE")
    employees_with_outlet = normalized_employees.join(
        outlet_df.select("outlet_id")
        .dropDuplicates()
        .withColumn("_outlet_exists", F.lit(True)),
        on="outlet_id",
        how="left",
    )
    valid_employees = employees_with_outlet.filter(
        F.col("_outlet_exists").isNotNull() & valid_employee_status
    ).drop("_outlet_exists")
    invalid_employees = employees_with_outlet.filter(
        F.col("_outlet_exists").isNull() | ~valid_employee_status
    ).drop("_outlet_exists")
    invalid_employee_count = invalid_employees.count()
    if invalid_employee_count > 0:
        invalid_employees.write \
            .mode("overwrite") \
            .parquet(f"{QUARANTINE_BUCKET}/employees/")
        log.warning(
            "⚠️ %d employees memiliki outlet atau employment_status tidak valid; "
            "dipindahkan ke quarantine.",
            invalid_employee_count,
        )
    valid_employees.write \
        .mode("overwrite") \
        .parquet(f"{SILVER_BUCKET}/employees/")
    log.info(f"📤 employees → {SILVER_BUCKET}/employees/")

    return outlet_df, menu_df

def bronze_to_silver(spark, date, outlet_df, menu_df):
    """Load transaction CSV dari Bronze, transform, lalu write ke Silver.

    Missing transaction partitions are treated as a skippable condition so a
    backfill can continue processing the remaining dates.
    """
    partition = f"year={date[:4]}/month={date[5:7]}/day={date[8:10]}"
    orders_path = f"{BRONZE_BUCKET}/orders/{partition}/"
    order_items_path = f"{BRONZE_BUCKET}/order_items/{partition}/"
    payments_path = f"{BRONZE_BUCKET}/payments/{partition}/"
    
    # ── Transaction tables (partitioned path) ─────────────────────────
    try:
        orders_df = spark.read.csv(
            orders_path, header=True, schema=orders_schema
        )
        order_items_df = spark.read.csv(
            order_items_path, header=True, schema=order_items_schema
        )
        payments_df = spark.read.csv(
            payments_path, header=True, schema=payments_schema
        )
    except AnalysisException as exc:
        if "PATH_NOT_FOUND" not in str(exc):
            raise

        log.warning(
            "Skipping date %s: transaction Bronze partition is missing. "
            "orders=%s, order_items=%s, payments=%s",
            date,
            orders_path,
            order_items_path,
            payments_path,
        )
        return False

    # Check orders total_amount vs sum of order_items subtotal
    order_items_agg = order_items_df.groupBy("order_id").sum("subtotal").withColumnRenamed("sum(subtotal)", "calculated_total")
    orders_with_calc = orders_df.join(order_items_agg, on="order_id", how="left")

    null_calc = orders_with_calc.filter(F.col("calculated_total").isNull()).count()
    if null_calc > 0:
        log.warning(f"⚠️ {null_calc} order tidak memiliki order_items (calculated_total = NULL).")

    discrepancies = orders_with_calc.filter(
        F.col("calculated_total").isNotNull() &
        (F.col("total_amount") != F.col("calculated_total"))
    )
    discrepancy_count = discrepancies.count()
    if discrepancy_count > 0:
        log.warning(f"⚠️ Ditemukan {discrepancy_count} order dengan total_amount tidak sesuai dengan sum(subtotal) di order_items.")
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

    # 3. Cek harga sesuai tier: price_per_item harus cocok dengan salah satu tier di menu_master
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

    # 4. Cek cashier anomaly — cashier dengan jumlah transaksi ekstrem (z-score > 3)
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
                    F.when(
                        (F.col("calculated_total").isNotNull()) &
                        (F.col("total_amount") == F.col("calculated_total")),
                        "valid"
                    ).otherwise("MISMATCH TOTAL AMOUNT")) \
        .select(
            "order_id",
            "customer_id",
            "outlet_id",
            "cashier_id",
            "total_amount",
            "payment_method",
            "order_status",
            "created_at",
            "data_quality_status",
        )

    silver_orders_df.write \
        .mode("overwrite") \
        .parquet(f"{SILVER_BUCKET}/orders/{partition}/")
    log.info(f"📤 orders → {SILVER_BUCKET}/orders/{partition}/")
    
    order_items_df.write \
        .mode("overwrite") \
        .parquet(f"{SILVER_BUCKET}/order_items/{partition}/")
    log.info(f"📤 order_items → {SILVER_BUCKET}/order_items/{partition}/")

    # ── Payments: referential integrity ke orders ─────────────────────
    known_order_ids = orders_df.select("order_id").dropDuplicates()
    orphan_payments = payments_df.join(
        known_order_ids,
        on="order_id",
        how="left_anti",
    )
    valid_payments = payments_df.join(
        known_order_ids,
        on="order_id",
        how="left_semi",
    )
    orphan_payment_count = orphan_payments.count()
    if orphan_payment_count > 0:
        orphan_payments.write \
            .mode("overwrite") \
            .parquet(f"{QUARANTINE_BUCKET}/orphan_payments/{partition}/")
        log.warning(
            "⚠️ Ditemukan %d payments dengan order_id yang tidak ada di orders; "
            "dipindahkan ke quarantine.",
            orphan_payment_count,
        )
        log.info(
            "📤 Orphan payments → %s/orphan_payments/%s/",
            QUARANTINE_BUCKET,
            partition,
        )
    else:
        log.info("✅ Semua payment order_id memiliki pasangan di orders.")

    valid_payments.write \
        .mode("overwrite") \
        .parquet(f"{SILVER_BUCKET}/payments/{partition}/")
    log.info(f"📤 payments → {SILVER_BUCKET}/payments/{partition}/")

    # ── Quarantine Write ───────────────────────────────
    discrepancies.write \
        .mode("overwrite") \
        .parquet(f"{QUARANTINE_BUCKET}/orders_discrepancies/{partition}/")
    log.info(f"📤 Discrepancies orders → {QUARANTINE_BUCKET}/orders_discrepancies/{partition}/")
    return True

def date_range(start_str, end_str):
    """Yield dates from start to end inclusive."""
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    current = start
    while current <= end:
        yield current.strftime("%Y-%m-%d")
        current += timedelta(days=1)


def main():
    # ── Glue Init ─────────────────────────────────────────────────────
    # JOB_NAME otomatis dari AWS Glue, fallback "local" untuk development
    raw_args = {}
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith("--") and "=" in arg:
            # Format: --key=value
            k, v = arg.split("=", 1)
            raw_args[k] = v
        elif arg.startswith("--") and i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
            # Format: --key value
            raw_args[arg] = sys.argv[i + 1]
            i += 1
        i += 1
    job_name = raw_args.get("--JOB_NAME") or raw_args.get("JOB_NAME", "local")

    sc = SparkContext.getOrCreate()
    sc.setLogLevel("WARN")

    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    job = Job(glueContext)
    job.init(job_name, raw_args)

    log.info(f"✅ Glue Spark ready — v{spark.version}")

    # ── Override bucket names from Glue job args ──────────────────────
    if raw_args.get("--bronze-bucket"):
        global BRONZE_BUCKET, SILVER_BUCKET, QUARANTINE_BUCKET
        BRONZE_BUCKET = f"s3a://{raw_args['--bronze-bucket']}"
        SILVER_BUCKET = f"s3a://{raw_args['--silver-bucket']}"
        QUARANTINE_BUCKET = f"s3a://{raw_args['--quarantine-bucket']}"

    # ── Parse dates ───────────────────────────────────────────────────
    today = datetime.utcnow().strftime("%Y-%m-%d")
    raw_date = raw_args.get("--date", "")
    raw_start = raw_args.get("--start-date", "")
    raw_end = raw_args.get("--end-date", "")

    if raw_date:
        start_date = end_date = raw_date
    elif raw_start and raw_end:
        start_date, end_date = raw_start, raw_end
    elif raw_start:
        start_date = end_date = raw_start
    else:
        start_date = end_date = today

    log.info(f"Rentang transformasi: {start_date} → {end_date}")

    # ── Pipeline ──────────────────────────────────────────────────────
    total_start = time.time()

    outlet_df, menu_df = bronze_master_to_silver(spark)

    processed_dates = 0
    skipped_dates = 0

    for date in date_range(start_date, end_date):
        log.info(f"━━━ Processing date: {date} ━━━")
        processed = bronze_to_silver(spark, date, outlet_df, menu_df)
        if processed:
            processed_dates += 1
        else:
            skipped_dates += 1

    elapsed = time.time() - total_start
    log.info(
        "✅ All done in %.2fs — processed_dates=%d, skipped_dates=%d",
        elapsed,
        processed_dates,
        skipped_dates,
    )

    job.commit()


if __name__ == "__main__":
    main()
