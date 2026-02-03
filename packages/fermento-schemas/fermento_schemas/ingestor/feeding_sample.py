from pydantic import BaseModel


class FeedingSampleSchema(BaseModel):
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
