import json
from urllib.error import HTTPError
from pydantic_core import ValidationError
import config

from lib.api.client import APIClient
from lib.mqtt.client import MqttSubscriber
from lib.mqtt.utils import topic_matches_sub
import fermento_service_schemas.api as api

from lib.log import Logger

logger = Logger(__name__)

# ------------------------------------------------------
# API Client Setup
# ------------------------------------------------------
api_client = APIClient(base_url=config.API_ADDRESS)


# ------------------------------------------------------
# MQTT Subscriber Setup
# ------------------------------------------------------
def on_mqtt_message_received(topic, payload):
    # --- Feeding Sample Create ---
    if topic_matches_sub(config.TOPIC_FEEDING_SAMPLES_POSTED, topic):
        logger.debug("Feeding samples posted received...")
        # Retrieve the full sample data from the API (payload is { "id": ... })
        # Process the sample. This is just for the online features, not offline processing.
        # Submit the processed data back to the API:
        # growth_pct
        # growth_smoothed
        # temp_smoothed
        # humidity_smoothed
        # co2_smoothed
        # growth_rate
        # acceleration
        # running_max
        # running_min
        # stage_estimate


subscriber = MqttSubscriber(config.BROKER_ADDRESS, int(config.BROKER_PORT))
subscriber.add_subscribe_topic(config.TOPIC_FEEDING_SAMPLES_POSTED)
subscriber.add_on_message_callback(on_mqtt_message_received)


def main():
    logger.info("Application starting...")
    subscriber.connect()
    subscriber.loop()  # Blocking call to start the network loop


if __name__ == "__main__":
    main()
