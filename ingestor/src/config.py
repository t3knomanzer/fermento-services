import os


API_ADDRESS = os.getenv("API_ADDRESS", "http://localhost:8091")

SERVER_ADDRESS = os.getenv("SERVER_ADDRESS", "localhost")
SERVER_PORT = os.getenv("SERVER_PORT", 1883)

TOPIC_TELEMETRY = "fermento/+/telemetry"
TOPIC_STATUS = "fermento/+/status"
SUBSCRIBE_TOPICS = os.getenv("SERVER_ADDRESS", [TOPIC_TELEMETRY, TOPIC_STATUS])
