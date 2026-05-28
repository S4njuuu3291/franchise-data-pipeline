{{ config(
    materialized='table',
    format='parquet'
) }}

SELECT
    outlet_id,
    outlet_name,
    city,
    region_tier,
    CASE
        WHEN region_tier = '1' THEN 'Prime'
        WHEN region_tier = '2' THEN 'Secondary'
        WHEN region_tier = '3' THEN 'Tier 3'
        ELSE 'Unknown'
    END AS region_label,
    created_at,
    updated_at,
    dbt_valid_from as row_start_date,
    dbt_valid_to as row_end_date,
    -- Membuat kolom flag boolean agar orang BI gampang filter harga yang aktif sekarang
    case 
        when dbt_valid_to is null then true 
        else false 
    end as is_current_active
FROM {{ ref('snp_outlet_master') }}