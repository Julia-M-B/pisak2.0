import argparse
import logging
import os
from typing import Sequence

from app.logging_config import setup_logging
from app.settings import DEFAULT_PREDICTION_MODEL_NAME

logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the experimental environment.")
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_PREDICTION_MODEL_NAME,
        help=(
            "Prediction model filename from app/predictions directory "
            f"(default: {DEFAULT_PREDICTION_MODEL_NAME})."
        ),
    )
    parser.add_argument(
        "-p",
        "--participant",
        default="experiment",
        help="The name of the participant that is taking part in the experiment."
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    os.environ["APP_MODEL_NAME"] = args.model
    os.environ["PARTICIPANT_NAME"] = args.participant
    setup_logging()
    logger.info("Running the experimental environment with model: %s", args.model)

    from app.modules.speller import run_speller

    run_speller.main()
