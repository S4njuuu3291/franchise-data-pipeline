{% snapshot snp_outlet_master %}

{{
    config(
      target_database='awsdatacatalog',
      target_schema='franchise_pipeline_dev_athena_db',
      unique_key='outlet_id',
      strategy='timestamp',
      updated_at='updated_at',
      format='parquet',
    )
}}

SELECT
    CAST(outlet_id AS VARCHAR) AS outlet_id,
    outlet_name,
    city,
    region_tier,
    created_at,
    updated_at,
    CAST(EXTRACT(year FROM updated_at) AS VARCHAR) AS year,
    CAST(EXTRACT(month FROM updated_at) AS VARCHAR) AS month,
    CAST(EXTRACT(day FROM updated_at) AS VARCHAR) AS day
FROM {{ source('silver_data', 'outlet_master') }}

{% endsnapshot %}
