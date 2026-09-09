{{ config(
    materialized='table',
    format='parquet',
    partitioned_by=['year', 'month', 'day']
) }}

WITH payment_summary AS (
    SELECT
        order_id,
        COUNT(*) AS payment_count,
        SUM(amount) AS total_paid_amount,
        SUM(
            CASE
                WHEN payment_status = 'SUCCESS' THEN amount
                ELSE 0
            END
        ) AS successful_paid_amount,
        MAX(paid_at) AS latest_payment_at,
        MAX(
            CASE
                WHEN payment_status = 'SUCCESS' THEN 1
                ELSE 0
            END
        ) = 1 AS has_successful_payment
    FROM {{ ref('fact_payments') }}
    GROUP BY order_id
),

order_items AS (
    SELECT
        foi.item_id,
        foi.order_id,
        foi.menu_id,
        foi.quantity,
        foi.price_per_item,
        foi.subtotal,
        foi.outlet_id,
        foi.cashier_id,
        foi.total_amount,
        foi.payment_method,
        foi.order_date,
        foi.created_at,
        o.data_quality_status,
        foi.year,
        foi.month,
        foi.day,
        o.customer_id,
        o.order_status
    FROM {{ ref('fact_order_items') }} foi
    JOIN {{ ref('stg_orders') }} o
        ON foi.order_id = o.order_id
),

enriched AS (
    SELECT
        oi.item_id,
        oi.order_id,
        oi.order_date,
        oi.order_status,
        oi.total_amount,
        oi.payment_method,
        oi.created_at AS order_created_at,
        oi.data_quality_status,

        CAST(oi.menu_id AS VARCHAR) AS menu_id,
        menu.menu_name,
        menu.category,
        oi.quantity,
        oi.price_per_item,
        oi.subtotal,

        CAST(oi.customer_id AS VARCHAR) AS customer_id,
        customer.customer_name,
        customer.email AS customer_email,
        customer.phone AS customer_phone,

        CAST(oi.outlet_id AS VARCHAR) AS outlet_id,
        outlet.outlet_name,
        outlet.city AS outlet_city,
        outlet.region_tier,

        CAST(oi.cashier_id AS VARCHAR) AS employee_id,
        employee.employee_name,
        employee.employee_role,

        COALESCE(pay.payment_count, 0) AS payment_count,
        COALESCE(pay.total_paid_amount, 0) AS total_paid_amount,
        COALESCE(pay.successful_paid_amount, 0) AS successful_paid_amount,
        pay.latest_payment_at,
        COALESCE(pay.has_successful_payment, false) AS has_successful_payment,

        oi.year,
        oi.month,
        oi.day
    FROM order_items oi
    LEFT JOIN {{ ref('dim_menu') }} menu
        ON CAST(oi.menu_id AS VARCHAR) = menu.menu_id
        AND menu.is_current_active = true
    LEFT JOIN {{ ref('dim_customer') }} customer
        ON CAST(oi.customer_id AS VARCHAR) = customer.customer_id
        AND customer.is_current_active = true
    LEFT JOIN {{ ref('dim_outlet') }} outlet
        ON CAST(oi.outlet_id AS VARCHAR) = outlet.outlet_id
        AND outlet.is_current_active = true
    LEFT JOIN {{ ref('dim_employee') }} employee
        ON CAST(oi.cashier_id AS VARCHAR) = employee.employee_id
        AND employee.is_current_active = true
    LEFT JOIN payment_summary pay
        ON oi.order_id = pay.order_id
)

SELECT *
FROM enriched
