#!/usr/bin/env python
"""
Module defining the database models for the application.
"""

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class BaseModel(DeclarativeBase):
    """
    Base model from which all other models inherit, providing common configuration.
    """

    compare_fields: list[str] = []


class StarterModel(BaseModel):
    __tablename__ = "starters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    birth_date: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class JarModel(BaseModel):
    __tablename__ = "jars"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    height: Mapped[int] = mapped_column(Integer())


class FlourModel(BaseModel):
    __tablename__ = "flours"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str] = mapped_column(String(255))
    brand: Mapped[str] = mapped_column(String(255))
    ingredients: Mapped[str] = mapped_column(String(255))
    milling: Mapped[str] = mapped_column(String(255))
    organic: Mapped[bool] = mapped_column(Boolean())
    hydration_min: Mapped[float] = mapped_column(Float())
    hydration_max: Mapped[float] = mapped_column(Float())
    protein: Mapped[float] = mapped_column(Float())
    W: Mapped[float] = mapped_column(Float())
    P: Mapped[float] = mapped_column(Float())
    L: Mapped[float] = mapped_column(Float())
    PL: Mapped[float] = mapped_column(Float())
    notes: Mapped[str] = mapped_column(String(255))
    tested: Mapped[bool] = mapped_column(Boolean())


class FlourBlendModel(BaseModel):
    __tablename__ = "flour_blends"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))

    flour_01_id: Mapped[int] = mapped_column(ForeignKey("flours.id"))
    flour_01_percent: Mapped[float] = mapped_column(Float)

    flour_02_id: Mapped[int | None] = mapped_column(
        ForeignKey("flours.id"), nullable=True
    )
    flour_02_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    flour_03_id: Mapped[int | None] = mapped_column(
        ForeignKey("flours.id"), nullable=True
    )
    flour_03_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    flour_04_id: Mapped[int | None] = mapped_column(
        ForeignKey("flours.id"), nullable=True
    )
    flour_04_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Optional relationships (handy for joins; you don’t have to expose them in schemas)
    flour_01: Mapped[FlourModel] = relationship(foreign_keys=[flour_01_id])
    flour_02: Mapped[FlourModel | None] = relationship(foreign_keys=[flour_02_id])
    flour_03: Mapped[FlourModel | None] = relationship(foreign_keys=[flour_03_id])
    flour_04: Mapped[FlourModel | None] = relationship(foreign_keys=[flour_04_id])


class FeedingEventModel(BaseModel):
    __tablename__ = "feeding_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[str] = mapped_column(String(255))
    starter_id: Mapped[int] = mapped_column(ForeignKey("starters.id"))
    starter_ratio: Mapped[float] = mapped_column(Float())
    water_ratio: Mapped[float] = mapped_column(Float())
    flour_ratio: Mapped[float] = mapped_column(Float())
    flour_blend_id: Mapped[int] = mapped_column(ForeignKey("flour_blends.id"))
    jar_id: Mapped[int] = mapped_column(ForeignKey("jars.id"))

    starter: Mapped[StarterModel] = relationship(foreign_keys=[starter_id])
    flour_blend: Mapped[FlourBlendModel] = relationship(foreign_keys=[flour_blend_id])
    jar: Mapped[JarModel] = relationship(foreign_keys=[jar_id])


class FeedingSampleModel(BaseModel):
    __tablename__ = "feeding_samples"

    id: Mapped[int] = mapped_column(primary_key=True)
    feeding_event_id: Mapped[int] = mapped_column(ForeignKey("feeding_events.id"))
    temperature: Mapped[float] = mapped_column(Float())
    humidity: Mapped[float] = mapped_column(Float())
    co2: Mapped[float] = mapped_column(Float())
    distance: Mapped[float] = mapped_column(Float())

    feeding: Mapped[FeedingEventModel] = relationship(foreign_keys=[feeding_event_id])
