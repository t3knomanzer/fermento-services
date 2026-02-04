import os

API_ADDRESS = os.getenv("API_ADDRESS", "http://192.168.8.5:8091")

BROKER_ADDRESS = os.getenv("BROKER_ADDRESS", "192.168.8.5")
BROKER_PORT = os.getenv("BROKER_PORT", 1883)

TOPIC_FEEDING_SAMPLES_CREATE = "fermento/+/feeding_samples/create"
TOPIC_JARS_CREATE = "fermento/+/jars/create"
TOPIC_FEEDING_EVENTS_REQUEST = "fermento/+/feeding_events/request"
TOPIC_FEEDING_EVENTS_RECEIVE = "fermento/feeding_events/receive"
