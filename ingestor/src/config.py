import os

API_ADDRESS = os.getenv("API_ADDRESS", "http://localhost:8091")

BROKER_ADDRESS = os.getenv("BROKER_ADDRESS", "13.50.219.203")
BROKER_PORT = os.getenv("BROKER_PORT", 1883)

TOPIC_FEEDING_SAMPLES_CREATE = "fermento/+/feeding_samples/create"
TOPIC_FEEDING_SAMPLES_IMAGE = "fermento/+/feeding_samples/image/+"  # + for bundle_id
TOPIC_JARS_CREATE = "fermento/+/jars/create"
TOPIC_FEEDING_EVENTS_REQUEST = "fermento/+/feeding_events/request"
TOPIC_FEEDING_EVENTS_RECEIVE = "fermento/feeding_events/receive"

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
