# State Lock Bucket
output "state_lock_bucket_id" {
  description = "ID dari S3 bucket state lock (dev)"
  value       = module.base.state_lock_bucket_id
}

output "state_lock_bucket_arn" {
  description = "ARN dari S3 bucket state lock (dev)"
  value       = module.base.state_lock_bucket_arn
}

# Bronze Data Lake Bucket
output "data_lake_bronze_id" {
  description = "ID dari S3 bucket data lake bronze (dev)"
  value       = module.base.data_lake_bronze_id
}

output "data_lake_bronze_arn" {
  description = "ARN dari S3 bucket data lake bronze (dev)"
  value       = module.base.data_lake_bronze_arn
}

output "data_lake_bronze_bucket_domain_name" {
  description = "Domain name dari S3 bucket data lake bronze (dev)"
  value       = module.base.data_lake_bronze_bucket_domain_name
}

# Silver Data Lake Bucket
output "data_lake_silver_id" {
  description = "ID dari S3 bucket data lake silver (dev)"
  value       = module.base.data_lake_silver_id
}

output "data_lake_silver_arn" {
  description = "ARN dari S3 bucket data lake silver (dev)"
  value       = module.base.data_lake_silver_arn
}

output "data_lake_silver_bucket_domain_name" {
  description = "Domain name dari S3 bucket data lake silver (dev)"
  value       = module.base.data_lake_silver_bucket_domain_name
}

# Quarantine Data Lake Bucket
output "data_lake_quarantine_id" {
  description = "ID dari S3 bucket data lake quarantine (dev)"
  value       = module.base.data_lake_quarantine_id
}

output "data_lake_quarantine_arn" {
  description = "ARN dari S3 bucket data lake quarantine (dev)"
  value       = module.base.data_lake_quarantine_arn
}

output "data_lake_quarantine_bucket_domain_name" {
  description = "Domain name dari S3 bucket data lake quarantine (dev)"
  value       = module.base.data_lake_quarantine_bucket_domain_name
}

# Athena Query Results Bucket
output "athena_results_bucket_id" {
  description = "ID dari S3 bucket Athena query results (dev)"
  value       = module.base.athena_results_bucket_id
}

output "athena_results_bucket_arn" {
  description = "ARN dari S3 bucket Athena query results (dev)"
  value       = module.base.athena_results_bucket_arn
}

output "athena_results_bucket_path" {
  description = "S3 path untuk Athena query results (dev)"
  value       = module.base.athena_results_bucket_path
}

# Gold Data Lake Bucket
output "data_lake_gold_id" {
  description = "ID dari S3 bucket data lake gold (dev)"
  value       = module.base.data_lake_gold_id
}

output "data_lake_gold_arn" {
  description = "ARN dari S3 bucket data lake gold (dev)"
  value       = module.base.data_lake_gold_arn
}

output "data_lake_gold_bucket_domain_name" {
  description = "Domain name dari S3 bucket data lake gold (dev)"
  value       = module.base.data_lake_gold_bucket_domain_name
}

# Glue Catalog Table: outlet_master
output "glue_table_outlet_master_name" {
  description = "Nama Glue Catalog table untuk outlet_master (dev)"
  value       = module.base.glue_table_outlet_master_name
}

output "glue_table_menu_master_name" {
  description = "Nama Glue Catalog table untuk menu_master (dev)"
  value       = module.base.glue_table_menu_master_name
}

output "glue_table_orders_name" {
  description = "Nama Glue Catalog table untuk orders (dev)"
  value       = module.base.glue_table_orders_name
}

output "glue_table_order_items_name" {
  description = "Nama Glue Catalog table untuk order_items (dev)"
  value       = module.base.glue_table_order_items_name
}

# Athena WorkGroup
output "athena_workgroup_name" {
  description = "Nama Athena WorkGroup (dev)"
  value       = module.base.athena_workgroup_name
}

# Athena Database
output "athena_database_name" {
  description = "Nama database Athena (dev)"
  value       = module.base.athena_database_name
}