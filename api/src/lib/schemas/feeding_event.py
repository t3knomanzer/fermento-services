#!/usr/bin/env python
"""
Schemas module for starter data validation and serialization.
"""


from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class FeedingEventSchema(BaseModel):
    """
    Schema for feeding data retrieval.
    """

    id: int
    date: datetime
    starter_id: int
    starter_ratio: float
    water_ratio: float
    flour_ratio: float
    flour_blend_id: int
    jar_id: int


class FeedingEventCreateSchema(BaseModel):
    """
    Schema for creating a new feeding.
    """

    date: datetime
    starter_id: int
    starter_ratio: float
    water_ratio: float
    flour_ratio: float
    flour_blend_id: int
    jar_id: int


class FeedingEventUpdateSchema(BaseModel):
    """
    Schema for updating existing feeding data.
    """

    date: Optional[datetime] = None
    starter_id: Optional[int] = None
    starter_ratio: Optional[float] = None
    water_ratio: Optional[float] = None
    flour_ratio: Optional[float] = None
    flour_blend_id: Optional[int] = None
    jar_id: Optional[int] = None
