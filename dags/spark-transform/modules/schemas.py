from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType

# Schema definitions untuk Glue job — harus sama dengan header CSV extractor.

outlet_schema = StructType([
    StructField("outlet_id",    IntegerType(),   True),
    StructField("outlet_name",  StringType(),    True),
    StructField("city",         StringType(),    True),
    StructField("region_tier",  StringType(),    True),
    StructField("created_at",   TimestampType(), True),
    StructField("updated_at",   TimestampType(), True),
])

menu_master_schema = StructType([
    StructField("menu_id",         IntegerType(),   True),
    StructField("menu_name",       StringType(),    True),
    StructField("category",        StringType(),    True),
    StructField("base_price",      DoubleType(),    True),
    StructField("price_tier_1",    DoubleType(),    True),
    StructField("price_tier_2",    DoubleType(),    True),
    StructField("price_tier_3",    DoubleType(),    True),
    StructField("is_promo_active", StringType(),    True),
    StructField("updated_at",      TimestampType(), True),
])

orders_schema = StructType([
    StructField("order_id",       IntegerType(),   True),
    StructField("customer_id",    IntegerType(),   True),
    StructField("outlet_id",      IntegerType(),   True),
    StructField("cashier_id",     IntegerType(),   True),
    StructField("total_amount",   DoubleType(),    True),
    StructField("payment_method", StringType(),    True),
    StructField("order_status",   StringType(),    True),
    StructField("created_at",     TimestampType(), True),
])

# Transaction detail: order_items.csv
order_items_schema = StructType([
    StructField("item_id",        IntegerType(),   True),
    StructField("order_id",       IntegerType(),   True),
    StructField("menu_id",        IntegerType(),   True),
    StructField("quantity",       IntegerType(),   True),
    StructField("price_per_item", DoubleType(),    True),
    StructField("subtotal",       DoubleType(),    True),
])

# Transaction payments: payments.csv
payments_schema = StructType([
    StructField("payment_id",         IntegerType(),   True),
    StructField("order_id",           IntegerType(),   True),
    StructField("payment_method",     StringType(),    True),
    StructField("payment_status",     StringType(),    True),
    StructField("amount",             DoubleType(),    True),
    StructField("paid_at",            TimestampType(), True),
    StructField("provider_reference", StringType(),    True),
])

# Master data: customers.csv
customers_schema = StructType([
    StructField("customer_id",   IntegerType(),   True),
    StructField("customer_name", StringType(),    True),
    StructField("email",         StringType(),    True),
    StructField("phone",         StringType(),    True),
    StructField("created_at",    TimestampType(), True),
    StructField("updated_at",    TimestampType(), True),
])

# Master data: employees.csv
employees_schema = StructType([
    StructField("employee_id",       IntegerType(),   True),
    StructField("employee_name",     StringType(),    True),
    StructField("employee_role",     StringType(),    True),
    StructField("outlet_id",         IntegerType(),   True),
    StructField("employment_status", StringType(),    True),
    StructField("created_at",        TimestampType(), True),
    StructField("updated_at",        TimestampType(), True),
])
