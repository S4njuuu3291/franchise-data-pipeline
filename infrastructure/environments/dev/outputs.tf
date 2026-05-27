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