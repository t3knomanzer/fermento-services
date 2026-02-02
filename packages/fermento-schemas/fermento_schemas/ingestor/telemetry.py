from pydantic import BaseModel


class TelemetrySchema(BaseModel):
    """
    Schema for telemetry data validation.
    """

    schema: str
    device_id: str
    message_id: str
    timestamp: str
    feeding_event_id: int
    temperature: float
    humidity: float
    co2: float
    distance: float
