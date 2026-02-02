#!/usr/bin/env python
"""
API router module for actor operations, providing endpoints for creating, reading, updating, and deleting actors.
"""


from lib.repositories.feeding_event_repository import FeedingEventRepository
from lib.routers.base_router import crud_router
from lib.schemas.feeding_event import (
    FeedingEventCreateSchema,
    FeedingEventSchema,
    FeedingEventUpdateSchema,
)
from lib.services.feeding_event_service import FeedingEventService

router = crud_router(
    "/feeding-event",
    FeedingEventRepository,
    FeedingEventService,
    FeedingEventCreateSchema,
    FeedingEventUpdateSchema,
    FeedingEventSchema,
)
