{% snapshot snp_customers %}

{{
    config(
      target_database='awsdatacatalog',
      target_schema='franchise_pipeline_dev_athena_db',
      unique_key='customer_id',
      strategy='timestamp',
      updated_at='updated_at',
      format='parquet',
    )
}}

SELECT
    CAST(customer_id AS VARCHAR) AS customer_id,
    customer_name,
    email,
    phone,
    created_at,
    updated_at,
    CAST(EXTRACT(year FROM updated_at) AS VARCHAR) AS year,
    CAST(EXTRACT(month FROM updated_at) AS VARCHAR) AS month,
    CAST(EXTRACT(day FROM updated_at) AS VARCHAR) AS day
FROM {{ source('silver_data', 'customers') }}

{% endsnapshot %}
