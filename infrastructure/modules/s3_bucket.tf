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

# Bucket: Athena query results
resource "aws_s3_bucket" "athena_results" {
    bucket = "${local.resource_prefix}-athena-query-results"

    lifecycle {
      prevent_destroy = false
    }
}

# Public access: athena results
resource "aws_s3_bucket_public_access_block" "athena_results_privacy" {
  bucket = aws_s3_bucket.athena_results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket: gold (aggregated / analytics-ready data)
resource "aws_s3_bucket" "data_lake_gold" {
    bucket = "${local.resource_prefix}-data-lake-gold"

    lifecycle {
      prevent_destroy = false
    }
}

# Public access: gold
resource "aws_s3_bucket_public_access_block" "data_lake_gold_privacy" {
  bucket = aws_s3_bucket.data_lake_gold.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket: S3 access logs
resource "aws_s3_bucket" "access_logs" {
    bucket = "${local.resource_prefix}-access-logs"

    lifecycle {
      prevent_destroy = false
    }
}

# Public access: access logs
resource "aws_s3_bucket_public_access_block" "access_logs_privacy" {
  bucket = aws_s3_bucket.access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Policy: izinkan S3 logging service nulis log
resource "aws_s3_bucket_policy" "access_logs_policy" {
  bucket = aws_s3_bucket.access_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "logging.s3.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.access_logs.arn}/*"
      }
    ]
  })
}

# ── S3 Access Logging Configuration ──────────────────────────────────

resource "aws_s3_bucket_logging" "bronze_logging" {
  bucket = aws_s3_bucket.data_lake_bronze.id
  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "bronze/"
}

resource "aws_s3_bucket_logging" "silver_logging" {
  bucket = aws_s3_bucket.data_lake_silver.id
  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "silver/"
}

resource "aws_s3_bucket_logging" "gold_logging" {
  bucket = aws_s3_bucket.data_lake_gold.id
  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "gold/"
}

resource "aws_s3_bucket_logging" "athena_results_logging" {
  bucket = aws_s3_bucket.athena_results.id
  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "athena-results/"
}

resource "aws_s3_bucket_logging" "quarantine_logging" {
  bucket = aws_s3_bucket.data_lake_quarantine.id
  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "quarantine/"
}