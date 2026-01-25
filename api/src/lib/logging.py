#!/usr/bin/env python
"""
Module containing the logger for the application
"""


import logging
from enum import IntEnum
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

from lib.config import Config
from lib.utils.pathing import generate_path


class LogLevel(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class Logger:
    def __init__(self, name: Optional[str] = None) -> None:
        # Get the log level from the config and convert it to the correct int value
        # We set the level in the logging module to the lowest and then control
        # it in the individual handlers. The config value drives the console level,
        # the file level is always set to DEBUG.
        log_level = logging.getLevelNamesMapping()[Config().log_level]

        # Create a file handler to write logs to a file using timed rotation
        file_handler = TimedRotatingFileHandler(
            generate_path("tnm_validation_api.log"),
            when="midnight",
            interval=1,
            backupCount=3,
        )
        file_handler.setLevel(logging.DEBUG)

        # Create a console handler to output logs to the console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s : [%(name)s][%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[file_handler, console_handler],
        )

        self._logger = logging.getLogger(name or "tnm_validation")

    def log(self, level: int, msg: object, **kwargs) -> None:
        self._logger.log(level, msg, **kwargs)

    def info(self, message) -> None:
        self._logger.info(message)

    def warning(self, message) -> None:
        self._logger.warning(message)

    def error(self, message) -> None:
        self._logger.error(message)

    def debug(self, message) -> None:
        self._logger.debug(message)


logger = Logger()
