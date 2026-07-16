"""
Central logging configuration for the application.

This module handles diagnostic logging only. Experiment data is recorded separately
through `aac_app.experiment`, so that research data never depends on log formatting.

Usage:
    from aac_app.logging_config import setup_logging
    setup_logging()
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

GENERAL_LOGGING_LEVEL = logging.INFO


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
        "Logging configured (level=%s, file=%s)",
        logging.getLevelName(GENERAL_LOGGING_LEVEL),
        str(file_path),
    )


def get_module_logger(file_name: str, logger_name: str) -> logging.Logger:
    """
    Return a logger writing to its own diagnostic log file.

    :param file_name: Base name of the log file inside the logs directory
    :param logger_name: Name of the logger (usually `__name__`)
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    file_path = get_default_log_path() / f"{file_name}.log"

    # Prevent adding multiple handlers if called multiple times
    if not logger.handlers:
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(GENERAL_LOGGING_LEVEL)

        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger
