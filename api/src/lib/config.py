#!/usr/bin/env python
"""
Configuration module for setting up application settings.
"""


from pathlib import Path
from typing import List, Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class CorsConfig(BaseModel):
    """
    Configuration class for handling Cross-Origin Resource Sharing (CORS) settings.
    """

    allow_origins: List[str] = ["*", "*:8091"]
    allow_credentials: bool = True
    allow_methods: List[str] = ["*"]
    allow_headers: List[str] = ["*"]


class Config(BaseSettings):
    """
    Main configuration class which loads settings from environment variables and defaults.
    """

    model_config = SettingsConfigDict(env_prefix="API_", env_nested_delimiter="__")

    root_path: Path = Path.home() / "fermento"
    uploads_dir: str = "uploads"
    db_url: str = "postgresql+psycopg://fermento:pw123@db:5432/fermento"
    db_connect_args: dict = {}
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"

    cors_config: CorsConfig = CorsConfig()
