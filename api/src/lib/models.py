#!/usr/bin/env python
"""
Module defining the database models for the application.
"""


from sqlalchemy import (
    String,
    Integer,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class BaseModel(DeclarativeBase):
    """
    Base model from which all other models inherit, providing common configuration.
    """

    compare_fields: list[str] = []


class JarModel(BaseModel):
    __tablename__ = "jars"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    height: Mapped[int] = mapped_column(Integer())
