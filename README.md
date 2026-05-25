# Franchise Data Pipeline

Pipeline ETL data transaksional franchise restoran.

## Stack

- **Database:** PostgreSQL
- **Ingestion:** FastAPI + Faker
- **Replication:** WAL-based (primary → replica)

## Struktur Database

| Tabel | Keterangan |
|---|---|
| `outlet_master` | Data master cabang restoran |
| `menu_master` | Data master menu produk |
| `orders` | Header transaksi pesanan |
| `order_items` | Detail baris item dalam pesanan |

Lihat [`struktur-oltp.yaml`](struktur-oltp.yaml) untuk skema lengkap.
