#!/usr/bin/env python
"""
API router module for actor operations, providing endpoints for creating, reading, updating, and deleting actors.
"""


from lib.repositories.flour_blend_repository import FlourBlendRepository
from lib.routers.base_router import crud_router
from fermento_service_schemas.api.flour_blend import (
    FlourBlendCreateSchema,
    FlourBlendSchema,
    FlourBlendUpdateSchema,
)
from lib.services.flour_blend_service import FlourBlendService

router = crud_router(
    "/flour-blend",
    FlourBlendRepository,
    FlourBlendService,
    FlourBlendCreateSchema,
    FlourBlendUpdateSchema,
    FlourBlendSchema,
)
