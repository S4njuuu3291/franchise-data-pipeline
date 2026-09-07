import logging
import os
from datetime import date, datetime
from pathlib import Path

import great_expectations as gx
from great_expectations.exceptions.exceptions import NoAvailableBatchesError
import psycopg2


logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.getLogger("great_expectations").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)


def connect_to_gx_metadata_db():
    """Connect to GX metadata DB from Airflow or from the local host."""
    container_secret = Path("/run/secrets/gx_metadata_password")
    local_secret = Path(__file__).resolve().parents[2] / "docker/secrets/gx_metadata_password.txt"

    if container_secret.exists():
        password_path = container_secret
        host = "gx-metadata-db"
        port = 5432
    else:
        password_path = local_secret.resolve()
        host = "localhost"
        port = 5434

    password = password_path.read_text(encoding="utf-8").strip()
    return psycopg2.connect(
        host=host,
        port=port,
        dbname="gx_metadata",
        user="gx_metadata_user",
        password=password,
        sslmode=os.environ.get("GX_METADATA_SSLMODE", "require"),
    )


context = gx.get_context(mode="file")
site_name = "quality_gate_site"

try:
    checkpoints = {
        "master_data_checkpoint": context.checkpoints.get("master_data_checkpoint"),
        "transaction_data_checkpoint": context.checkpoints.get("transaction_data_checkpoint"),
    }

    with connect_to_gx_metadata_db() as metadata_connection:

        for checkpoint_name, checkpoint in checkpoints.items():
            logger.info("Running checkpoint: %s", checkpoint_name)
            checkpoint_result = checkpoint.run()

            for validation_id, validation_result in checkpoint_result.run_results.items():
                # A. Ambil nama Data Asset secara aman di versi 1.x
                meta = validation_result.get("meta", {})
                run_id = meta.get("run_id")
                execution_datetime = (
                    getattr(run_id, "run_time", None)
                    or getattr(run_id, "run_name", None)
                )
                execution_date = (
                    execution_datetime.date()
                    if isinstance(execution_datetime, datetime)
                    else execution_datetime
                    if isinstance(execution_datetime, date)
                    else date.today()
                )
                stage = "Bronze"

                asset_name = meta.get("active_batch_definition", {}).get("data_asset_name", "unknown_asset")
                statistics = validation_result.get("statistics", {})
                success_rate = statistics.get("success_percent", 0.0)
                total_records = statistics.get("evaluated_expectations_count", 0) # Menangkap volume harian

                # C. Tentukan status kelulusan asset
                status = "SUCCESS" if validation_result.get("success", False) else "FAILED"

                volume = 0
                # Kita cari aturan khusus row count di dalam list hasil evaluasi
                for individual_result in validation_result.get("results", []):
                    expect_type = individual_result.get("expectation_config", {}).get("type", "")

                    # Jika aturan tersebut adalah pengecekan jumlah baris
                    if expect_type == "expect_table_row_count_to_be_between":
                        # Ambil nilai baris asli yang diobservasi oleh GX dari S3/Tabel
                        volume = individual_result.get("result", {}).get("observed_value", 0)
                        break

                with metadata_connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO public.data_quality_ledger (
                            validation_id,
                            execution_date,
                            stage,
                            asset_name,
                            volume,
                            success_rate,
                            status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(validation_id),
                            execution_date,
                            stage,
                            asset_name,
                            volume,
                            success_rate,
                            status,
                        ),
                    )

                logger.info(
                    "Metadata saved: validation_id=%s execution_date=%s stage=%s "
                    "asset=%s volume=%s success_rate=%s status=%s",
                    validation_id,
                    execution_date,
                    stage,
                    asset_name,
                    volume,
                    success_rate,
                    status,
                )

            if not checkpoint_result.success:
                raise RuntimeError(
                    f"GX checkpoint failed: {checkpoint_name}. "
                    "See Data Docs for details."
                )

            logger.info("Checkpoint passed: %s", checkpoint_name)

        metadata_connection.commit()

except NoAvailableBatchesError as exc:
    raise RuntimeError(
        "Required Bronze batch is unavailable; stopping pipeline. "
        "Check the configured S3 paths and extracted data."
    ) from exc

context.build_data_docs(site_names=site_name)
logger.info("Data Docs rebuilt: %s", site_name)
