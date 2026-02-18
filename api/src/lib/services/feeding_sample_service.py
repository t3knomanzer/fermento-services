#!/usr/bin/env python
""" """


import boto3
from lib.models import FeedingSampleModel
from lib.repositories.feeding_sample_repository import (
    FeedingSampleRepository,
)
from fermento_service_schemas.api.feeding_sample import (
    FeedingSampleCreateSchema,
    FeedingSampleSchema,
    FeedingSampleUpdateSchema,
)
from lib.services.base_service import BaseCrudService


class FeedingSampleService(
    BaseCrudService[
        FeedingSampleRepository,
        FeedingSampleModel,
        FeedingSampleCreateSchema,
        FeedingSampleUpdateSchema,
        FeedingSampleSchema,
    ]
):
    def _convert_to_model(
        self,
        item: FeedingSampleCreateSchema | FeedingSampleUpdateSchema,
        exclude_unset: bool = False,
    ) -> FeedingSampleModel:
        return FeedingSampleModel(**item.model_dump(exclude_unset=exclude_unset))

    def _convert_to_schema(self, model: FeedingSampleModel) -> FeedingSampleSchema:
        return FeedingSampleSchema(**model.__dict__)

    def upload_image(self, file: bytes, resource_key: str):
        """Uploads a feeding sample image to S3."""
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket="feeding-sample-images",
            Key=resource_key,
            Body=file,
            ContentType="image/jpeg",
        )
        # Repository method to update feeding sample with image key
