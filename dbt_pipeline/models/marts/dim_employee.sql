{{ config(
    materialized='table',
    format='parquet'
) }}

SELECT
    employee_id,
    employee_name,
    employee_role,
    outlet_id,
    employment_status,
    created_at,
    updated_at,
    dbt_valid_from AS row_start_date,
    dbt_valid_to AS row_end_date,
    CASE
        WHEN dbt_valid_to IS NULL THEN true
        ELSE false
    END AS is_current_active
FROM {{ ref('snp_employees') }}
