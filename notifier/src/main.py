import dotenv

dotenv.load_dotenv()

from lib.mqtt.client import MqttSubscriber
import config

import boto3
import json


def send_sms(phone_number: str, message: str):
    # Placeholder for SMS sending logic
    print(f"Sending SMS to {phone_number}: {message}")
    sns = boto3.client("sns")
    sns.publish(
        PhoneNumber=phone_number,
        Message=message,
        MessageAttributes={
            "AWS.SNS.SMS.SenderID": {"DataType": "String", "StringValue": "Fermento"},
            "AWS.SNS.SMS.SMSType": {
                "DataType": "String",
                "StringValue": "Transactional",  # or "Promotional"
            },
        },
    )


def on_mqtt_message(topic: str, payload: bytes):
    print(f"Received message on topic '{topic}': {payload.decode('utf-8')}")
    data = json.loads(payload.decode())
    message = f"Fermentation stage transition: \
                \n{data["previous_stage"]} -> {data["stage"]}"
    send_sms(config.PHONE_NUMBER, message)


def main():
    mqtt_subscriber = MqttSubscriber(
        server_address=config.BROKER_ADDRESS, server_port=config.BROKER_PORT
    )
    mqtt_subscriber.connect()
    mqtt_subscriber.add_subscribe_topic(config.TOPIC_STAGE_TRANSITION)
    mqtt_subscriber.add_on_message_callback(on_mqtt_message)
    mqtt_subscriber.loop()


if __name__ == "__main__":
    main()
