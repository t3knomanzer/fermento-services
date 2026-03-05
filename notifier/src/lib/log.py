#!/usr/bin/env python
"""
Module containing the logger for the application.
"""

import logging
from typing import Optional

import config

# ---------------------------------------------------------------------------
# Configure logging once at import time
# ---------------------------------------------------------------------------
_log_level = logging.getLevelNamesMapping()[config.LOG_LEVEL]

_console_handler = logging.StreamHandler()
_console_handler.setLevel(_log_level)

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[_console_handler],
)


# ---------------------------------------------------------------------------
# Logger wrapper
# ---------------------------------------------------------------------------

class Logger:
    def __init__(self, name: Optional[str] = "generic") -> None:
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
