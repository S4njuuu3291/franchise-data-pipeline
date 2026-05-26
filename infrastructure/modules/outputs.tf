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