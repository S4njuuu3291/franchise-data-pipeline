SELECT *
FROM {{ source('silver_data', 'payments') }}
