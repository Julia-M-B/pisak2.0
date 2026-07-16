import argparse
import logging
import os
from typing import Sequence

from aac_app.logging_config import setup_logging
from aac_app.settings import (
    DEFAULT_PREDICTION_MODEL_NAME,
    ScanningSettings,
    configure_scanning,
)

logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    defaults = ScanningSettings()
    parser = argparse.ArgumentParser(description="Run the experimental environment.")
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_PREDICTION_MODEL_NAME,
        help=(
            "Prediction model filename; resolved from the bundled models, the "
            "download cache, or fetched on first use "
            f"(default: {DEFAULT_PREDICTION_MODEL_NAME})."
        ),
    )
    parser.add_argument(
        "--download-models",
        action="store_true",
        help=(
            "Download all model weights into the cache and exit. Use this to "
            "prepare a machine before running the experiment offline."
        ),
    )
    parser.add_argument(
        "-p",
        "--participant",
        default="experiment",
        help="The name of the participant that is taking part in the experiment.",
    )
    scanning = parser.add_argument_group(
        "scanning", "Parameters of the switch-scanning interface."
    )
    scanning.add_argument(
        "--scan-highlight-time",
        type=float,
        default=None,
        metavar="SECONDS",
        help=(
            "How long each item stays highlighted while scanning "
            f"(default: {defaults.highlight_time})."
        ),
    )
    scanning.add_argument(
        "--scan-start-delay",
        type=float,
        default=None,
        metavar="SECONDS",
        help=(
            "Delay before the first highlight when a new scan starts "
            f"(default: {defaults.start_delay})."
        ),
    )
    scanning.add_argument(
        "--scan-loops",
        type=int,
        default=None,
        metavar="N",
        help=(
            "How many times scanning loops over the items before giving up "
            f"(default: {defaults.loop_number})."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    os.environ["APP_MODEL_NAME"] = args.model
    os.environ["PARTICIPANT_NAME"] = args.participant

    # Apply scanning overrides before the UI (and its ScanningManager) is built.
    settings = configure_scanning(
        highlight_time=args.scan_highlight_time,
        start_delay=args.scan_start_delay,
        loop_number=args.scan_loops,
    )

    setup_logging()

    if args.download_models:
        from aac_app.predictions.model_store import prefetch_models

        logger.info("Downloading model weights...")
        prefetch_models()
        return

    logger.info("Running the experimental environment with model: %s", args.model)
    logger.info("Scanning settings: %s", settings)

    from aac_app.modules.speller import run_speller

    run_speller.main()
