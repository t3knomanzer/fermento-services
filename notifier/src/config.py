"""
config.py — Constants and shared configuration.
"""

import os
from pathlib import Path

BROKER_ADDRESS = os.getenv("BROKER_ADDRESS", "13.50.219.203")
BROKER_PORT = int(os.getenv("BROKER_PORT", "1883"))

TOPIC_STAGE_TRANSITION = "fermento/stage_transition/"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

PHONE_NUMBER = os.getenv("PHONE_NUMBER", "+1234567890")
