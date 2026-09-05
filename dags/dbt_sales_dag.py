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
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="sales_data_dbt_pipeline",
    default_args=default_args,
    description="A DAG to run dbt transformations for sales data",
    schedule="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["etl"],
) as dag:
# Sintaks yang PALING BENAR dan AMAN:
    date = "{{ dag_run.conf.get('execution_date', ds) }}"

    start_pipeline = EmptyOperator(task_id="start_pipeline")

    setup_gx_task = BashOperator(
        task_id="setup_gx",
        bash_command=(
            "cd /opt/airflow/dags/quality_gate_gx && "
            "python setup.py --date "
            '"{{ dag_run.conf.get(\'execution_date\', ds) }}"'
        ),
    )

    extract_task = BashOperator(
        task_id="extract_data",
        bash_command='cd /opt/airflow/dags/go-extract && go run main.go -date "{{ dag_run.conf.get(\'execution_date\', ds) }}"',
    )

    bronze_quality_gate_task = BashOperator(
        task_id="bronze_quality_gate",
        bash_command="cd /opt/airflow/dags/quality_gate_gx && python bronze_quality_gate.py",
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

    silver_quality_gate_task = BashOperator(
        task_id="silver_quality_gate",
        bash_command=(
            "cd /opt/airflow/dags/quality_gate_gx && "
            "python setup_and_run_silver_quality_gate.py --date "
            '"{{ dag_run.conf.get(\'execution_date\', ds) }}"'
        ),
    )

    dbt_transform_gold = DbtTaskGroup(
        group_id="dbt_gold_transformation",
        project_config=ProjectConfig(
            manifest_path=Path("/opt/airflow/dbt_pipeline/target/manifest.json"), # Cosmos membaca manifest
            project_name="dbt_pipeline",
        ),
        profile_config=ProfileConfig(
            profile_name="franchise_athena_profile",
            target_name="dev",
            profile_mapping=AthenaAccessKeyProfileMapping(
                conn_id=CONN_ID,
                profile_args={
                    "database": "awsdatacatalog",
                    "schema": "franchise_pipeline_dev_athena_db",
                    # Query results sementara Athena tetap dipisahkan dari data Gold.
                    "s3_staging_dir": "s3://franchise-pipeline-dev-athena-query-results/",
                    # Lokasi permanen tabel/model dbt Gold.
                    "s3_data_dir": "s3://franchise-pipeline-dev-data-lake-gold/",
                    "s3_data_naming": "schema_table",
                },
            ),
        ),
        execution_config=ExecutionConfig(
            dbt_project_path=DBT_PROJECT_DIR,
            execution_mode=ExecutionMode.LOCAL,
        ),
        # Teruskan tanggal Airflow ke dbt saat task dieksekusi.
        # ProjectConfig.dbt_vars hanya dipakai saat parsing project pada setup ini.
        operator_args={
            "vars": {"execution_date": "{{ dag_run.conf.get('execution_date', '2026-05-01') }}"},
        },
    )

    end_pipeline = EmptyOperator(task_id="end_pipeline")

    # hello_task >> start_pipeline >> dbt_transform_gold >> end_pipeline
    start_pipeline >> setup_gx_task >> extract_task >> bronze_quality_gate_task >> transform_task >> silver_quality_gate_task >> dbt_transform_gold >> end_pipeline
