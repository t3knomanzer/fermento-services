#!/usr/bin/env python
"""
API router module for actor operations, providing endpoints for creating, reading, updating, and deleting actors.
"""


from datetime import datetime
from typing import Annotated

from fastapi import Depends, File, Request
from lib.database import get_session
from lib.repositories.feeding_sample_processed_repository import (
    FeedingSampleProcessedRepository,
)
from lib.routers.base_router import crud_router
from fermento_service_schemas.api.feeding_sample_processed import (
    FeedingSampleProcessedCreateSchema,
    FeedingSampleProcessedSchema,
    FeedingSampleProcessedUpdateSchema,
)
from lib.services.feeding_sample_processed_service import FeedingSampleProcessedService

router = crud_router(
    "/feeding-sample-processed",
    FeedingSampleProcessedRepository,
    FeedingSampleProcessedService,
    FeedingSampleProcessedCreateSchema,
    FeedingSampleProcessedUpdateSchema,
    FeedingSampleProcessedSchema,
)
