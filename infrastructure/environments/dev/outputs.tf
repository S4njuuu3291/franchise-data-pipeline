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