{{ config(
    materialized='table',
    format='parquet'
) }}

WITH date_series AS (
    SELECT CAST(date AS DATE) AS date
    FROM UNNEST(
        SEQUENCE(
            DATE '2025-01-01',
            DATE '2026-12-31',
            INTERVAL '1' DAY
        )
    ) AS t(date)
)

SELECT
    date,
    EXTRACT(year FROM date) AS year,
    EXTRACT(month FROM date) AS month,
    EXTRACT(day FROM date) AS day,
    EXTRACT(quarter FROM date) AS quarter,
    EXTRACT(week FROM date) AS week_of_year,
    EXTRACT(day_of_week FROM date) AS day_of_week,
    CASE EXTRACT(day_of_week FROM date)
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
        WHEN 7 THEN 'Sunday'
    END AS day_name,
    CASE EXTRACT(month FROM date)
        WHEN 1  THEN 'January'
        WHEN 2  THEN 'February'
        WHEN 3  THEN 'March'
        WHEN 4  THEN 'April'
        WHEN 5  THEN 'May'
        WHEN 6  THEN 'June'
        WHEN 7  THEN 'July'
        WHEN 8  THEN 'August'
        WHEN 9  THEN 'September'
        WHEN 10 THEN 'October'
        WHEN 11 THEN 'November'
        WHEN 12 THEN 'December'
    END AS month_name,
    CASE
        WHEN EXTRACT(day_of_week FROM date) IN (6, 7) THEN 'Weekend'
        ELSE 'Weekday'
    END AS is_weekend,
    CAST(EXTRACT(year FROM date) AS VARCHAR) || '-' || LPAD(CAST(EXTRACT(month FROM date) AS VARCHAR), 2, '0') AS year_month
FROM date_series
