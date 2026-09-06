COMPOSE_FILE := docker/docker-compose.yml

docker-build:
	docker compose -f $(COMPOSE_FILE) build

docker-up:
	docker compose -f $(COMPOSE_FILE) up -d

docker-up-db:
	docker compose -f $(COMPOSE_FILE) up -d postgres-primary postgres-replica postgres

docker-down:
	docker compose -f $(COMPOSE_FILE) down

docker-down-v:
	docker compose -f $(COMPOSE_FILE) down -v

pm-db-shell:
	psql \
		"host=localhost \
		port=5432 \
		dbname=main_db \
		user=primary_user \
		sslmode=verify-full \
		sslrootcert=docker/certs/ca.crt"

repl-db-shell:
	PGPASSWORD="$$(cd $(TF_DATABASE_DIR) && terraform output -raw airflow_etl_password)" psql \
		"host=localhost \
		port=5433 \
		dbname=main_db \
		user=airflow_reader \
		sslmode=disable"

.PHONY: worker-shell
worker-shell:
	docker compose -f $(COMPOSE_FILE) exec airflow-worker bash

docker-restart:
	docker compose -f $(COMPOSE_FILE) restart

# ---------------------------------------------------------------------------
# init-schema — Inject SOURCE-SCHEMA.sql ke primary database
# ---------------------------------------------------------------------------
init-schema:
	@echo "Waiting for PostgreSQL at $(DB_HOST):$(DB_PORT) ..."
	@until docker compose -f $(COMPOSE_FILE) exec postgres-primary pg_isready -U primary_user > /dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "Injecting $(SOURCE_SCHEMA) into primary ..."
	@docker compose -f $(COMPOSE_FILE) exec -T postgres-primary psql -U primary_user -d main_db < $(SOURCE_SCHEMA)
	@echo "Schema injected successfully."

# ---------------------------------------------------------------------------
# truncate-primary — Hapus semua data di primary (reset tabel)
# ---------------------------------------------------------------------------
.PHONY: truncate-primary
truncate-primary:
	@echo "Truncating all tables in primary database ..."
	@docker compose -f $(COMPOSE_FILE) exec -T postgres-primary psql -U primary_user -d main_db -c \
		"TRUNCATE TABLE order_items, orders, menu_master, outlet_master RESTART IDENTITY CASCADE;"
	@echo "All tables truncated."

# ---------------------------------------------------------------------------
# drop-schema — Hapus semua tabel (DROP TABLE)
# ---------------------------------------------------------------------------
.PHONY: drop-schema
drop-schema:
	@echo "Dropping all tables in primary database ..."
	@docker compose -f $(COMPOSE_FILE) exec -T postgres-primary psql -U primary_user -d main_db -c \
		"DROP TABLE IF EXISTS order_items, orders, menu_master, outlet_master CASCADE;"
	@echo "All tables dropped."

# ---------------------------------------------------------------------------
# Variabel untuk Athena & Glue
# ---------------------------------------------------------------------------
ATHENA_DATABASE = franchise_pipeline_dev_athena_db
DATA_LAKE_GOLD_BUCKET = franchise-pipeline-dev-data-lake-gold
SILVER_BUCKET = franchise-pipeline-dev-data-lake-silver

# Daftar semua objek dbt di Athena (views & tables)
DBT_VIEWS = stg_orders stg_order_items
DBT_TABLES = dim_date dim_menu dim_outlet fact_order_items snp_menu_master snp_outlet_master
# ---------------------------------------------------------------------------

TF_DEV_DIR = infrastructure/environments/dev
TF_DATABASE_DIR = infrastructure/database
SOURCE_SCHEMA = $(TF_DATABASE_DIR)/sql/SOURCE-SCHEMA.sql

# ---------------------------------------------------------------------------
# Terraform database — Role, user, dan grant PostgreSQL
# ---------------------------------------------------------------------------
.PHONY: tf-init-db
tf-init-db:
	@echo "Initializing Terraform (database) ..."
	cd $(TF_DATABASE_DIR) && terraform init

.PHONY: tf-validate-db
tf-validate-db:
	@echo "Validating Terraform configuration (database) ..."
	cd $(TF_DATABASE_DIR) && terraform validate

.PHONY: tf-plan-db
tf-plan-db:
	@echo "Planning Terraform (database) ..."
	cd $(TF_DATABASE_DIR) && terraform plan

