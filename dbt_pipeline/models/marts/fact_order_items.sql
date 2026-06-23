{{ config(
    materialized='incremental',
    format='parquet',
    partitioned_by=['year', 'month', 'day'],
    incremental_strategy='insert_overwrite',
    unique_key=['item_id']
) }}

WITH fact AS (
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
        AND oi.year  = '{{ var("execution_date", "2026")[:4] }}'
        AND oi.month = '{{ var("execution_date", "06")[5:7] }}'
        AND oi.day   = '{{ var("execution_date", "23")[8:10] }}'
    {% endif %}
)

SELECT * FROM fact