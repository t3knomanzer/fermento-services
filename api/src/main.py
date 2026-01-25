#!/usr/bin/env python
"""
Main application module for setting up and running the FastAPI application.
"""

from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lib.config import Config
from lib.database import close_database, create_database
from lib.logging import logger
from lib.routers import jar_router

from lib.utils.pathing import create_root_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for managing application startup and shutdown events.
    """
    logger.info("Application starting...")
    logger.debug("Application Config:")
    for key, value in Config().model_dump().items():
        logger.debug(f"{key}: {value}")

    logger.debug("Creating root path...")
    create_root_path()
    logger.debug("Creating database...")
    create_database()

    yield

    logger.info("Application shutting down...")
    logger.debug("Closing database connections...")
    close_database()  # Close all sessions


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, **Config().cors_config.model_dump())
app.include_router(jar_router.router)


@app.get("/healthcheck")
def healthcheck() -> Dict[str, str]:
    """
    Healthcheck endpoint to ensure the service is running.

    Returns:
        Response: A simple HTTP response indicating the service is up.
    """
    return {"result": "ok"}
