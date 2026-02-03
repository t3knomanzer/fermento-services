import os


API_ADDRESS = os.getenv("API_ADDRESS", "http://localhost:8091")

BROKER_ADDRESS = os.getenv("BROKER_ADDRESS", "192.168.8.5")
BROKER_PORT = os.getenv("BROKER_PORT", 1883)

TOPIC_TELEMETRY = "fermento/+/telemetry"
TOPIC_STATUS = "fermento/+/status"
SUBSCRIBE_TOPICS = [TOPIC_TELEMETRY, TOPIC_STATUS]
