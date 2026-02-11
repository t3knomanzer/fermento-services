#!/usr/bin/env python
"""
Module containing the logger for the application
"""


import logging
from enum import IntEnum
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

import config


class LogLevel(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class Logger:
    def __init__(self, name: Optional[str] = "generic") -> None:
        # Get the log level from the config and convert it to the correct int value
        # We set the level in the logging module to the lowest and then control
        # it in the individual handlers. The config value drives the console level,
        # the file level is always set to DEBUG.
        log_level = logging.getLevelNamesMapping()[config.LOG_LEVEL]

        # Create a console handler to output logs to the console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[console_handler],
        )

        self._logger = logging.getLogger(name)

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
