import paho.mqtt.client as mqtt


def topic_matches_sub(sub: str, topic: str) -> bool:
    """
    Check if a topic matches a subscription, supporting wildcards.

    Args:
        sub (str): The subscription topic, which may include wildcards.
        topic (str): The actual topic to check against the subscription.
    Returns:
        bool: True if the topic matches the subscription, False otherwise.
    """
    return mqtt.topic_matches_sub(sub, topic)
