import os

API_ADDRESS = os.getenv("API_ADDRESS", "http://13.50.219.203:8091")

BROKER_ADDRESS = os.getenv("BROKER_ADDRESS", "13.50.219.203")
BROKER_PORT = os.getenv("BROKER_PORT", 1883)

TOPIC_FEEDING_SAMPLES_POSTED = "fermento/+/feeding_samples/posted"

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
