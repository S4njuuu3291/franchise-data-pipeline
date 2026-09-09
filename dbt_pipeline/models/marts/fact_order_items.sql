{{ config(
    materialized='incremental',
    format='parquet',
    partitioned_by=['year', 'month', 'day'],
    incremental_strategy='insert_overwrite',
    unique_key=['item_id']
) }}

WITH fact_source AS (
    SELECT
        oi.item_id,
        oi.order_id,
        oi.menu_id,
        oi.quantity,
        oi.price_per_item,
        oi.subtotal,
        o.outlet_id,
        o.cashier_id,
        o.total_amount,
        o.payment_method,
        CAST(o.created_at AS DATE) AS order_date,
        o.created_at,
        oi.year,
        oi.month,
        oi.day
    FROM {{ ref('stg_orders') }} o
    JOIN {{ ref('stg_order_items') }} oi ON o.order_id = oi.order_id
    WHERE o.data_quality_status = 'valid'
    {% if is_incremental() %}
        AND oi.year  = '{{ var("execution_date", "2026-09-09")[:4] }}'
        AND oi.month = '{{ var("execution_date", "2026-09-09")[5:7] }}'
        AND oi.day   = '{{ var("execution_date", "2026-09-09")[8:10] }}'
    {% endif %}
),
deduplicated AS (
    SELECT
        fact_source.*,
        ROW_NUMBER() OVER (
            PARTITION BY item_id
            ORDER BY created_at DESC
        ) AS row_num
    FROM fact_source
)

SELECT item_id, order_id, menu_id, quantity, price_per_item, subtotal,
       outlet_id, cashier_id, total_amount, payment_method, order_date,
       created_at, year, month, day
FROM deduplicated
WHERE row_num = 1
