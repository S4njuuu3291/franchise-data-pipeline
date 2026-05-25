# Plan

Timestamp: 26-05-2026 07:30:00 WIB
## Phase 1 — Schema & Documentation
- Add initial content to `README.md`
- Design simulation database schema (primary & replica)
Status: ✅ Completed


## Phase 2 — Replication Setup
- Set up primary database (write WAL logs)
- Set up replica database (read & apply WAL logs to stay in sync)

## Phase 3 — Data Ingestion
- Set up FastAPI server
- Use Faker library to generate fake data
- Insert generated data into primary database