.PHONY: tf-show-airflow-password
tf-show-airflow-password:
	@echo "Reading Airflow password from Terraform state ..."
	cd $(TF_DATABASE_DIR) && terraform output -raw airflow_etl_password

.PHONY: tf-apply-db
tf-apply-db:
	@echo "Applying Terraform (database) ..."
	cd $(TF_DATABASE_DIR) && terraform apply --auto-approve

.PHONY: tf-destroy-db
tf-destroy-db:
	@echo "Destroying Terraform-managed database roles and grants ..."
	cd $(TF_DATABASE_DIR) && terraform destroy --auto-approve

# ---------------------------------------------------------------------------
# athena-truncate-dbt — Hapus semua tabel/view hasil dbt di Athena + data S3
# ---------------------------------------------------------------------------
.PHONY: athena-truncate-dbt
athena-truncate-dbt:
	@echo "🗑️  Dropping dbt views from Athena ($(ATHENA_DATABASE)) ..."
	@for view in $(DBT_VIEWS); do \
		echo "   → Dropping view $$view ..."; \
		aws glue delete-table --database-name "$(ATHENA_DATABASE)" --name "$$view" 2>/dev/null && echo "     ✅ Dropped" || echo "     ⏭️  Not found"; \
	done
	@echo ""
	@echo "🗑️  Dropping dbt tables from Athena ($(ATHENA_DATABASE)) ..."
	@for table in $(DBT_TABLES); do \
		echo "   → Dropping table $$table ..."; \
		aws glue delete-table --database-name "$(ATHENA_DATABASE)" --name "$$table" 2>/dev/null && echo "     ✅ Dropped" || echo "     ⏭️  Not found"; \
	done
	@echo ""
	@echo "🧹 Cleaning S3 gold layer (dbt output) ..."
	aws s3 rm "s3://$(DATA_LAKE_GOLD_BUCKET)/" --recursive 2>/dev/null && echo "   ✅ Gold layer cleaned" || echo "   ⏭️  Empty or not found"
	@echo ""
	@echo "✅ All dbt objects in Athena have been removed."

# ---------------------------------------------------------------------------
# seed-db — Seed data master (outlet & menu) ke database
# ---------------------------------------------------------------------------
.PHONY: seed-db
seed-db:
	@echo "Running seed-master.py to populate outlet_master and menu_master ..."
	python3 data-generator/seed-master.py
	@echo "Seed master data completed."
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# run-transactions — Jalankan simulasi transaksi harian (full range)
# ---------------------------------------------------------------------------
.PHONY: run-transactions
run-transactions:
	@echo "Running run_all_simulations.py to generate daily transactions ..."
	python3 data-generator/run_all_simulations.py
	@echo "All transactions generated."
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# tf-init-dev — Inisialisasi Terraform (dev)
# ---------------------------------------------------------------------------
.PHONY: tf-init-dev
tf-init-dev:
	@echo "Initializing Terraform (dev) ..."
	cd $(TF_DEV_DIR) && terraform init

# ---------------------------------------------------------------------------
# tf-validate-dev — Validasi konfigurasi Terraform (dev)
# ---------------------------------------------------------------------------
.PHONY: tf-validate-dev
tf-validate-dev:
	@echo "Validating Terraform configuration (dev) ..."
	cd $(TF_DEV_DIR) && terraform validate

# ---------------------------------------------------------------------------
# tf-plan-dev — Planning Terraform (dev)
# ---------------------------------------------------------------------------
.PHONY: tf-plan-dev
tf-plan-dev:
	@echo "Planning Terraform (dev) ..."
	cd $(TF_DEV_DIR) && terraform plan

# ---------------------------------------------------------------------------
# tf-apply-dev — Apply Terraform (dev)
# ---------------------------------------------------------------------------
.PHONY: tf-apply-dev
tf-apply-dev:
	@echo "Applying Terraform (dev) ..."
	cd $(TF_DEV_DIR) && terraform apply --auto-approve

# ---------------------------------------------------------------------------
# tf-destroy-dev — Destroy Terraform (dev)
# ---------------------------------------------------------------------------
.PHONY: tf-destroy-dev
tf-destroy-dev:
	@echo "Destroying Terraform (dev) ..."
	cd $(TF_DEV_DIR) && terraform destroy --auto-approve

GO_EXTRACT_DIR = dags/go-extract

