import argparse
import logging
import os
from datetime import datetime

import great_expectations as gx
from great_expectations.exceptions.exceptions import NoAvailableBatchesError
from pyspark.sql import SparkSession
import yaml

# ── 1. LOGGING & ARGUMENT PARSER ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)
logging.getLogger("great_expectations").setLevel(logging.WARNING)

parser = argparse.ArgumentParser(description="Run the GX Silver quality gate")
parser.add_argument("--date", required=True, help="Tanggal data dengan format YYYY-MM-DD")
args = parser.parse_args()

execution_date = datetime.strptime(args.date, "%Y-%m-%d")
year = execution_date.strftime("%Y")
month = execution_date.strftime("%m")
day = execution_date.strftime("%d")

# ── 2. LOAD CONFIGURATION ─────────────────────────────────────────────
config_path = os.environ.get("PIPELINE_CONFIG_PATH") or os.path.join(
    os.path.dirname(__file__), "../../config/pipeline-config.yaml"
)
with open(config_path) as config_file:
    config = yaml.safe_load(config_file)["storage"]

# Alamat S3 menggunakan protokol s3a://
bucket_base = f"s3a://{config['silver']}"

# ── 3. INISIALISASI SPARK SESSION DENGAN CONFIG S3A UTUH ──────────────
# Di sini kuncinya: kita sertakan packages maven agar Spark otomatis mendownload JAR runtime ke laptop
spark = SparkSession.builder \
    .appName("GX_Silver_Validation") \
    .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain") \
    .config("spark.hadoop.fs.s3a.connection.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.connection.establish.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.connection.socket.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.threads.keepalivetime", "60") \
    .config("spark.hadoop.fs.s3a.multipart.purge.age", "86400") \
    .config("spark.hadoop.fs.s3a.connection.acquisition.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.connection.idle.time", "60000") \
    .config("spark.hadoop.fs.s3a.connection.request.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.connection.ttl", "300000") \
    .getOrCreate()

# ── 4. INITIALIZE GX CONTEXT & IKAT SPARK SESSION ─────────────────────
context = gx.get_context(mode="file")

# Bersihkan sisa datasource lama jika ada
for old_ds in ["silver_spark_data", "silver_in_memory_data"]:
    try:
        context.data_sources.delete(name=old_ds)
    except ValueError:
        pass

# GX membuat Spark Data Source sendiri dan menggunakan Spark context aktif.
# Parameter `spark` bukan parameter valid pada GX Core 1.x.
datasource = context.data_sources.add_spark(
    name="silver_in_memory_data",
    force_reuse_spark_context=True,
)

# ── 5. DAFTARKAN DIRECTORY ASSETS LEWAT SPARK S3A ─────────────────────
logger.info("Membaca data Silver Parquet langsung dari S3 via Spark S3A...")
df_menu = spark.read.parquet(f"{bucket_base}/menu_master/")
df_outlet = spark.read.parquet(f"{bucket_base}/outlet_master/")

orders_path = f"{bucket_base}/orders/year={year}/month={month}/day={day}/"
order_items_path = f"{bucket_base}/order_items/year={year}/month={month}/day={day}/"
df_orders = spark.read.parquet(orders_path)
df_order_items = spark.read.parquet(order_items_path)

# Daftarkan ke GX sebagai Dataframe Asset
menu_asset = datasource.add_dataframe_asset(name="menu_silver_asset")
outlet_asset = datasource.add_dataframe_asset(name="outlet_silver_asset")
orders_asset = datasource.add_dataframe_asset(name="orders_silver_asset")
order_items_asset = datasource.add_dataframe_asset(name="order_items_silver_asset")

# Definisikan Batch
menu_definition = menu_asset.add_batch_definition_whole_dataframe(name="menu_def")
outlet_definition = outlet_asset.add_batch_definition_whole_dataframe(name="outlet_def")
orders_definition = orders_asset.add_batch_definition_whole_dataframe(name="orders_def")
order_items_definition = order_items_asset.add_batch_definition_whole_dataframe(name="order_items_def")

# Ambil Batch dengan menyertakan runtime dataframe yang dibaca lewat S3A tadi
# ── 6. CREATE EXPECTATION SUITES ──────────────────────────────────────
def add_smoke_suite(name, columns, key_columns):
    suite = gx.ExpectationSuite(name=name)
    suite.add_expectation(gx.expectations.ExpectTableColumnsToMatchSet(column_set=columns, exact_match=True))
    suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))
    for column in key_columns:
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=column))
    context.suites.add_or_update(suite)
    return suite

menu_suite = add_smoke_suite(
    "silver_menu_master_suite",
    ["menu_id", "menu_name", "category", "base_price", "price_tier_1", "price_tier_2", "price_tier_3", "is_promo_active", "updated_at"],
    ["menu_id"],
)
outlet_suite = add_smoke_suite(
    "silver_outlet_master_suite",
    ["outlet_id", "outlet_name", "city", "region_tier", "created_at", "updated_at"],
    ["outlet_id"],
)
orders_suite = add_smoke_suite(
    "silver_orders_suite",
    ["order_id", "outlet_id", "cashier_id", "total_amount", "payment_method", "created_at", "data_quality_status"],
    ["order_id", "outlet_id", "created_at"],
)
order_items_suite = add_smoke_suite(
    "silver_order_items_suite",
    ["item_id", "order_id", "menu_id", "quantity", "price_per_item", "subtotal"],
    ["item_id", "order_id", "menu_id"],
)

# ── 7. VALIDATION DEFINITIONS & CHECKPOINT SETUP ──────────────────────
definitions = [
    gx.ValidationDefinition(name="silver_menu_master_runtime_validation", suite=menu_suite, data=menu_definition),
    gx.ValidationDefinition(name="silver_outlet_master_runtime_validation", suite=outlet_suite, data=outlet_definition),
    gx.ValidationDefinition(name="silver_orders_runtime_validation", suite=orders_suite, data=orders_definition),
    gx.ValidationDefinition(name="silver_order_items_runtime_validation", suite=order_items_suite, data=order_items_definition),
]
for definition in definitions:
    context.validation_definitions.add_or_update(definition)

checkpoint = gx.Checkpoint(
    name="silver_runtime_quality_gate_checkpoint",
    validation_definitions=definitions,
    actions=[
        gx.checkpoint.actions.UpdateDataDocsAction(name="update_data_docs", site_names=[])
    ],
    result_format={"result_format": "SUMMARY"},
)
context.checkpoints.add_or_update(checkpoint)

# ── 8. EXECUTE VALIDATIONS & BUILD DATA DOCS ──────────────────────────
try:
    logger.info("Menjalankan Validasi Silver quality gate...")
    results = [
        definition.run(batch_parameters={"dataframe": dataframe})
        for definition, dataframe in zip(
            definitions,
            [df_menu, df_outlet, df_orders, df_order_items],
        )
    ]

    if not all(result.success for result in results):
        raise RuntimeError(
            "GX Silver validation failed; stopping pipeline. "
            "See Data Docs for details."
        )

    logger.info("Silver validation passed!")

except NoAvailableBatchesError as exc:
    raise RuntimeError("Required Silver batch is unavailable.") from exc

context.build_data_docs()
logger.info("Silver Data Docs successfully built/rebuilt!")
