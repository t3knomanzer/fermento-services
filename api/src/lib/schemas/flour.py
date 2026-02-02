#!/usr/bin/env python
"""
Schemas module for starter data validation and serialization.
"""


from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class FlourSchema(BaseModel):
    """
    Schema for starter data retrieval.
    """

    id: int
    name: str
    short_name: str
    brand: str
    ingredients: str
    milling: str
    organic: bool
    hydration_min: float
    hydration_max: float
    protein: float
    W: float
    P: float
    L: float
    PL: float
    notes: str
    tested: bool


class FlourCreateSchema(BaseModel):
    """
    Schema for creating a new starter.
    """

    name: str
    short_name: str
    brand: str
    organic: bool
    ingredients: str
    milling: Optional[str]
    hydration_min: Optional[float]
    hydration_max: Optional[float]
    protein: float
    W: Optional[float]
    P: Optional[float]
    L: Optional[float]
    PL: Optional[float]
    notes: Optional[str]
    tested: bool


class FlourUpdateSchema(BaseModel):
    """
    Schema for updating existing starter data.
    """

    name: Optional[str]
    short_name: Optional[str]
    brand: Optional[str]
    organic: Optional[bool]
    ingredients: Optional[str]
    milling: Optional[str]
    hydration_min: Optional[float]
    hydration_max: Optional[float]
    protein: Optional[float]
    W: Optional[float]
    P: Optional[float]
    L: Optional[float]
    PL: Optional[float]
    notes: Optional[str]
    tested: Optional[bool]
