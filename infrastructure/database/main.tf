terraform {
  required_providers {
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "~> 1.25.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

# Terhubung langsung ke kontainer Replica Anda
provider "postgresql" {
  host            = "127.0.0.1"
  port            = 5432
  username        = "primary_user"
  password        = trimspace(file("${path.module}/../../docker/secrets/postgres_primary_password.txt"))
  database        = "main_db"
  sslmode         = "verify-full"
  sslrootcert     = "${path.module}/../../docker/certs/ca.crt"
  connect_timeout = 15
}

# ------------------------------------------------------------
# ROLE & USER MANAGEMENT (LEAST PRIVILEGE)
# ------------------------------------------------------------

# 1. Role Grup khusus untuk hak Read-Only (NOLOGIN)
resource "postgresql_role" "oltp_readonly" {
  name      = "oltp_readonly"
  login     = false
  superuser = false
}

# Generasi password otomatis untuk Airflow agar aman
resource "random_password" "airflow_pass" {
  length  = 32
  special = false
}

# Sinkronkan password Terraform ke secret lokal yang dipasang Docker Compose.
resource "local_file" "write_airflow_secret" {
  content              = random_password.airflow_pass.result
  filename             = "${path.module}/../../docker/secrets/airflow_reader_password.txt"
  file_permission      = "0600"
  directory_permission = "0700"
}

# 2. User Identitas untuk Airflow agar bisa Login
resource "postgresql_role" "airflow_reader" {
  name     = "airflow_reader"
  login    = true
  inherit  = true # Mewarisi hak akses dari grup
  password = random_password.airflow_pass.result
  roles    = [postgresql_role.oltp_readonly.name]
}

# 3. Masukkan Airflow ke dalam grup Read-Only
resource "postgresql_grant_role" "grant_readonly_to_airflow" {
  role       = postgresql_role.airflow_reader.name
  grant_role = postgresql_role.oltp_readonly.name
}

# 4. Berikan izin masuk/akses ke skema 'public' tempat tabel asli Anda berada
resource "postgresql_grant" "public_schema_usage" {
  database    = "main_db"
  role        = postgresql_role.oltp_readonly.name
  schema      = "public"
  object_type = "schema"
  privileges  = ["USAGE"]
}

output "airflow_etl_password" {
  description = "Generated password for airflow_etl_user"
  value       = random_password.airflow_pass.result
  sensitive   = true
}

resource "postgresql_grant" "readonly_tables" {
  database    = "main_db"
  role        = postgresql_role.oltp_readonly.name
  schema      = "public"
  object_type = "table"

  # KUNCI: Gunakan 'objects', bukan 'tables'
  objects = [
    "outlet_master",
    "menu_master",
    "orders",
    "order_items"
  ]
  privileges = ["SELECT"]
}

resource "postgresql_default_privileges" "primary_tables" {
  database    = "main_db"
  owner       = "primary_user"
  schema      = "public"
  role        = postgresql_role.oltp_readonly.name
  object_type = "table"
  privileges  = ["SELECT"]
}
