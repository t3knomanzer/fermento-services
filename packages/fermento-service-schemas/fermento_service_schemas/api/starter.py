#!/usr/bin/env python
"""
Schemas module for starter data validation and serialization.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class StarterSchema(BaseModel):
    """
    Schema for starter data retrieval.
    """

    id: int
    name: str
    birth_date: datetime


class StarterCreateSchema(BaseModel):
    """
    Schema for creating a new starter.
    """

    name: str
    birth_date: datetime


class StarterUpdateSchema(BaseModel):
    """
    Schema for updating existing starter data.
    """

    name: Optional[str]
    birth_date: Optional[datetime]
