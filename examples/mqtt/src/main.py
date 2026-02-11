from lib.mqtt.client import MqttSubscriber
from lib.mqtt.utils import topic_matches_sub
import pathlib

BROKER_ADDRESS = "192.168.8.5"
BROKER_PORT = 1883
TOPIC = "fermento/+/image"

counter = 0
frames_path = pathlib.Path("./frames")
frames_path.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------
# MQTT Subscriber Setup
# ------------------------------------------------------
def on_mqtt_message_received(topic, payload):
    global counter

    print(f"Received MQTT message on topic: {topic}")
    # Save to a file
    try:
        output_file = frames_path / f"frame_{counter:04d}.jpg"
        with open(output_file, "wb") as f:
            f.write(payload)  # convert memoryview to bytes
    except Exception as e:
        print(f"Error saving MQTT payload to file: {e}")
        return

    counter += 1


def main():
    print("Starting MQTT subscriber...")
    subscriber = MqttSubscriber(BROKER_ADDRESS, int(BROKER_PORT))
    subscriber.add_subscribe_topic(TOPIC)
    subscriber.add_on_message_callback(on_mqtt_message_received)
    subscriber.start_standalone()


main()
