{% snapshot snp_employees %}

{{
    config(
      target_database='awsdatacatalog',
      target_schema='franchise_pipeline_dev_athena_db',
      unique_key='employee_id',
      strategy='timestamp',
      updated_at='updated_at',
      format='parquet',
    )
}}

SELECT
    CAST(employee_id AS VARCHAR) AS employee_id,
    employee_name,
    employee_role,
    CAST(outlet_id AS VARCHAR) AS outlet_id,
    employment_status,
    created_at,
    updated_at,
    CAST(EXTRACT(year FROM updated_at) AS VARCHAR) AS year,
    CAST(EXTRACT(month FROM updated_at) AS VARCHAR) AS month,
    CAST(EXTRACT(day FROM updated_at) AS VARCHAR) AS day
FROM {{ source('silver_data', 'employees') }}

{% endsnapshot %}
