from datetime import datetime
from pydantic import BaseModel


class FeedingEventSchema(BaseModel):
    """
    Schema for telemetry data validation.
    """

    schema: tuple[int, int, int]
    device_id: str
    message_id: str
    timestamp: str
    date: datetime
    starter_id: int
    starter_ratio: float
    water_ratio: float
    flour_ratio: float
    flour_blend_id: int
    jar_id: int
