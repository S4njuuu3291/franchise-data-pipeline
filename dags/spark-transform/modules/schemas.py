from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType

# ── Schema definitions (untuk Glue job — self-contained) ──

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
    StructField("outlet_id",      IntegerType(),   True),
    StructField("cashier_id",     IntegerType(),   True),
    StructField("total_amount",   DoubleType(),    True),
    StructField("payment_method", StringType(),    True),
    StructField("created_at",     TimestampType(), True),
])

order_items_schema = StructType([
    StructField("item_id",        IntegerType(),   True),
    StructField("order_id",       IntegerType(),   True),
    StructField("menu_id",        IntegerType(),   True),
    StructField("quantity",       IntegerType(),   True),
    StructField("price_per_item", DoubleType(),    True),
    StructField("subtotal",       DoubleType(),    True),
])
