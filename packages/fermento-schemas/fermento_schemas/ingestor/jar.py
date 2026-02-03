from pydantic import BaseModel


class JarSchema(BaseModel):
    """
    Schema for jar data validation.
    """

    schema: tuple[int, int, int]
    device_id: str
    message_id: str
    timestamp: str
    name: str
    distance: float
