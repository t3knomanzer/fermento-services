#!/usr/bin/env python
"""
API router module for feeding event operations, providing CRUD endpoints
plus expanded read endpoints that include related starter, flour_blend, and jar data.
"""


from typing import List

from fastapi import Depends

from lib.database import get_session
from lib.repositories.feeding_event_repository import FeedingEventRepository
from lib.routers.base_router import crud_router
from fermento_service_schemas.api.feeding_event import (
    FeedingEventCreateSchema,
    FeedingEventExpandedSchema,
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


@router.get(
    "/feeding-event/{item_id}/expanded", response_model=FeedingEventExpandedSchema
)
def read_expanded(item_id: int, session=Depends(get_session)):
    """Read a single feeding event with nested starter, flour_blend, and jar."""
    service = FeedingEventService(FeedingEventRepository())
    return service.read_expanded(session, item_id)


@router.get("/feeding-events/expanded", response_model=List[FeedingEventExpandedSchema])
def read_all_expanded(session=Depends(get_session)):
    """List all feeding events with nested starter, flour_blend, and jar."""
    service = FeedingEventService(FeedingEventRepository())
    return service.all_expanded(session)
