import json
from urllib.error import HTTPError
from fastapi.concurrency import asynccontextmanager
import config
from fastapi import FastAPI

from lib.api.client import APIClient
from lib.mqtt.client import MqttSubscriber
from lib.mqtt.utils import topic_matches_sub
import fermento_embedded_schemas as mcu
import fermento_service_schemas.api as api

# ------------------------------------------------------
# API Client Setup
# ------------------------------------------------------
api_client = APIClient(base_url=config.API_ADDRESS)


# ------------------------------------------------------
# MQTT Subscriber Setup
# ------------------------------------------------------
def on_message(topic, payload):
    print(f"Received {topic}: {payload}")

    if topic_matches_sub(config.TOPIC_FEEDING_SAMPLES_CREATE, topic):
        print("Topic found, processing data...")
        # Validate pydantic model
        feeding_sample = api.FeedingSampleCreateSchema.model_validate_json(payload)

        # Convert to api schema
        feeding_sample_create = api.FeedingSampleCreateSchema(
            feeding_event_id=feeding_sample.feeding_event_id,
            temperature=feeding_sample.temperature,
            humidity=feeding_sample.humidity,
            co2=feeding_sample.co2,
            distance=feeding_sample.distance,
        )

        # Send to api
        try:
            response = api_client.create_resource(
                "feeding-sample", feeding_sample_create.model_dump()
            )
            print(f"Feeding sample created: {response}")
        except HTTPError as e:
            print(f"Error creating feeding sample: {e}")

    elif topic_matches_sub(config.TOPIC_JARS_CREATE, topic):
        print("Topic found, processing data...")
        # Process jar creation data
        jar = api.JarCreateSchema.model_validate_json(payload)

        jar_create = api.JarCreateSchema(
            name=jar.name,
            height=int(jar.height),
        )

        # Send to api
        try:
            response = api_client.create_resource("jar", jar_create.model_dump())
            print(f"Jar created: {response}")
        except HTTPError as e:
            print(f"Error creating jar: {e}")

    elif topic_matches_sub(config.TOPIC_FEEDING_EVENTS_REQUEST, topic):
        print("Topic found, processing data...")
        try:
            response = api_client.list_resources("feeding-events")
        except HTTPError as e:
            print(f"Error listing feeding events: {e}")
            return

        subscriber.publish(config.TOPIC_FEEDING_EVENTS_RECEIVE, json.dumps(response))
        print(f"Feeding events: {response}")
    else:
        print("Topic not implemented: " + topic)


subscriber = MqttSubscriber(config.BROKER_ADDRESS, int(config.BROKER_PORT))
subscriber.add_subscribe_topic(config.TOPIC_FEEDING_SAMPLES_CREATE)
subscriber.add_subscribe_topic(config.TOPIC_FEEDING_EVENTS_REQUEST)
subscriber.add_subscribe_topic(config.TOPIC_JARS_CREATE)
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
