#!/usr/bin/env python
"""
API router module for actor operations, providing endpoints for creating, reading, updating, and deleting actors.
"""


from lib.repositories.flour_repository import FlourRepository
from lib.routers.base_router import crud_router
from fermento_service_schemas.api.flour import (
    FlourCreateSchema,
    FlourSchema,
    FlourUpdateSchema,
)
from lib.services.flour_service import FlourService

router = crud_router(
    "/flour",
    FlourRepository,
    FlourService,
    FlourCreateSchema,
    FlourUpdateSchema,
    FlourSchema,
)
