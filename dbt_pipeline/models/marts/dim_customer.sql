{{ config(
    materialized='table',
    format='parquet'
) }}

SELECT
    customer_id,
    customer_name,
    email,
    phone,
    created_at,
    updated_at,
    dbt_valid_from AS row_start_date,
    dbt_valid_to AS row_end_date,
    CASE
        WHEN dbt_valid_to IS NULL THEN true
        ELSE false
    END AS is_current_active
FROM {{ ref('snp_customers') }}
