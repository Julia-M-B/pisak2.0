"""
Central logging configuration for the PISAK application.

Usage:
    from pisak.logging_config import setup_logging
    setup_logging()
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_default_log_path() -> Path:
    file_path = Path.home() / "pisak2.0" / "logs"
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
    file_path = get_default_log_path() / "pisak.log"
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=10**7,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(general_logging_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.getLogger("pisak").info(
        "Logging configured (level=%s, file=%s)", logging.getLevelName(general_logging_level), str(file_path)
    )

def get_module_logger(file_name: str, logger_name: str) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    file_path = get_default_log_path() / f"{file_name}.log"

    # Prevent adding multiple handlers if called multiple times
    if not logger.handlers:
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger

