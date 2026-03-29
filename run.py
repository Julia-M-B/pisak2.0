import logging

from pisak.modules.speller import run_speller
from pisak.logging_config import setup_logging

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    setup_logging()
    logger.info("Running the SPELLER module.")
    run_speller.main()