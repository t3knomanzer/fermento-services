"""
service.py — MQTT-driven fermentation monitoring service.

Flow:
    MQTT message (record ID) → fetch from DB → dict → SensorReading → monitor → post stage to DB

Integration points (marked with TODO):
    - Plug in your MQTT client in start() where indicated
    - Implement fetch_from_db() to retrieve a sensor reading dict by ID
    - Implement post_to_db() to write the predicted stage back

Usage:
    python service.py
    python service.py --model models/model.pkl
"""

import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError

from pydantic import ValidationError

from config import STAGE_NAMES, MODEL_PATH
import config
from lib.mqtt.utils import topic_matches_sub
from lib.monitor import FermentationMonitor, SensorReading
from lib.mqtt.client import MqttSubscriber
from lib.api.client import APIClient
import fermento_service_schemas.api as api_schemas
from lib.log import Logger


logger = Logger(__name__)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class FermentationService:
    """
    Wires MQTT messages → DB fetch → FermentationMonitor → DB post.
    Call on_message() from your MQTT client's on_message hook.
    """

    def __init__(self, model_path: Path = MODEL_PATH):
        self.monitor = FermentationMonitor(model_path=model_path, silent=True)
        self.api_client = APIClient(base_url=config.API_ADDRESS)

        self.mqtt_client = MqttSubscriber(
            config.BROKER_ADDRESS, int(config.BROKER_PORT)
        )
        self.mqtt_client.add_subscribe_topic(config.TOPIC_FEEDING_SAMPLES_POSTED)
        self.mqtt_client.add_on_message_callback(self.on_message_received)

        self._last_stage: Optional[int] = None

    def start(self):
        logger.info("Starting MQTT client loop...")
        self.mqtt_client.connect()
        self.mqtt_client.loop()  # Blocking call to start the network loop

    def retrieve_record(
        self,
        feeding_sample_id: int,
    ) -> api_schemas.FeedingSampleSchema | None:
        try:
            # Get the feeding sample
            sample_data = self.api_client.get_resource(
                "feeding-sample", feeding_sample_id
            )
            sample = api_schemas.FeedingSampleSchema(**sample_data)
        except (HTTPError, ValidationError) as e:
            logger.error(f"Failed to retrieve or validate feeding sample: {e}")
            return None
        return sample

    def convert_sample_to_reading(
        self, sample: api_schemas.FeedingSampleSchema
    ) -> SensorReading:
        try:
            reading = SensorReading(
                timestamp=sample.timestamp,
                temperature=sample.temperature,
                co2=sample.co2,
                distance=sample.distance,
                humidity=sample.humidity,
            )
        except ValidationError as e:
            logger.error(f"Failed to convert sample to SensorReading: {e}")
            raise
        return reading

    def on_message_received(self, topic: str, payload: str) -> None:
        if topic_matches_sub(config.TOPIC_FEEDING_SAMPLES_POSTED, topic):
            logger.debug("Feeding samples posted received...")

            # Payload to dict.
            try:
                payload_dict = json.loads(payload)
                record_id = int(payload_dict["id"])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON payload: {e}")
                return

            record = self.retrieve_record(record_id)
            if record is None:
                logger.error(f"Failed to fetch record {record_id} from DB")
                return

            reading = self.convert_sample_to_reading(record)
            stage = self.monitor.update(reading)

            if stage != self._last_stage:
                if self._last_stage is not None:
                    logger.info("=" * 40)
                    logger.info(
                        f"🍞 Stage transition: {STAGE_NAMES.get(self._last_stage, '?')} → {STAGE_NAMES.get(stage, '?')}"
                    )
                    logger.info("=" * 40)
                self._last_stage = stage


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def start(model_path: Path = MODEL_PATH) -> None:
    service = FermentationService(model_path=model_path)
    service.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fermentation monitoring service")
    parser.add_argument(
        "--model",
        type=Path,
        default=MODEL_PATH,
        help=f"Path to trained model (default: {MODEL_PATH})",
    )
    args = parser.parse_args()
    start(model_path=args.model)
