import nt
from time import sleep
import paho.mqtt.client as mqtt
import json
from datetime import datetime


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
try:
    client.connect("13.50.219.203", 1883, 60)
except Exception as e:
    print(f"Could not connect to MQTT broker: {e}")

client.loop_start()

for i in range(4277, 4617):
    msg = {"id": i}
    msg_info = client.publish(
        "fermento/x/feeding_samples/posted", json.dumps(msg), qos=0
    )
    msg_info.wait_for_publish()
    print(f"Published message {i}")
    sleep(1)

client.loop_stop()
client.disconnect()
