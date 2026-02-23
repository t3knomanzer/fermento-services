from collections import deque
import json
from urllib.error import HTTPError
from pydantic_core import ValidationError

import config

from lib.api.client import APIClient
from lib.computation.derivative import DerivativeComputation
from lib.filtering.ema import EMAFilter
from lib.mqtt.client import MqttSubscriber
from lib.mqtt.utils import topic_matches_sub
import fermento_service_schemas.api as api_schemas

from lib.log import Logger
from lib.schemas.sample_buffer_schema import SampleBufferSchema

logger = Logger(__name__)
api_client = APIClient(base_url=config.API_ADDRESS)

# ------------------------------------------------------
# Variables
# ------------------------------------------------------
common_data = {}
raw_buffer: deque[SampleBufferSchema] = deque(maxlen=5)

growth_rate_derivative = DerivativeComputation(window_size=5)
acceleration_derivative = DerivativeComputation(window_size=5)

growth_ema_01 = EMAFilter(alpha=0.1)
growth_ema_02 = EMAFilter(alpha=0.1)
temperature_ema_01 = EMAFilter(alpha=0.2)
humidity_ema_01 = EMAFilter(alpha=0.1)
humidity_ema_02 = EMAFilter(alpha=0.1)
co2_ema_01 = EMAFilter(alpha=0.2)
growth_rate_ema_01 = EMAFilter(alpha=0.1)
growth_rate_ema_02 = EMAFilter(alpha=0.1)
acceleration_ema_01 = EMAFilter(alpha=0.2)
acceleration_ema_02 = EMAFilter(alpha=0.2)


# ------------------------------------------------------
# Functions
# ------------------------------------------------------
# TODO: Implement read-expanded in the api to replace this function.
def retrieve_feeding_sample(
    feeding_sample_id: int,
) -> api_schemas.FeedingSampleSchema | None:
    try:
        # Get the feeding sample
        sample_data = api_client.get_resource("feeding-sample", feeding_sample_id)
        sample = api_schemas.FeedingSampleSchema(**sample_data)
    except (HTTPError, ValidationError) as e:
        logger.error(f"Failed to retrieve or validate feeding sample: {e}")
        return None
    return sample


def retrieve_feeding_event(
    feeding_event_id: int,
) -> api_schemas.FeedingEventSchema | None:
    try:
        # Get the feeding event
        event_data = api_client.get_resource("feeding-event", feeding_event_id)
        event = api_schemas.FeedingEventSchema(**event_data)
    except (HTTPError, ValidationError) as e:
        logger.error(f"Failed to retrieve or validate feeding event: {e}")
        return None
    return event


def retrieve_jar(jar_id: int) -> api_schemas.JarSchema | None:
    try:
        # Get the jar
        jar_data = api_client.get_resource("jar", jar_id)
        jar = api_schemas.JarSchema(**jar_data)
    except (HTTPError, ValidationError) as e:
        logger.error(f"Failed to retrieve or validate jar: {e}")
        return None
    return jar


def retrieve_schemas(
    feeding_sample_id: int,
) -> tuple[
    api_schemas.FeedingSampleSchema | None,
    api_schemas.FeedingEventSchema | None,
    api_schemas.JarSchema | None,
]:
    sample = retrieve_feeding_sample(feeding_sample_id)
    if sample is None:
        return None, None, None
    event = retrieve_feeding_event(sample.feeding_event_id)
    if event is None:
        return sample, None, None
    jar = retrieve_jar(event.jar_id)
    if jar is None:
        return sample, event, None
    return sample, event, jar


def compute_growth(
    distance: float, starting_distance: float, jar_height: float
) -> float:
    # Compute growth percentage based on the formula:
    # growth_pct = (distance - starting_distance) / (starting_distance - jar_height)
    if starting_distance == jar_height:
        logger.warning(
            "Starting distance is equal to jar height, cannot compute growth."
        )
        return 0.0
    result = (distance - starting_distance) / (starting_distance - jar_height)
    return result


