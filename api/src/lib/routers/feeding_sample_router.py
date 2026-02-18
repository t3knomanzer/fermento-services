#!/usr/bin/env python
"""
API router module for actor operations, providing endpoints for creating, reading, updating, and deleting actors.
"""


from datetime import datetime
from typing import Annotated

from fastapi import Depends, File, Request
from lib.database import get_session
from lib.repositories.feeding_sample_repository import FeedingSampleRepository
from lib.routers.base_router import crud_router
from fermento_service_schemas.api.feeding_sample import (
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


@router.post("/feeding-sample/image")
async def create_image(
    request: Request,
    bundle_id: int,
    session=Depends(get_session),
):
    """Endpoint to receive feeding sample images."""
    image_bytes = await request.body()

    # Generate resource key for S3
    resource_key = f"feeding-sample/images/{bundle_id}.jpg"
    # Upload to S3
    service = FeedingSampleService(FeedingSampleRepository())
    service.upload_image(image_bytes, resource_key)

    # Update feeding sample with frame key
    schema = service.find(
        session,
        FeedingSampleCreateSchema(
            bundle_id=bundle_id,
            feeding_event_id=0,
            temperature=0,
            humidity=0,
            co2=0,
            distance=0,
            image_key=None,
        ),
    )
    if schema is None:
        return {
            "message": "Feeding sample not found for bundle_id",
            "bundle_id": bundle_id,
        }
    update_schema = FeedingSampleUpdateSchema(image_key=resource_key)
    service.update(item_id=schema.id, item=update_schema, session=session)
    return {"message": "Frame uploaded successfully", "resource_key": resource_key}
