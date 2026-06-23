# Plan

Timestamp: 26-05-2026 07:30:00 WIB
## Phase 1 — Schema & Documentation
- Add initial content to `README.md`
- Design simulation database schema (primary & replica)
Status: ✅ Completed

Timestamp: 26-05-2026 10:00:00 WIB
## Phase 2 — Replication & Data Generation
- Set up primary database (write WAL logs)
- Set up replica database (read & apply WAL logs to stay in sync)
- Add .sql files for create tables
- Use Faker library to generate fake data
- Insert generated data into primary database
Status: ✅ Completed

Timestamp: 26-05-2026 13:10:00 WIB
## Phase 3 — Setup Bronze Layer Pipeline & AWS Infrastructure
- Setup Terraform for Bronze layer infrastructure (S3)
- Create scripts to extract data from replica and load into S3 (Bronze layer)
- Create unit tests for data extraction and loading scripts
Status: ✅ Done

Timestamp: 27-05-2026 07:00:00 WIB
## Phase 4 — Setup Silver Layer Pipeline & AWS Infrastructure
- Create Logic and Business Rules for Silver layer transformation
- Setup Terraform for Silver layer infrastructure (S3, AWS Glue, Athena)
- Create scripts to transform data from Bronze layer and load into Silver layer (AWS Glue)
<!-- - Create unit tests for data transformation and loading scripts -->
Status: ✅ Done

Timestamp: 28-05-2026 13:00:00 WIB
## Phase 5 — dbt Modeling & Testing
- Setup Terraform bucket for athena query results
- Create dbt models for Silver layer data
- Create dbt snapshots for slowly changing dimensions (SCD)
- Create dbt models for Gold layer data (mart tables)
- Create dbt tests for data quality and integrity
Status: ✅ Done

## Phase 6 — Setup Airflow Orchestration
- Setup Airflow infrastructure ✅ Done
- Create DAG task for bronze ✅ Done
- Setup local Glue development environment ✅ Done
- Test Glue transformation script locally ✅ Done
- Setup Terraform for AWS Glue, upload and test ✅ Done
- Create DAG task for silver ✅ Done
- Create dbt documentation for data models and lineage ✅ Done
- Create DAG task for dbt transformations ✅ Done

Status: ✅ Done