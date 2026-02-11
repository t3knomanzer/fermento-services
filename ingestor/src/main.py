import json
from urllib.error import HTTPError
from fastapi.concurrency import asynccontextmanager
from pydantic_core import ValidationError
import config
from fastapi import FastAPI

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
    if topic_matches_sub(config.TOPIC_FEEDING_SAMPLES_CREATE, topic):
        logger.debug("Topic found, processing data...")
        # Validate pydantic model
        try:
            feeding_sample_create = api.FeedingSampleCreateSchema.model_validate_json(
                payload
            )
        except ValidationError as e:
            logger.error(f"Error validating feeding sample: {e}")
            return

        # Send to api
        try:
            response = api_client.create_resource(
                "feeding-sample", feeding_sample_create.model_dump()
            )
            logger.info(f"Feeding sample created: {response}")
        except HTTPError as e:
            logger.error(f"Error creating feeding sample: {e}")

    elif topic_matches_sub(config.TOPIC_JARS_CREATE, topic):
        logger.debug("Topic found, processing data...")
        # Process jar creation data
        try:
            jar_create = api.JarCreateSchema.model_validate_json(payload)
        except ValidationError as e:
            logger.error(f"Error validating jar: {e}")
            return

        # Send to api
        try:
            response = api_client.create_resource("jar", jar_create.model_dump())
            logger.info(f"Jar created: {response}")
        except HTTPError as e:
            logger.error(f"Error creating jar: {e}")

    elif topic_matches_sub(config.TOPIC_FEEDING_EVENTS_REQUEST, topic):
        logger.debug("Topic found, processing data...")
        try:
            response = api_client.list_resources("feeding-events/expanded")
        except HTTPError as e:
            logger.error(f"Error listing feeding events: {e}")
            return

        subscriber.publish(config.TOPIC_FEEDING_EVENTS_RECEIVE, json.dumps(response))
        logger.info(f"Feeding events: {response}")
    else:
        logger.warning("Topic not implemented: " + topic)


subscriber = MqttSubscriber(config.BROKER_ADDRESS, int(config.BROKER_PORT))
subscriber.add_subscribe_topic(config.TOPIC_FEEDING_SAMPLES_CREATE)
subscriber.add_subscribe_topic(config.TOPIC_FEEDING_EVENTS_REQUEST)
subscriber.add_subscribe_topic(config.TOPIC_JARS_CREATE)
subscriber.add_on_message_callback(on_mqtt_message_received)


# ------------------------------------------------------
# FastAPI Application Setup
# ------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for managing application startup and shutdown events.
    """
    logger.info("Application starting...")
    subscriber.connect()
    subscriber.start()

    yield

    subscriber.stop()


app = FastAPI(lifespan=lifespan)


# ------------------------------------------------------
# Sample Endpoint
# ------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "Hello World"}
