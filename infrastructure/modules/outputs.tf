# State Lock Bucket
output "state_lock_bucket_id" {
  description = "ID dari S3 bucket untuk state lock"
  value       = aws_s3_bucket.state_lock.id
}

output "state_lock_bucket_arn" {
  description = "ARN dari S3 bucket untuk state lock"
  value       = aws_s3_bucket.state_lock.arn
}

# Bronze Data Lake Bucket
output "data_lake_bronze_id" {
  description = "ID dari S3 bucket data lake bronze"
  value       = aws_s3_bucket.data_lake_bronze.id
}

output "data_lake_bronze_arn" {
  description = "ARN dari S3 bucket data lake bronze"
  value       = aws_s3_bucket.data_lake_bronze.arn
}

output "data_lake_bronze_bucket_domain_name" {
  description = "Domain name dari S3 bucket data lake bronze"
  value       = aws_s3_bucket.data_lake_bronze.bucket_domain_name
}

# Silver Data Lake Bucket
output "data_lake_silver_id" {
  description = "ID dari S3 bucket data lake silver"
  value       = aws_s3_bucket.data_lake_silver.id
}

output "data_lake_silver_arn" {
  description = "ARN dari S3 bucket data lake silver"
  value       = aws_s3_bucket.data_lake_silver.arn
}

output "data_lake_silver_bucket_domain_name" {
  description = "Domain name dari S3 bucket data lake silver"
  value       = aws_s3_bucket.data_lake_silver.bucket_domain_name
}

# Quarantine Data Lake Bucket
output "data_lake_quarantine_id" {
  description = "ID dari S3 bucket data lake quarantine"
  value       = aws_s3_bucket.data_lake_quarantine.id
}

output "data_lake_quarantine_arn" {
  description = "ARN dari S3 bucket data lake quarantine"
  value       = aws_s3_bucket.data_lake_quarantine.arn
}

output "data_lake_quarantine_bucket_domain_name" {
  description = "Domain name dari S3 bucket data lake quarantine"
  value       = aws_s3_bucket.data_lake_quarantine.bucket_domain_name
}

# Athena Query Results Bucket
output "athena_results_bucket_id" {
  description = "ID dari S3 bucket untuk Athena query results"
  value       = aws_s3_bucket.athena_results.id
}

output "athena_results_bucket_arn" {
  description = "ARN dari S3 bucket untuk Athena query results"
  value       = aws_s3_bucket.athena_results.arn
}

output "athena_results_bucket_path" {
  description = "S3 path untuk Athena query results"
  value       = "s3://${aws_s3_bucket.athena_results.id}/query-results/"
}

# Gold Data Lake Bucket
output "data_lake_gold_id" {
  description = "ID dari S3 bucket data lake gold"
  value       = aws_s3_bucket.data_lake_gold.id
}

output "data_lake_gold_arn" {
  description = "ARN dari S3 bucket data lake gold"
  value       = aws_s3_bucket.data_lake_gold.arn
}

output "data_lake_gold_bucket_domain_name" {
  description = "Domain name dari S3 bucket data lake gold"
  value       = aws_s3_bucket.data_lake_gold.bucket_domain_name
}

# Glue Catalog Table: outlet_master
output "glue_table_outlet_master_name" {
  description = "Nama Glue Catalog table untuk outlet_master"
  value       = aws_glue_catalog_table.outlet_master.name
}

output "glue_table_menu_master_name" {
  description = "Nama Glue Catalog table untuk menu_master"
  value       = aws_glue_catalog_table.menu_master.name
}

output "glue_table_orders_name" {
  description = "Nama Glue Catalog table untuk orders"
  value       = aws_glue_catalog_table.orders.name
}

output "glue_table_order_items_name" {
  description = "Nama Glue Catalog table untuk order_items"
  value       = aws_glue_catalog_table.order_items.name
}

# Athena WorkGroup
output "athena_workgroup_name" {
  description = "Nama Athena WorkGroup"
  value       = aws_athena_workgroup.franchise.name
}

# Athena Database
output "athena_database_name" {
  description = "Nama database Athena"
  value       = aws_athena_database.franchise.name
}