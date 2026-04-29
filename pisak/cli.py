import argparse
import logging
import os
from typing import Sequence

from pisak.logging_config import setup_logging
from pisak.settings import DEFAULT_PREDICTION_MODEL_NAME

logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Pisak application.")
    parser.add_argument(
        "--model",
        default=DEFAULT_PREDICTION_MODEL_NAME,
        help=(
            "Prediction model filename from pisak/predictions directory "
            f"(default: {DEFAULT_PREDICTION_MODEL_NAME})."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    os.environ["PISAK_MODEL_NAME"] = args.model
    setup_logging()
    logger.info("Running the SPELLER module with model: %s", args.model)

    from pisak.modules.speller import run_speller

    run_speller.main()
