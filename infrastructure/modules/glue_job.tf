# ── IAM Role untuk Glue ──────────────────────────────────────────────
resource "aws_iam_role" "glue_role" {
  name = "${local.resource_prefix}-glue-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "glue.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3_access" {
  name = "${local.resource_prefix}-glue-s3-access"
  role = aws_iam_role.glue_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_lake_bronze.arn,
          "${aws_s3_bucket.data_lake_bronze.arn}/*",
          aws_s3_bucket.data_lake_silver.arn,
          "${aws_s3_bucket.data_lake_silver.arn}/*",
          aws_s3_bucket.data_lake_quarantine.arn,
          "${aws_s3_bucket.data_lake_quarantine.arn}/*",
          aws_s3_bucket.scripts.arn,
          "${aws_s3_bucket.scripts.arn}/*",
        ]
      }
    ]
  })
}

# ── S3 Bucket untuk Script Glue ──────────────────────────────────────
resource "aws_s3_bucket" "scripts" {
  bucket = "${local.resource_prefix}-glue-scripts"

  lifecycle {
    prevent_destroy = false
  }
}

resource "aws_s3_bucket_public_access_block" "scripts_privacy" {
  bucket = aws_s3_bucket.scripts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── Glue Job: Bronze → Silver Transform ─────────────────────────────
resource "aws_glue_job" "transform" {
  name              = "${local.resource_prefix}-bronze-to-silver"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.scripts.bucket}/transform_glue.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-auto-scaling" = "true"
    "--bronze-bucket"     = aws_s3_bucket.data_lake_bronze.bucket
    "--silver-bucket"     = aws_s3_bucket.data_lake_silver.bucket
    "--quarantine-bucket" = aws_s3_bucket.data_lake_quarantine.bucket
    "--extra-py-files"    = "s3://${aws_s3_bucket.scripts.bucket}/dependencies/schemas.zip"
  }
}
