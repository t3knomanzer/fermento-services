#!/usr/bin/env python
"""
API router module for actor operations, providing endpoints for creating, reading, updating, and deleting actors.
"""


from lib.repositories.feeding_sample_repository import FeedingSampleRepository
from lib.routers.base_router import crud_router
from lib.schemas.feeding_sample_schemas import (
    FeedingSampleCreateSchema,
    FeedingSampleSchema,
    FeedingSampleUpdateSchema,
)
from lib.services.feeding_sample_service import FeedingSampleService

router = crud_router(
    "/feeding-sample",
    FeedingSampleRepository,
    FeedingSampleService,
    FeedingSampleCreateSchema,
    FeedingSampleUpdateSchema,
    FeedingSampleSchema,
)
