import argparse
import os
from pathlib import Path
from urllib.parse import quote

import great_expectations as gx
from dotenv import load_dotenv
import yaml
import logging
from datetime import datetime

from great_expectations.exceptions.exceptions import NoAvailableBatchesError

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Setup and run the GX quality gate")
parser.add_argument(
    "--date",
    required=True,
    help="Tanggal data orders/order_items dengan format YYYY-MM-DD",
)
args = parser.parse_args()
execution_date = datetime.strptime(args.date, "%Y-%m-%d")
year = execution_date.strftime("%Y")
month = execution_date.strftime("%m")
day = execution_date.strftime("%d")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.getLogger("great_expectations").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)

# ── Config dari YAML ──────────────────────────────────────────────────
_config_path = os.environ.get("PIPELINE_CONFIG_PATH") or \
    os.path.join(os.path.dirname(__file__), "../../config/pipeline-config.yaml")
with open(_config_path) as _f:
    _cfg = yaml.safe_load(_f)["storage"]

logger.info("Initializing GX quality gate")

context = gx.get_context(mode='file')

datasource_name = "bronze_data"
bucket_name = _cfg["bronze"]

datasource = context.data_sources.add_or_update_pandas_s3(
    name=datasource_name, 
    bucket=bucket_name
)
logger.info("GX datasource ready: %s", datasource_name)

menu_master = "menu_master_asset"
outlet_master = "outlet_master_asset"
orders = "orders_asset"
order_items = "order_items_asset"

menu_master_asset = datasource.add_csv_asset(
    name=menu_master,
    s3_prefix="menu_master/", 
)

outlet_master_asset = datasource.add_csv_asset(
    name=outlet_master,
    s3_prefix="outlet_master/", 
)

menu_batch_definition = menu_master_asset.add_batch_definition_path(
    name="daily_menu_definition",
    path=r".*\.csv"  # Tulis regex nama file Anda di sini
)

menu_batch = menu_batch_definition.get_batch()

outlet_batch_definition = outlet_master_asset.add_batch_definition_path(
    name="daily_outlet_definition",
    path=r".*\.csv"  # Tulis regex nama file Anda di sini
)

outlet_batch = outlet_batch_definition.get_batch()

logger.debug("Menu master batch preview:\n%s", menu_batch.data.dataframe.head())
logger.debug("Outlet master batch preview:\n%s", outlet_batch.data.dataframe.head())
logger.info("Master batches loaded: menu_master and outlet_master")

# Suite for menu_master
menu_suite_name = "menu_master_suite"

logger.info("Creating expectation suite: %s", menu_suite_name)
menu_suite = gx.ExpectationSuite(
    name=menu_suite_name
)

menu_suite.add_expectation(
    gx.expectations.ExpectTableColumnsToMatchSet(
        column_set=[
            "menu_id",
            "menu_name",
            "category",
            "base_price",
            "price_tier_1",
            "price_tier_2",
            "price_tier_3",
            "is_promo_active",
            "updated_at",
        ],
        exact_match=True,
    )
)
for column in ("menu_id", "menu_name", "category"):
    menu_suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column=column)
    )

context.suites.add_or_update(menu_suite)
logger.info("Expectation suite saved: %s (%d expectations)", menu_suite_name, len(menu_suite.expectations))

# Suite for outlet_master
outlet_suite_name = "outlet_master_suite"

logger.info("Creating expectation suite: %s", outlet_suite_name)
outlet_suite = gx.ExpectationSuite(
    name=outlet_suite_name
)

outlet_suite.add_expectation(
    gx.expectations.ExpectTableColumnsToMatchSet(
        column_set=[
            "outlet_id",
            "outlet_name",
            "city",
            "region_tier",
            "created_at",
            "updated_at",
        ],
        exact_match=True,
    )
)
for column in ("outlet_id", "outlet_name", "city", "region_tier"):
    outlet_suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column=column)
    )

context.suites.add_or_update(outlet_suite)
logger.info("Expectation suite saved: %s (%d expectations)", outlet_suite_name, len(outlet_suite.expectations))

# Validation for menu_master
menu_validation_definition = gx.ValidationDefinition(
    name="menu_master_validation",
    suite=menu_suite,
    data=menu_batch_definition
)

# Validation for outlet_master
outlet_validation_definition = gx.ValidationDefinition(
    name="outlet_master_validation",
    suite=outlet_suite,
    data=outlet_batch_definition
)

context.validation_definitions.add_or_update(menu_validation_definition)
context.validation_definitions.add_or_update(outlet_validation_definition)
# Checkpoint for master

checkpoint = gx.Checkpoint(
    name="master_data_checkpoint",
    validation_definitions=[menu_validation_definition, outlet_validation_definition],
    actions=[],
    result_format={"result_format": "SUMMARY"},
)

context.checkpoints.add_or_update(checkpoint)

logger.info("Checkpoint configured: %s", checkpoint.name)

site_name = "quality_gate_site"

site_config = {
    "class_name": "SiteBuilder",
    "site_index_builder": {
        "class_name": "DefaultSiteIndexBuilder"
    },
    "store_backend": {
        "class_name": "TupleFilesystemStoreBackend",
        "base_directory": "uncommitted/data_docs/quality_gate_site/",
    },
}

if site_name not in context.get_site_names():
    context.add_data_docs_site(
        site_name=site_name,
        site_config=site_config,
    )
else:
    logger.info("Data Docs site already exists: %s", site_name)

context.build_data_docs(site_names=site_name)
logger.info("Data Docs site built: %s", site_name)

