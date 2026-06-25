locals {
  db_prefix = "franchise_pipeline_${var.environment}"
}

# Athena Database
resource "aws_athena_database" "franchise" {
    name = "${local.db_prefix}_athena_db"
    bucket = aws_s3_bucket.athena_results.bucket
}

# Athena WorkGroup
resource "aws_athena_workgroup" "franchise" {
  name = "${local.db_prefix}_workgroup"
  force_destroy = true

  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/query-results/"
    }
  }
}

# Glue Catalog Table: outlet_master
resource "aws_glue_catalog_table" "outlet_master" {
  name          = "outlet_master"
  database_name = aws_athena_database.franchise.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_lake_silver.bucket}/outlet_master/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "ParquetHiveSerDe"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "outlet_id"
      type = "int"
    }
    columns {
      name = "outlet_name"
      type = "string"
    }
    columns {
      name = "city"
      type = "string"
    }
    columns {
      name = "region_tier"
      type = "string"
    }
    columns {
      name = "created_at"
      type = "timestamp"
    }
    columns {
      name = "updated_at"
      type = "timestamp"
    }
  }

}

# Glue Catalog Table: menu_master
resource "aws_glue_catalog_table" "menu_master" {
  name          = "menu_master"
  database_name = aws_athena_database.franchise.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_lake_silver.bucket}/menu_master/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "ParquetHiveSerDe"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "menu_id"
      type = "int"
    }
    columns {
      name = "menu_name"
      type = "string"
    }
    columns {
      name = "category"
      type = "string"
    }
    columns {
      name = "base_price"
      type = "double"
    }
    columns {
      name = "price_tier_1"
      type = "double"
    }
    columns {
      name = "price_tier_2"
      type = "double"
    }
    columns {
      name = "price_tier_3"
      type = "double"
    }
    columns {
      name = "is_promo_active"
      type = "string"
    }
    columns {
      name = "updated_at"
      type = "timestamp"
    }
  }

}

# Glue Catalog Table: orders
resource "aws_glue_catalog_table" "orders" {
  name          = "orders"
  database_name = aws_athena_database.franchise.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
    "projection.enabled"           = "true"
    "projection.year.type"         = "integer"
    "projection.year.range"        = "2026,2027"
    "projection.month.type"        = "integer"
    "projection.month.range"       = "1,12"
    "projection.month.digits"      = "2"
    "projection.day.type"          = "integer"
    "projection.day.range"         = "1,31"
    "projection.day.digits"        = "2"
    "partition_filtering.enabled"  = "true"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_lake_silver.bucket}/orders/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "ParquetHiveSerDe"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "order_id"
      type = "int"
    }
    columns {
      name = "outlet_id"
      type = "int"
    }
    columns {
      name = "cashier_id"
      type = "int"
    }
    columns {
      name = "total_amount"
      type = "double"
    }
    columns {
      name = "payment_method"
      type = "string"
    }
    columns {
      name = "created_at"
      type = "timestamp"
    }
    columns {
      name = "data_quality_status"
      type = "string"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
  partition_keys {
    name = "month"
    type = "string"
  }
  partition_keys {
    name = "day"
    type = "string"
  }
}

# Glue Catalog Table: order_items
resource "aws_glue_catalog_table" "order_items" {
  name          = "order_items"
  database_name = aws_athena_database.franchise.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
    "projection.enabled"           = "true"
    "projection.year.type"         = "integer"
    "projection.year.range"        = "2026,2027"
    "projection.month.type"        = "integer"
    "projection.month.range"       = "1,12"
    "projection.month.digits"      = "2"
    "projection.day.type"          = "integer"
    "projection.day.range"         = "1,31"
    "projection.day.digits"        = "2"
    "partition_filtering.enabled"  = "true"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_lake_silver.bucket}/order_items/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "ParquetHiveSerDe"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "item_id"
      type = "int"
    }
    columns {
      name = "order_id"
      type = "int"
    }
    columns {
      name = "menu_id"
      type = "int"
    }
    columns {
      name = "quantity"
      type = "int"
    }
    columns {
      name = "price_per_item"
      type = "double"
    }
    columns {
      name = "subtotal"
      type = "double"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
  partition_keys {
    name = "month"
    type = "string"
  }
  partition_keys {
    name = "day"
    type = "string"
  }
}

