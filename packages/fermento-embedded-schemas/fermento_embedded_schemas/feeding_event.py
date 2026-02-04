from datetime import datetime
from fermento_embedded_schemas.base import BaseSchema


class FeedingEventSchema(BaseSchema):
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

    @classmethod
    def _get_fields(cls) -> list[str]:
        return [
            "schema",
            "device_id",
            "message_id",
            "timestamp",
            "date",
            "starter_id",
            "starter_ratio",
            "water_ratio",
            "flour_ratio",
            "flour_blend_id",
            "jar_id",
        ]
