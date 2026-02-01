#!/usr/bin/env python
"""
Schemas module for starter data validation and serialization.
"""


from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class FeedingSampleSchema(BaseModel):
    """
    Schema for feeding data retrieval.
    """

    id: int
    feeding_id: int
    temperature: float
    humidity: float
    co2: float
    distance: float


class FeedingSampleCreateSchema(BaseModel):
    """
    Schema for creating a new feeding.
    """

    feeding_id: int
    temperature: float
    humidity: float
    co2: float
    distance: float


class FeedingSampleUpdateSchema(BaseModel):
    """
    Schema for updating existing feeding data.
    """

    feeding_id: Optional[int] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    co2: Optional[float] = None
    distance: Optional[float] = None
