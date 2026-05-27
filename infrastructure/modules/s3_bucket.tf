# Bucket: state lock Terraform
resource "aws_s3_bucket" "state_lock" {
    bucket = "${local.resource_prefix}-state-lock"

    lifecycle {
      prevent_destroy = false
    }
}

# Versioning: state lock
resource "aws_s3_bucket_versioning" "state_versioning" {
  bucket = aws_s3_bucket.state_lock.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Bucket: bronze (raw data)
resource "aws_s3_bucket" "data_lake_bronze" {
    bucket = "${local.resource_prefix}-data-lake-bronze"

    lifecycle {
      prevent_destroy = false
    }
}

# Public access: bronze
resource "aws_s3_bucket_public_access_block" "data_lake_bronze_privacy" {
  bucket = aws_s3_bucket.data_lake_bronze.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket: silver (processed data)
resource "aws_s3_bucket" "data_lake_silver" {
    bucket = "${local.resource_prefix}-data-lake-silver"

    lifecycle {
      prevent_destroy = false
    }
}

# Public access: silver
resource "aws_s3_bucket_public_access_block" "data_lake_silver_privacy" {
  bucket = aws_s3_bucket.data_lake_silver.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket: quarantine (data tidak valid / suspect)
resource "aws_s3_bucket" "data_lake_quarantine" {
    bucket = "${local.resource_prefix}-data-lake-quarantine"

    lifecycle {
      prevent_destroy = false
    }
}

# Public access: quarantine
resource "aws_s3_bucket_public_access_block" "data_lake_quarantine_privacy" {
  bucket = aws_s3_bucket.data_lake_quarantine.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

