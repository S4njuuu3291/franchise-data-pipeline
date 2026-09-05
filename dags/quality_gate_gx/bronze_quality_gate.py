import logging

import great_expectations as gx
from great_expectations.exceptions.exceptions import NoAvailableBatchesError


logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.getLogger("great_expectations").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)


context = gx.get_context(mode="file")
site_name = "quality_gate_site"

try:
    master_checkpoint = context.checkpoints.get("master_data_checkpoint")
    transaction_checkpoint = context.checkpoints.get("transaction_data_checkpoint")

    logger.info("Running master data checkpoint")
    master_result = master_checkpoint.run()
    if not master_result.success:
        raise RuntimeError(
            "GX master data validation failed; stopping pipeline. "
            "See Data Docs for details."
        )
    logger.info("Master data validation passed")

    logger.info("Running transaction data checkpoint")
    transaction_result = transaction_checkpoint.run()
    if not transaction_result.success:
        raise RuntimeError(
            "GX transaction data validation failed; stopping pipeline. "
            "See Data Docs for details."
        )
    logger.info("Transaction data validation passed")

except NoAvailableBatchesError as exc:
    raise RuntimeError(
        "Required Bronze batch is unavailable; stopping pipeline. "
        "Check the configured S3 paths and extracted data."
    ) from exc

context.build_data_docs(site_names=site_name)
logger.info("Data Docs rebuilt: %s", site_name)
