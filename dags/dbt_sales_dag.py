from datetime import datetime,timedelta
from airflow import DAG
import logging
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from pathlib import Path
from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig, ExecutionConfig, ExecutionMode
from cosmos.profiles import AthenaAccessKeyProfileMapping # Cosmos built-in profile mapper
from airflow.operators.bash import BashOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
# ── 1. CONFIG PATH ───────────────────────────────────────────────────
# Tunjuk langsung ke folder project dbt lokalmu
DBT_PROJECT_DIR = Path("/opt/airflow/dbt_pipeline/") # Path saat di-mount ke docker/airflow

# ── Glue Job Config ───────────────────────────────────────────────────
GLUE_JOB_NAME = "franchise-pipeline-dev-bronze-to-silver"
CONN_ID = "aws_default"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

default_args = {
    "owner": "data_engineer",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="sales_data_dbt_pipeline",
    default_args=default_args,
    description="A DAG to run dbt transformations for sales data",
    schedule="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["nyc-taxi", "etl"],
) as dag:
    date = "{{ ds }}"

    start_pipeline = EmptyOperator(task_id="start_pipeline")

    extract_task = BashOperator(
        task_id="extract_data",
        bash_command='cd /opt/airflow/dags/go-extract && go run main.go -date "{{ ds }}"',
    )

    transform_task = GlueJobOperator(
        task_id="bronze_to_silver",
        job_name=GLUE_JOB_NAME,
        script_args={
            "--date": date,
        },
        region_name="ap-southeast-1",
        aws_conn_id=CONN_ID,
        wait_for_completion=True,
    )

    dbt_transform_gold = DbtTaskGroup(
        group_id="dbt_gold_transformation",
        project_config=ProjectConfig(
            manifest_path=Path("/opt/airflow/dbt_pipeline/target/manifest.json"), # Cosmos membaca manifest
            project_name="dbt_pipeline",
            dbt_vars={
                "execution_date": "{{ ds }}",
            },
        ),
        profile_config=ProfileConfig(
            profile_name="franchise_athena_profile",
            target_name="dev",
            profile_mapping=AthenaAccessKeyProfileMapping(
                conn_id=CONN_ID,
                profile_args={
                    "database": "awsdatacatalog",
                    "schema": "franchise_pipeline_dev_athena_db",
                    "s3_staging_dir": "s3://franchise-pipeline-dev-athena-query-results/",
                },
            ),
        ),
        execution_config=ExecutionConfig(
            dbt_project_path=DBT_PROJECT_DIR,
            execution_mode=ExecutionMode.LOCAL,
        ),
    )

    end_pipeline = EmptyOperator(task_id="end_pipeline")

    # hello_task >> start_pipeline >> dbt_transform_gold >> end_pipeline
    start_pipeline >> extract_task >> transform_task >> dbt_transform_gold >> end_pipeline