{{ config(
    materialized='table',
    format='parquet'
) }}

SELECT
    menu_id,
    menu_name,
    category,
    CASE
        WHEN category IN ('Pastry', 'Heavy Meal')      THEN 'Makanan'
        WHEN category IN ('Coffee', 'Non-Coffee')       THEN 'Minuman'
        ELSE 'Lainnya'
    END AS category_group,
    base_price,
    price_tier_1,
    price_tier_2,
    price_tier_3,
    CASE
        WHEN base_price <= 10000 THEN 'Value'
        WHEN base_price <= 17000 THEN 'Core'
        ELSE                          'Signature'
    END AS price_segment,
    CASE
        WHEN is_promo_active = 'true' THEN 'Active'
        ELSE 'Inactive'
    END AS promo_status,
    updated_at,
    dbt_valid_from as row_start_date,
    dbt_valid_to as row_end_date,
    -- Membuat kolom flag boolean agar orang BI gampang filter harga yang aktif sekarang
    case 
        when dbt_valid_to is null then true 
        else false 
    end as is_current_active
FROM {{ ref('snp_menu_master') }}
