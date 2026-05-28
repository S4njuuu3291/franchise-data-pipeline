{% snapshot snp_menu_master %}

{{
    config(
      target_database='awsdatacatalog',
      target_schema='franchise_pipeline_dev_athena_db',
      unique_key='menu_id',
      strategy='timestamp',
      updated_at='updated_at',
      format='parquet',
    )
}}

SELECT
    CAST(menu_id AS VARCHAR) AS menu_id,
    menu_name,
    category,
    base_price,
    price_tier_1,
    price_tier_2,
    price_tier_3,
    is_promo_active,
    updated_at,
    CAST(EXTRACT(year FROM updated_at) AS VARCHAR) AS year,
    CAST(EXTRACT(month FROM updated_at) AS VARCHAR) AS month,
    CAST(EXTRACT(day FROM updated_at) AS VARCHAR) AS day
FROM {{ source('silver_data', 'menu_master') }}

{% endsnapshot %}