# ---------------------------------------------------------------------------
# go-test — Jalankan unit test (cepat, tanpa DB/MinIO)
# ---------------------------------------------------------------------------
.PHONY: go-test
go-test:
	@echo "Running unit tests (short mode) ..."
	cd $(GO_EXTRACT_DIR) && go test -v -short

# ---------------------------------------------------------------------------
# go-test-all — Jalankan semua test (termasuk integration)
# ---------------------------------------------------------------------------
.PHONY: go-test-all
go-test-all:
	@echo "Running all tests (including integration) ..."
	cd $(GO_EXTRACT_DIR) && go test -v

# ---------------------------------------------------------------------------
# go-test-cover — Jalankan test dengan coverage report
# ---------------------------------------------------------------------------
.PHONY: go-test-cover
go-test-cover:
	@echo "Running tests with coverage ..."
	cd $(GO_EXTRACT_DIR) && go test -v -cover -short

# ---------------------------------------------------------------------------
# go-build — Build binary go-extract
# ---------------------------------------------------------------------------
.PHONY: go-build
go-build:
	@echo "Building go-extract binary ..."
	cd $(GO_EXTRACT_DIR) && go build -o bin/go-extract .

# ---------------------------------------------------------------------------
# go-run — Jalankan go-extract
#   make go-run                         → hari ini
#   make go-run DATE=2026-05-01         → 1 hari (5 Mei 2026)
#   make go-run START=2026-05-01 END=2026-05-10  → range
# ---------------------------------------------------------------------------
.PHONY: go-run
go-run:
	@echo "Running go-extract ..."
	cd $(GO_EXTRACT_DIR) && go run . -date "$(DATE)" -start-date "$(START)" -end-date "$(END)"

# ---------------------------------------------------------------------------
# go-tidy — Rapikan go.mod (go mod tidy)
# ---------------------------------------------------------------------------
.PHONY: go-tidy
go-tidy:
	@echo "Running go mod tidy ..."
	cd $(GO_EXTRACT_DIR) && go mod tidy

.PHONY: spark-transform
spark-transform:
	@echo "Running Spark transformation notebook ..."
	cd dags/spark-transform && python transform.py

.PHONY: glue-build
glue-build:
	@echo "Building custom Glue image ..."
	docker build -t franchise-glue-custom:latest -f infrastructure/docker/Dockerfile.glue .

.PHONY: glue-run
glue-run:
	@./scripts/run-spark-glue.sh $(ARGS)

S3_SCRIPTS_BUCKET = franchise-pipeline-dev-glue-scripts
SCRIPT_LOCAL_PATH = dags/spark-transform/transform_glue.py
SCRIPT_S3_PATH = s3://$(S3_SCRIPTS_BUCKET)/transform_glue.py
DEPS_LOCAL_DIR = dags/spark-transform/modules
DEPS_ZIP_PATH = /tmp/schemas.zip
DEPS_S3_PATH = s3://$(S3_SCRIPTS_BUCKET)/dependencies/schemas.zip
GLUE_JOB_NAME = franchise-pipeline-dev-bronze-to-silver

# Zip & upload dependencies (modules/*) ke S3
.PHONY: upload-deps
upload-deps:
	@echo "📦 Zipping dependencies..."
	cd $(DEPS_LOCAL_DIR)/.. && zip -r $(DEPS_ZIP_PATH) modules/
	@echo "📤 Uploading dependencies to S3..."
	aws s3 cp $(DEPS_ZIP_PATH) $(DEPS_S3_PATH)
	@echo "✅ Dependencies uploaded to $(DEPS_S3_PATH)"

# Upload script transform_glue.py ke S3
.PHONY: upload-script
upload-script:
	@echo "📤 Uploading $(SCRIPT_LOCAL_PATH) to S3..."
	aws s3 cp $(SCRIPT_LOCAL_PATH) $(SCRIPT_S3_PATH)
	@echo "✅ Script uploaded to $(SCRIPT_S3_PATH)"

# Upload all (script + deps) + jalankan Glue job (kasih DATE=YYYY-MM-DD)
.PHONY: deploy-and-run
deploy-and-run: upload-script upload-deps
	@echo "🚀 Running Glue job: $(GLUE_JOB_NAME)..."
	aws glue start-job-run \
		--job-name $(GLUE_JOB_NAME) \
		--arguments '{"--date":"$(DATE)"}'
