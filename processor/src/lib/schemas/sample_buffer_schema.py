from datetime import datetime

from pydantic import BaseModel


class SampleBufferSchema(BaseModel):
    growth: float
    temperature: float
    humidity: float
    co2: float
    timestamp: datetime
    growth_rate: float = 0.0
