#!/usr/bin/env python
"""
Schemas module for jar data validation and serialization.
"""


from typing import List, Optional

from pydantic import BaseModel


class JarSchema(BaseModel):
    """
    Schema for jar data retrieval.
    """

    id: int
    name: str
    height: int


class JarCreateSchema(BaseModel):
    """
    Schema for creating a new jar.
    """

    name: str
    height: int


class JarUpdateSchema(BaseModel):
    """
    Schema for updating existing jar data.
    """

    name: Optional[str]
    height: Optional[int]
