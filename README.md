# Franchise Data Pipeline

> **End-to-end ETL pipeline for franchise restaurant transactional data.**
> From PostgreSQL -> Bronze (S3) -> Silver (AWS Glue) -> Gold (dbt on Athena)

---

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Go](https://img.shields.io/badge/Go-1.21-00ADD8?logo=go&logoColor=white)
![Apache Spark](https://img.shields.io/badge/Spark-3.5-E25A1C?logo=apachespark&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-1.11-FF694B?logo=dbt&logoColor=white)
![Apache Airflow](https://img.shields.io/badge/Airflow-3.0-017CEE?logo=apacheairflow&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-1.11-844FBA?logo=terraform&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

![AWS Glue](https://img.shields.io/badge/AWS_Glue-FF9900?logo=amazonaws&logoColor=white)
![AWS Athena](https://img.shields.io/badge/AWS_Athena-FF9900?logo=amazonathena&logoColor=white)
![AWS S3](https://img.shields.io/badge/AWS_S3-569A31?logo=amazons3&logoColor=white)
![AWS Glue Catalog](https://img.shields.io/badge/Glue_Catalog-232F3E?logo=amazonaws&logoColor=white)

---

## Pipeline Architecture

![Architecture Diagram](assets/architecture.png)

The pipeline flows data through four layers:

| Layer | Location | Format | Description |
|---|---|---|---|
| **Source** | PostgreSQL (OLTP) | Tables | Transactional database with WAL-based primary-replica replication |
| **Bronze** | S3: data-lake-bronze | CSV | Raw extracted data, partitioned by date for transaction tables |
| **Silver** | S3: data-lake-silver | Parquet | Cleaned and validated data with business rules applied via PySpark |
| **Gold** | S3: data-lake-gold | Parquet | Analytics-ready tables built by dbt (star schema: facts + dimensions) |

---

## Technology Stack

| Category | Technology | Purpose |
|---|---|---|
| **Database** | PostgreSQL 15 | Source OLTP database with primary-replica replication |
| **Extraction** | Go 1.21 | Custom binary reads replica and writes CSV to Bronze S3 |
| **Orchestration** | Apache Airflow 3.0 | Schedules and orchestrates the daily pipeline DAG |
| **Transformation** | AWS Glue (PySpark 3.5) | Bronze to Silver: data cleansing, validation, quarantine logic |
| **Analytics Modeling** | dbt 1.11 (Cosmos) | Silver to Gold: staging, SCD Type 2 snapshots, dimensional marts |
| **Query Engine** | AWS Athena | Serverless SQL queries on Gold layer tables |
| **Infrastructure** | Terraform 1.11 | Provisions all AWS resources (S3, Glue, Athena, IAM) |
| **Containerization** | Docker / Compose | Local development environment for Airflow and PostgreSQL |


## AWS Infrastructure

All infrastructure is provisioned via Terraform (`infrastructure/environments/dev`).

### S3 Buckets

| Bucket | Purpose |
|---|---|
| `franchise-pipeline-dev-data-lake-bronze` | Raw CSV data from Go extractor |
| `franchise-pipeline-dev-data-lake-silver` | Cleaned Parquet data from Glue |
| `franchise-pipeline-dev-data-lake-gold` | Analytics-ready tables from dbt |
| `franchise-pipeline-dev-data-lake-quarantine` | Invalid or suspicious records |
| `franchise-pipeline-dev-athena-query-results` | Athena query output storage |
| `franchise-pipeline-dev-glue-scripts` | Glue job scripts and dependencies |
| `franchise-pipeline-dev-state-lock` | Terraform state lock |

### AWS Glue

| Resource | Name | Description |
|---|---|---|
| **Glue Job** | `franchise-pipeline-dev-bronze-to-silver` | PySpark job: reads Bronze CSV, validates, writes Silver Parquet |
| **IAM Role** | `franchise-pipeline-dev-glue-role` | Execution role with S3 and Glue permissions |

### AWS Athena

| Resource | Name |
|---|---|
| **Database** | `franchise_pipeline_dev_athena_db` |
| **Workgroup** | `franchise_pipeline_dev_workgroup` |
| **Tables** | `outlet_master`, `menu_master`, `orders`, `order_items` (partitioned by year/month/day) |

### Glue Catalog Tables

| Table | Source Location | Format | Partitioned |
|---|---|---|---|
| `outlet_master` | `silver/outlet_master/` | Parquet | No |
| `menu_master` | `silver/menu_master/` | Parquet | No |
| `orders` | `silver/orders/` | Parquet | year, month, day |
| `order_items` | `silver/order_items/` | Parquet | year, month, day |


## Database Schema (OLTP)

![ERD](assets/erd.png)

Refer to `struktur-oltp.yaml` and `SOURCE-SCHEMA.sql` for complete schema details.


## dbt Models & Lineage

The dbt project (`dbt_pipeline/`) transforms data from Silver to Gold.

![dbt DAG](assets/dbt-dag.png)


## Airflow DAG

The pipeline is orchestrated by a single DAG `sales_data_dbt_pipeline` scheduled daily.

![DAG Graph](assets/sales_data_dbt_pipeline-graph.png)


## Data Quality

### Bronze to Silver (Glue Job)

The Glue transformation applies multiple validation rules:

| Validation Rule | Action | Quarantine Location |
|---|---|---|
| Referential integrity (menu_id in menu_master) | Log warning + quarantine copy | `orphan_items/` |
| Referential integrity (outlet_id in outlet_master) | Log warning | - |
| Invalid payment_method | Log warning + quarantine copy | `invalid_payments/` |
| Price not matching any tier | Log warning + quarantine copy | `invalid_prices/` |
| Duplicate order_id detected | Log warning + quarantine copy | `duplicate_orders/` |
| Cashier transaction anomaly (z-score > 3) | Log warning + quarantine copy | `anomaly_cashiers/` |
| Order total vs item subtotal mismatch | Set data_quality_status flag + quarantine | `orders_discrepancies/` |

All data is still written to Silver layer with `data_quality_status` column for traceability. Bad records are also copied to the quarantine bucket for investigation.

### dbt Tests

| Test Type | Count | Models |
|---|---|---|
| not_null | 8 | All staging models, snapshots, dimensions, and fact tables |
| unique | 2 | `fact_order_items.item_id`, `dim_date.date` |
| relationships | 1 | `fact_order_items.order_date -> dim_date.date` |
| freshness | 1 | `silver_data.orders` (warn: 24h, error: 48h) |


## Setup & Usage

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Go 1.21+
- AWS CLI configured with appropriate credentials
- Terraform 1.11+ (for infrastructure deployment)

### Quick Start

```bash
# 1. Build and start Airflow
make docker-build
make docker-up

# 2. Initialize database schema
make init-schema

# 3. Seed master data
make seed-db

# 4. Generate transaction data (adjust dates in simulation_config.yaml)
make run-transactions
```

### Makefile Commands

| Command | Description |
|---|---|
| `make docker-up` | Start Airflow and supporting services |
| `make docker-down` | Stop all services |
| `make init-schema` | Inject SOURCE-SCHEMA.sql into primary database |
| `make seed-db` | Populate outlet_master and menu_master data |
| `make run-transactions` | Generate daily transaction data for date range |
| `make truncate-primary` | Truncate all tables in primary database |
| `make tf-apply-dev` | Apply Terraform infrastructure (dev) |
| `make athena-truncate-dbt` | Drop all dbt objects in Athena and clean S3 gold layer |
| `make worker-shell` | Open shell in Airflow worker container |

### Manual Pipeline Execution

```bash
# Trigger the full DAG from Airflow UI, or run manually:
docker compose exec airflow-worker bash -c \
  "cd /opt/airflow/dags/go-extract && go run main.go -date YYYY-MM-DD"
```


## Project Structure

```
.
|-- README.md
|-- SOURCE-SCHEMA.sql              # PostgreSQL source schema
|-- struktur-oltp.mmd              # ERD diagram (Mermaid)
|-- docker-compose.yml             # Airflow + PostgreSQL + Redis
|-- Dockerfile.airflow             # Custom Airflow image
|-- Makefile                       # Command center
|-- PLAN.md                        # Development roadmap
|-- config/
|   |-- airflow.cfg
|   |-- pipeline-config.yaml
|-- dags/
|   |-- dbt_sales_dag.py           # Airflow DAG definition
|   |-- go-extract/                # Go CSV extractor
|   |-- spark-transform/           # PySpark transform scripts
|-- dbt_pipeline/                  # dbt project
|   |-- models/
|   |   |-- staging/               # Staging views
|   |   |-- marts/                 # Dimension & fact tables
|   |-- snapshots/                 # SCD Type 2 snapshots
|   |-- dbt_project.yml
|-- data-generator/                # Faker-based data simulation
|-- infrastructure/
|   |-- modules/                   # Terraform modules
|   |-- environments/dev/          # Dev environment config
|-- assets/
|   |-- architecture.png           # Architecture diagram
|   |-- sales_data_dbt_pipeline-graph.png  # DAG visualization
