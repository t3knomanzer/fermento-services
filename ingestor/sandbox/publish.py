import nt
import paho.mqtt.client as mqtt
import json
from datetime import datetime


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
try:
    client.connect("localhost")
except Exception as e:
    print(f"Could not connect to MQTT broker: {e}")

msg = {
    "schema": "0,1",
    "device_id": "dev01",
    "message_id": "1",
    "timestamp": datetime.now().isoformat(),
    "feeding_event_id": "123",
    "temperature": 22.5,
    "humidity": 45.0,
    "co2": 800,
    "distance": 10.0,
}

client.loop_start()
msg_info = client.publish("fermento/dev01/telemetry", json.dumps(msg), qos=1)
msg_info.wait_for_publish()
print(msg_info.is_published())
client.loop_stop()
client.disconnect()
