"""
config.py — Constants and shared configuration.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Fermentation stages
# ---------------------------------------------------------------------------
STAGE_NAMES = {0: "Lag", 1: "Exponential", 2: "Peak", 3: "Decline"}

# ---------------------------------------------------------------------------
# Feature engineering windows (in samples)
# At 1 sample/min: SHORT=5min, MEDIUM=15min, LONG=30min
# ---------------------------------------------------------------------------
SHORT_WIN = 5
MEDIUM_WIN = 15
LONG_WIN = 30

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MODEL_PATH = Path("./models/model.pkl")

API_ADDRESS = os.getenv("API_ADDRESS", "http://13.50.219.203:8091")

BROKER_ADDRESS = os.getenv("BROKER_ADDRESS", "13.50.219.203")
BROKER_PORT = os.getenv("BROKER_PORT", 1883)

TOPIC_FEEDING_SAMPLES_POSTED = "fermento/+/feeding_samples/posted"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
