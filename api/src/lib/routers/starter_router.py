#!/usr/bin/env python
"""
API router module for actor operations, providing endpoints for creating, reading, updating, and deleting actors.
"""


from lib.repositories.starter_repository import StarterRepository
from lib.routers.base_router import crud_router
from fermento_schemas.api.starter import (
    StarterCreateSchema,
    StarterSchema,
    StarterUpdateSchema,
)
from lib.services.starter_service import StarterService

router = crud_router(
    "/starter",
    StarterRepository,
    StarterService,
    StarterCreateSchema,
    StarterUpdateSchema,
    StarterSchema,
)
