import json
from urllib.error import HTTPError
from pydantic_core import ValidationError
import config

from lib.api.client import APIClient
from lib.mqtt.client import MqttSubscriber
from lib.mqtt.utils import topic_matches_sub
import fermento_service_schemas.api as api_schemas

from lib.log import Logger

logger = Logger(__name__)

# ------------------------------------------------------
# API Client Setup
# ------------------------------------------------------
api_client = APIClient(base_url=config.API_ADDRESS)

# ------------------------------------------------------
# Variables
# ------------------------------------------------------
record_buffer = []  # Buffer for incoming feeding samples before processing
common_data = {}  # Dictionary to hold computed metrics to be reused


# ------------------------------------------------------
# MQTT Subscriber Setup
# ------------------------------------------------------
def on_mqtt_message_received(topic, payload):
    # --- Feeding Sample Create ---
    if topic_matches_sub(config.TOPIC_FEEDING_SAMPLES_POSTED, topic):
        logger.debug("Feeding samples posted received...")
        # Retrieve the full sample data from the API (payload is { "id": ... })
        try:
            payload_dict = json.loads(payload)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON payload: {e}")
            return
        try:
            # Get the feeding sample
            sample_data = api_client.get_resource("feeding-sample", payload_dict["id"])
            sample = api_schemas.FeedingSampleSchema(**sample_data)

            # Get the feeding event
            event_data = api_client.get_resource(
                "feeding-event", sample.feeding_event_id
            )
            event = api_schemas.FeedingEventSchema(**event_data)

            # Get the jar
            jar_data = api_client.get_resource("jar", event.jar_id)
            jar = api_schemas.JarSchema(**jar_data)
        except (HTTPError, ValidationError) as e:
            logger.error(f"Failed to retrieve or validate feeding sample: {e}")
            return
        # Add the sample to the buffer.
        common_data.setdefault(
            sample.feeding_event_id,
            {"starting_distance": sample.distance, "jar_height": jar.height},
        )

        # Compute:
        # -- growth_pct
        # (distance - starting_distance) / (starting_distance - jar_height)
        event_data = common_data[sample.feeding_event_id]
        growth_pct = (sample.distance - event_data["starting_distance"]) / (
            event_data["starting_distance"] - event_data["jar_height"]
        )
        logger.info(
            f"Feeding event {sample.feeding_event_id}: growth_pct={growth_pct:.2%}"
        )
        # growth_smoothed
        # temp_smoothed
        # humidity_smoothed
        # co2_smoothed
        # growth_rate
        # acceleration
        # running_max
        # running_min
        # stage_estimate

        schema = api_schemas.FeedingSampleProcessedCreateSchema(
            feeding_sample_id=sample.id,
            timestamp=sample.timestamp,
            temperature=sample.temperature,
            humidity=sample.humidity,
            co2=sample.co2,
            distance=sample.distance,
            growth=growth_pct,
            growth_rate=0.0,  # Placeholder for growth rate calculation
            acceleration=0.0,  # Placeholder for acceleration calculation
            running_max=growth_pct,  # Placeholder for running max calculation
            running_min=growth_pct,  # Placeholder for running min calculation
            stage_estimate="unknown",  # Placeholder for stage estimate calculation
        )


subscriber = MqttSubscriber(config.BROKER_ADDRESS, int(config.BROKER_PORT))
subscriber.add_subscribe_topic(config.TOPIC_FEEDING_SAMPLES_POSTED)
subscriber.add_on_message_callback(on_mqtt_message_received)


def main():
    logger.info("Application starting...")
    subscriber.connect()
    subscriber.loop()  # Blocking call to start the network loop


if __name__ == "__main__":
    main()
