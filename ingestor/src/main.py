from fastapi.concurrency import asynccontextmanager
import config
from fastapi import FastAPI

from lib.api.client import APIClient
from lib.mqtt.subscriber import MqttSubscriber
from lib.schemas.telemetry import TelemetrySchema
from fermento_schemas.feeding_sample import FeedingSampleCreateSchema
import paho.mqtt.client as mqtt


# ------------------------------------------------------
# API Client Setup
# ------------------------------------------------------
api_client = APIClient(base_url=config.API_ADDRESS)


# ------------------------------------------------------
# MQTT Subscriber Setup
# ------------------------------------------------------
def on_message(topic, payload):
    print(f"Received {topic}: {payload}")
    if mqtt.topic_matches_sub(config.TOPIC_TELEMETRY, topic):
        # Validate pydantic model
        telemetry = TelemetrySchema.model_validate_json(payload)
        # Convert to api schema
        feeding_sample = FeedingSampleCreateSchema(
            feeding_event_id=telemetry.feeding_event_id,
            temperature=telemetry.temperature,
            humidity=telemetry.humidity,
            co2=telemetry.co2,
            distance=telemetry.distance,
        )
        # Send to api
        api_client.create_resource("feeding-sample", feeding_sample.model_dump())
    if mqtt.topic_matches_sub(config.TOPIC_STATUS, topic):
        # Process status data
        pass


subscriber = MqttSubscriber(config.SERVER_ADDRESS, int(config.SERVER_PORT))
subscriber.add_subscribe_topic(config.TOPIC_TELEMETRY)
subscriber.add_on_message_callback(on_message)


# ------------------------------------------------------
# FastAPI Application Setup
# ------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for managing application startup and shutdown events.
    """
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
