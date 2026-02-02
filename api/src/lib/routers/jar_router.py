#!/usr/bin/env python
"""
API router module for actor operations, providing endpoints for creating, reading, updating, and deleting actors.
"""


from lib.repositories.jar_repository import JarRepository
from lib.routers.base_router import crud_router
from lib.schemas.jar import (
    JarCreateSchema,
    JarSchema,
    JarUpdateSchema,
)
from lib.services.jar_service import JarService

router = crud_router(
    "/jar",
    JarRepository,
    JarService,
    JarCreateSchema,
    JarUpdateSchema,
    JarSchema,
)
