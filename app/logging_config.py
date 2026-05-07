"""
Central logging configuration for the PISAK application.

Usage:
    from pisak.logging_config import setup_logging
    setup_logging()
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
import csv

GENERAL_LOGGING_LEVEL = logging.INFO
EXPERIMENT_LOGGING_LEVEL = logging.DEBUG


class DebugOnlyFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == logging.DEBUG

def get_default_log_path(is_experiment: bool = False) -> Path:
    if is_experiment:
        file_path = Path.home() / "aac_app" / "experiment"
    else:
        file_path = Path.home() / "aac_app" / "logs"
    file_path.mkdir(parents=True, exist_ok=True)
    return file_path

def setup_logging():
    """
    Configure application logging (console + rotating file).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(GENERAL_LOGGING_LEVEL)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    file_path = get_default_log_path() / "aac_app.log"
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=10**7,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(GENERAL_LOGGING_LEVEL)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.getLogger("aac_app").info(
        "Logging configured (level=%s, file=%s)", logging.getLevelName(GENERAL_LOGGING_LEVEL), str(file_path)
    )

def get_module_logger(file_name: str, logger_name: str, experiment: bool = False) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    file_path = get_default_log_path() / f"{file_name}.log"

    # Prevent adding multiple handlers if called multiple times
    if not logger.handlers:
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(GENERAL_LOGGING_LEVEL)

        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            # datefmt="%Y-%m-%d %H:%M:%S:%f",
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        if experiment:
            experiment_name = os.getenv("PARTICIPANT_NAME", "experiment").lower()
            experiment_time = str(datetime.now().strftime("%Y-%m-%d_%H-%M"))
            experiment_file_path = get_default_log_path(is_experiment=True) / f"{experiment_name}_{experiment_time}.csv"

            csv_header = ["Date", "Time", "Level", "Module", "Action", "Type", "Text", "Additional information"]
            if (not experiment_file_path.exists()) or experiment_file_path.stat().st_size == 0:
                with open(experiment_file_path, "w", newline="", encoding="utf-8") as csv_log:
                    csv_writer = csv.writer(csv_log)
                    csv_writer.writerow(csv_header)

            experiment_handler = logging.FileHandler(experiment_file_path, encoding="utf-8")
            experiment_handler.setLevel(EXPERIMENT_LOGGING_LEVEL)

            csv_formatter = logging.Formatter(
                fmt="%(asctime)s.%(msecs)03d,%(levelname)s,%(name)s,%(message)s",
                datefmt="%Y.%m.%d,%H:%M:%S"
            )

            experiment_filter = DebugOnlyFilter()

            experiment_handler.setFormatter(csv_formatter)
            experiment_handler.addFilter(experiment_filter)

            logger.addHandler(experiment_handler)

    return logger

