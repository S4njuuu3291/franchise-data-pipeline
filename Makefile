docker-up:
	docker compose up -d

docker-down:
	docker compose down

pm-db-shell:
	docker compose exec postgres-primary psql -U replicator_user -d main_db

repl-db-shell:
	docker compose exec postgres-replica psql -U replicator_user -d main_db

docker-restart:
	docker compose restart

# ---------------------------------------------------------------------------
# init-schema — Inject SOURCE-SCHEMA.sql ke primary database
# ---------------------------------------------------------------------------
init-schema:
	@echo "Waiting for PostgreSQL at $(DB_HOST):$(DB_PORT) ..."
	@until docker compose exec postgres-primary pg_isready -U replicator_user > /dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "Injecting SOURCE-SCHEMA.sql into primary ..."
	@docker compose exec -T postgres-primary psql -U replicator_user -d main_db < SOURCE-SCHEMA.sql
	@echo "Schema injected successfully."

# ---------------------------------------------------------------------------
# truncate-primary — Hapus semua data di primary (reset tabel)
# ---------------------------------------------------------------------------
.PHONY: truncate-primary
truncate-primary:
	@echo "Truncating all tables in primary database ..."
	@docker compose exec -T postgres-primary psql -U replicator_user -d main_db -c \
		"TRUNCATE TABLE order_items, orders, menu_master, outlet_master RESTART IDENTITY CASCADE;"
	@echo "All tables truncated."

# ---------------------------------------------------------------------------
# drop-schema — Hapus semua tabel (DROP TABLE)
# ---------------------------------------------------------------------------
.PHONY: drop-schema
drop-schema:
	@echo "Dropping all tables in primary database ..."
	@docker compose exec -T postgres-primary psql -U replicator_user -d main_db -c \
		"DROP TABLE IF EXISTS order_items, orders, menu_master, outlet_master CASCADE;"
	@echo "All tables dropped."

TF_DEV_DIR = infrastructure/environments/dev

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
# ---------------------------------------------------------------------------
.PHONY: go-run
go-run:
	@echo "Running go-extract ..."
	cd $(GO_EXTRACT_DIR) && go run .

# ---------------------------------------------------------------------------
# go-tidy — Rapikan go.mod (go mod tidy)
# ---------------------------------------------------------------------------
.PHONY: go-tidy
go-tidy:
	@echo "Running go mod tidy ..."
	cd $(GO_EXTRACT_DIR) && go mod tidy