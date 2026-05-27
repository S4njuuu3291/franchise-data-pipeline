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