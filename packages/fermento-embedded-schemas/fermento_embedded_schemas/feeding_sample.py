from fermento_embedded_schemas.base import BaseSchema


class FeedingSampleSchema(BaseSchema):
    """
    Schema for telemetry data validation.
    """

    schema: tuple[int, int, int]
    device_id: str
    message_id: str
    timestamp: str
    feeding_event_id: int
    temperature: float
    humidity: float
    co2: float
    distance: float

    @classmethod
    def _get_fields(cls) -> list[str]:
        return [
            "schema",
            "device_id",
            "message_id",
            "timestamp",
            "feeding_event_id",
            "temperature",
            "humidity",
            "co2",
            "distance",
        ]