# Run the checkpoint to validate the master data

try:
    checkpoint_result = checkpoint.run()
    if checkpoint_result:
        logger.info("Master data validation passed.")
    else:
        logger.error("Master data validation failed. See Data Docs for details.")
except NoAvailableBatchesError:
    raise SystemExit(
        f"CRITICAL: expected batch missing for validation. Please check the S3 bucket '{bucket_name}' for the required master data files."
    )

context.build_data_docs(site_names=site_name)

# =========================================================

orders = "orders_asset"
order_items = "order_items_asset"

orders_asset = datasource.add_csv_asset(
    name=orders,
    s3_prefix=f"orders/year={year}/month={month}/day={day}/",
)

order_items_asset = datasource.add_csv_asset(
    name=order_items,
    s3_prefix=f"order_items/year={year}/month={month}/day={day}/",
)

orders_batch_definition = orders_asset.add_batch_definition_path(
    name="daily_orders_definition",
    # prefix example = orders/year=2025/month=01/day=01/orders.csv
    path=r"orders.csv"  # Tulis regex nama file Anda di sini
)

orders_batch = orders_batch_definition.get_batch()

order_items_batch_definition = order_items_asset.add_batch_definition_path(
    name="daily_order_items_definition",
    # prefix example = order_items/year=2025/month=01/day=01/order_items.csv
    path=r"order_items.csv"  # Tulis regex nama file Anda di sini
)

order_items_batch = order_items_batch_definition.get_batch()

# Suite for orders
orders_suite_name = "orders_suite"

logger.info("Creating expectation suite: %s", orders_suite_name)
orders_suite = gx.ExpectationSuite(name=orders_suite_name)

orders_suite.add_expectation(
    gx.expectations.ExpectTableColumnsToMatchSet(
        column_set=[
            "order_id",
            "outlet_id",
            "cashier_id",
            "total_amount",
            "payment_method",
            "created_at",
        ],
        exact_match=True,
        meta={"severity": "critical"},
    )
)
for column in (
    "order_id",
    "outlet_id",
    "cashier_id",
    "total_amount",
    "payment_method",
    "created_at",
):
    orders_suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(
            column=column,
            meta={"severity": "critical"},
        )
    )

orders_suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeUnique(
        column="order_id",
        meta={"severity": "critical"},
    )
)
orders_suite.add_expectation(
    gx.expectations.ExpectTableRowCountToBeBetween(
        min_value=1,
        meta={"severity": "critical"},
    )
)
orders_suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeInSet(
        column="payment_method",
        value_set=["Cash", "Credit Card", "Debit Card", "GoPay", "OVO", "QRIS"],
        mostly=0.99,
        meta={"severity": "warning"},
    )
)

context.suites.add_or_update(orders_suite)
logger.info("Expectation suite saved: %s (%d expectations)", orders_suite_name, len(orders_suite.expectations))

# Suite for order_items
order_items_suite_name = "order_items_suite"

logger.info("Creating expectation suite: %s", order_items_suite_name)
order_items_suite = gx.ExpectationSuite(name=order_items_suite_name)

order_items_suite.add_expectation(
    gx.expectations.ExpectTableColumnsToMatchSet(
        column_set=[
            "item_id",
            "order_id",
            "menu_id",
            "quantity",
            "price_per_item",
            "subtotal",
        ],
        exact_match=True,
        meta={"severity": "critical"},
    )
)
for column in (
    "item_id",
    "order_id",
    "menu_id",
    "quantity",
    "price_per_item",
    "subtotal",
):
    order_items_suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(
            column=column,
            meta={"severity": "critical"},
        )
    )

order_items_suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeUnique(
        column="item_id",
        meta={"severity": "critical"},
    )
)
order_items_suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="quantity",
        min_value=1,
        meta={"severity": "critical"},
    )
)
for column in ("price_per_item", "subtotal"):
    order_items_suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column=column,
            min_value=0,
            meta={"severity": "warning"},
        )
    )

context.suites.add_or_update(order_items_suite)
logger.info("Expectation suite saved: %s (%d expectations)", order_items_suite_name, len(order_items_suite.expectations))

# Validation definitions and checkpoint for transactions
orders_validation_definition = gx.ValidationDefinition(
    name="orders_validation",
    suite=orders_suite,
    data=orders_batch_definition,
)
order_items_validation_definition = gx.ValidationDefinition(
    name="order_items_validation",
    suite=order_items_suite,
    data=order_items_batch_definition,
)

context.validation_definitions.add_or_update(orders_validation_definition)
context.validation_definitions.add_or_update(order_items_validation_definition)

transaction_checkpoint = gx.Checkpoint(
    name="transaction_data_checkpoint",
    validation_definitions=[
        orders_validation_definition,
        order_items_validation_definition,
    ],
    actions=[],
    result_format={"result_format": "SUMMARY"},
)
context.checkpoints.add_or_update(transaction_checkpoint)
logger.info("Checkpoint configured: %s", transaction_checkpoint.name)

try:
    transaction_checkpoint_result = transaction_checkpoint.run()
    if transaction_checkpoint_result:
        logger.info("Transaction data validation passed.")
    else:
        logger.error("Transaction data validation failed. See Data Docs for details.")
except NoAvailableBatchesError:
    raise SystemExit(
        f"CRITICAL: expected transaction batch missing for date {args.date}. "
        f"Please check the S3 bucket '{bucket_name}'."
    )

context.build_data_docs(site_names=site_name)
logger.info("Transaction validation Data Docs rebuilt: %s", site_name)
