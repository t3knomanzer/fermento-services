from fermento_embedded_schemas.base import BaseSchema


class JarSchema(BaseSchema):
    """
    Schema for jar data validation.
    """

    schema: tuple[int, int, int]
    device_id: str
    message_id: str
    timestamp: str
    name: str
    distance: float

    @classmethod
    def _get_fields(cls) -> list[str]:
        return [
            "schema",
            "device_id",
            "message_id",
            "timestamp",
            "name",
            "distance",
        ]
