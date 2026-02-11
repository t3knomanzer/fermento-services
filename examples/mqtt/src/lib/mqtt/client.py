import paho.mqtt.client as mqtt


class MqttSubscriber:
    def __init__(self, server_address: str = "localhost", server_port: int = 1883):
        self._server_address = server_address
        self._server_port = int(server_port)

        self._on_message_callbacks = []
        self._subscribe_topics = []

        self._connected = False
        self._loop_running = False

        # Paho v2 callback API
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self.on_connect
        self._client.on_message = self.on_message
        self._client.on_disconnect = self.on_disconnect

        # Reasonable reconnect behavior (seconds)
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

    # --- Public API ---------------------------------------------------------

    def add_on_message_callback(self, callback):
        print(
            "MQTT", "MqttSubscriber", "DEBUG", f"Adding on_message callback: {callback}"
        )
        self._on_message_callbacks.append(callback)

    def add_subscribe_topic(self, topic: str):
        print("MQTT", "MqttSubscriber", "DEBUG", f"Adding subscribe topic: {topic}")
        if topic not in self._subscribe_topics:
            self._subscribe_topics.append(topic)
            # If already connected, subscribe immediately
            if self._connected:
                self._client.subscribe(topic)

    def remove_on_message_callback(self, callback):
        print(
            "MQTT",
            "MqttSubscriber",
            "DEBUG",
            f"Removing on_message callback: {callback}",
        )
        self._on_message_callbacks.remove(callback)

    def remove_subscribe_topic(self, topic: str):
        print("MQTT", "MqttSubscriber", "DEBUG", f"Removing subscribe topic: {topic}")
        if topic in self._subscribe_topics:
            self._subscribe_topics.remove(topic)
            if self._connected:
                try:
                    self._client.unsubscribe(topic)
                except Exception:
                    pass

    def connect(self, keepalive: int = 60):
        """
        Connect to the broker (non-blocking).
        Call start() to begin the network loop.
        """
        print(
            "MQTT",
            "MqttSubscriber",
            "INFO",
            f"Connecting to MQTT broker at {self._server_address}:{self._server_port}...",
        )
        try:
            self._client.connect(self._server_address, self._server_port, keepalive)
        except ConnectionRefusedError as e:
            print("MQTT", "MqttSubscriber", "ERROR", f"MQTT connection refused: {e}")
        except OSError as e:
            print("MQTT", "MqttSubscriber", "ERROR", f"MQTT connection error: {e}")

    def start(self):
        """
        Start Paho's network loop in a background thread.
        Safe to call from FastAPI startup.
        """
        if self._loop_running:
            return
        self._loop_running = True
        self._client.loop_start()

    def start_standalone(self):
        """
        Convenience method for running the subscriber in a standalone mode.
        Connects and starts the loop, then blocks indefinitely.
        """
        self.connect()
        self._client.loop_forever()

    def stop(self):
        """
        Stop the network loop and disconnect cleanly.
        Safe to call from FastAPI shutdown.
        """
        try:
            self._client.disconnect()
        except Exception:
            pass

        if self._loop_running:
            self._client.loop_stop()
            self._loop_running = False

    def publish(
        self, topic: str, payload: bytes | str, qos: int = 0, retain: bool = False
    ):
        """
        Convenience publish method (useful for retained cache topics).
        """
        print("MQTT", "MqttSubscriber", "DEBUG", f"Publishing to {topic}: {payload}")
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        return self._client.publish(topic, payload=payload, qos=qos, retain=retain)

    # --- Paho callbacks -----------------------------------------------------

    def on_connect(self, client, userdata, flags, reason_code, properties):
        self._connected = True
        print(
            "MQTT",
            "MqttSubscriber",
            "INFO",
            f"MQTT Connected with result code {reason_code}",
        )

        # Re-subscribe on reconnect
        for topic in self._subscribe_topics:
            client.subscribe(topic)

    def on_disconnect(self, client, userdata, reason_code, properties, *args, **kwargs):
        self._connected = False
        print(
            "MQTT",
            "MqttSubscriber",
            "INFO",
            f"MQTT Disconnected with reason code {reason_code}",
        )

    def on_message(self, client, userdata, msg):
        if self._on_message_callbacks:
            for callback in self._on_message_callbacks:
                try:
                    callback(msg.topic, msg.payload)
                except Exception as e:
                    print(
                        "MQTT",
                        "MqttSubscriber",
                        "ERROR",
                        f"on_message callback error: {e}",
                    )
        else:
            print(
                "MQTT",
                "MqttSubscriber",
                "WARNING",
                "No on_message callbacks registered.",
            )
