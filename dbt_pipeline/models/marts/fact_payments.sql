{{ config(
    materialized='incremental',
    format='parquet',
    partitioned_by=['year', 'month', 'day'],
    incremental_strategy='insert_overwrite',
    unique_key=['payment_id']
) }}

WITH fact_source AS (
    SELECT
        p.payment_id,
        p.order_id,
        p.payment_method,
        p.payment_status,
        p.amount,
        p.paid_at,
        p.provider_reference,

        o.customer_id,
        o.outlet_id,
        o.cashier_id,
        o.order_status,
        o.created_at AS order_created_at,
        CAST(p.paid_at AS DATE) AS payment_date,

        p.year,
        p.month,
        p.day
    FROM {{ ref('stg_payment') }} p
    JOIN {{ ref('stg_orders') }} o
        ON p.order_id = o.order_id
    WHERE o.data_quality_status = 'valid'
    {% if is_incremental() %}
        AND p.year = '{{ var("execution_date", "2026-09-09")[0:4] }}'
        AND p.month = '{{ var("execution_date", "2026-09-09")[5:7] }}'
        AND p.day = '{{ var("execution_date", "2026-09-09")[8:10] }}'
    {% endif %}
),
deduplicated AS (
    SELECT
        fact_source.*,
        ROW_NUMBER() OVER (
            PARTITION BY payment_id
            ORDER BY paid_at DESC
        ) AS row_num
    FROM fact_source
)

SELECT payment_id, order_id, payment_method, payment_status, amount,
       paid_at, provider_reference, customer_id, outlet_id, cashier_id,
       order_status, order_created_at, payment_date, year, month, day
FROM deduplicated
WHERE row_num = 1
