#!/usr/bin/env python
"""
Schemas module for flour blend data validation and serialization.
"""


from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class FlourBlendSchema(BaseModel):
    """
    Schema for flour blend data retrieval.
    """

    id: int
    name: str
    flour_01_id: int
    flour_01_percent: float
    flour_02_id: Optional[int]
    flour_02_percent: Optional[float]
    flour_03_id: Optional[int]
    flour_03_percent: Optional[float]
    flour_04_id: Optional[int]
    flour_04_percent: Optional[float]


class FlourBlendCreateSchema(BaseModel):
    """
    Schema for creating a new flour blend.
    """

    name: str
    flour_01_id: int
    flour_01_percent: float
    flour_02_id: Optional[int] = None
    flour_02_percent: Optional[float] = None
    flour_03_id: Optional[int] = None
    flour_03_percent: Optional[float] = None
    flour_04_id: Optional[int] = None
    flour_04_percent: Optional[float] = None


class FlourBlendUpdateSchema(BaseModel):
    """
    Schema for updating existing flour blend data.
    """

    name: Optional[str] = None
    flour_01_id: Optional[int] = None
    flour_01_percent: Optional[float] = None
    flour_02_id: Optional[int] = None
    flour_02_percent: Optional[float] = None
    flour_03_id: Optional[int] = None
    flour_03_percent: Optional[float] = None
    flour_04_id: Optional[int] = None
    flour_04_percent: Optional[float] = None
