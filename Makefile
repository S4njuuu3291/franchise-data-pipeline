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