# ------------------------------------------------------
# MQTT Subscriber Setup
# ------------------------------------------------------
def on_mqtt_message_received(topic, payload):
    # --- Feeding Sample Create ---
    if topic_matches_sub(config.TOPIC_FEEDING_SAMPLES_POSTED, topic):
        logger.debug("Feeding samples posted received...")

        # Payload to dict.
        try:
            payload_dict = json.loads(payload)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON payload: {e}")
            return

        # Retrieve data from API.
        sample, event_data, jar = retrieve_schemas(payload_dict.get("id"))
        if not sample or not event_data or not jar:
            logger.error("Failed to retrieve all necessary schemas for processing.")
            return

        # TODO: Starting distance retrieval should be moved to the API.
        # Store common data for the feeding events.
        common_data.setdefault(
            sample.feeding_event_id,
            {"starting_distance": sample.distance, "jar_height": jar.height},
        )

        # --------------------------------------
        # ----------- Growth Raw
        # --------------------------------------
        # We compute the growth from the distance and use this metric from here on.
        event_data = common_data[sample.feeding_event_id]
        growth_raw = compute_growth(
            sample.distance, event_data["starting_distance"], event_data["jar_height"]
        )
        logger.info(f"Growth={growth_raw:.2%}")

        # Add the sample to the buffer.
        raw_item = SampleBufferSchema(
            growth=growth_raw,
            temperature=sample.temperature,
            humidity=sample.humidity,
            co2=sample.co2,
            timestamp=sample.timestamp,
        )
        raw_buffer.append(raw_item)

        # --------------------------------------
        # ----------- Growth Smoothed
        # --------------------------------------
        growth = growth_ema_01.update(growth_raw)
        growth = growth_ema_01.update(growth)
        logger.info(f"Growth smoothed={growth:.2%}")

        # --------------------------------------
        # ----------- Temperature Smoothed
        # --------------------------------------
        # temperature_smoothed = median_filter([s.temperature for s in sample_buffer])
        temperature = temperature_ema_01.update(raw_item.temperature)
        logger.info(f"Temperature smoothed={temperature:.2f}")

        # --------------------------------------
        # ----------- Humidity Smoothed
        # --------------------------------------
        # humidity_smoothed = median_filter([s.humidity for s in sample_buffer])
        humidity = humidity_ema_01.update(raw_item.humidity)
        logger.info(f"Humidity smoothed={humidity:.2f}")

        # --------------------------------------
        # ----------- CO2 Smoothed
        # --------------------------------------
        # co2_smoothed = median_filter([s.co2 for s in sample_buffer])
        co2 = co2_ema_01.update(raw_item.co2)
        logger.info(f"CO2 smoothed={co2:.2f}")

        # --------------------------------------
        # ----------- Growth rate
        # --------------------------------------
        growth_rate = growth_rate_derivative.update(growth, raw_item.timestamp)
        growth_rate = growth_rate_ema_01.update(growth_rate)
        logger.info(f"Growth rate={growth_rate:.4f} per minute")

        # --------------------------------------
        # ----------- Acceleration
        # --------------------------------------
        acceleration = acceleration_derivative.update(growth_rate, raw_item.timestamp)
        acceleration = acceleration_ema_01.update(acceleration)
        acceleration = acceleration_ema_02.update(acceleration)

        logger.info(f"Acceleration={acceleration:.4f} per minute^2")

        # --------------------------------------
        # ----------- Stage estimate
        # --------------------------------------
        stage_estimate = "unknown"  # Placeholder for stage estimate calculation
        logger.info(f"Stage estimate={stage_estimate}")

        schema = api_schemas.FeedingSampleProcessedCreateSchema(
            feeding_sample_id=sample.id,
            growth=growth,
            temperature=temperature,
            humidity=humidity,
            co2=co2,
            growth_rate=growth_rate,
            acceleration=acceleration,
            stage_estimate=stage_estimate,
        )
        try:
            api_client.create_resource("feeding-sample-processed", schema.model_dump())
        except HTTPError as e:
            logger.error(f"Failed to create feeding sample processed: {e}")


subscriber = MqttSubscriber(config.BROKER_ADDRESS, int(config.BROKER_PORT))
subscriber.add_subscribe_topic(config.TOPIC_FEEDING_SAMPLES_POSTED)
subscriber.add_on_message_callback(on_mqtt_message_received)


def main():
    logger.info("Application starting...")
    subscriber.connect()
    subscriber.loop()  # Blocking call to start the network loop


if __name__ == "__main__":
    main()
