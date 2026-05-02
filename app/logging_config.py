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


def get_default_log_path() -> Path:
    file_path = Path.home() / "aac_app" / "logs"
    file_path.mkdir(parents=True, exist_ok=True)
    return file_path

def setup_logging():
    """
    Configure application logging (console + rotating file).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    general_logging_level = logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(general_logging_level)
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
    file_handler.setLevel(general_logging_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.getLogger("aac_app").info(
        "Logging configured (level=%s, file=%s)", logging.getLevelName(general_logging_level), str(file_path)
    )

def get_module_logger(file_name: str, logger_name: str, experiment: bool = False) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    file_path = get_default_log_path() / f"{file_name}.log"

    # Prevent adding multiple handlers if called multiple times
    if not logger.handlers:
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            # datefmt="%Y-%m-%d %H:%M:%S:%f",
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        if experiment:
            experiment_name = os.getenv("PARTICIPANT_NAME", "experiment").lower()
            experiment_time = str(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
            experiment_file_path = get_default_log_path() / f"{experiment_name}_{experiment_time}.log"
            experiment_handler = logging.FileHandler(experiment_file_path)
            experiment_handler.setLevel(logging.DEBUG)
            experiment_handler.setFormatter(formatter)

            logger.addHandler(experiment_handler)

    return logger

