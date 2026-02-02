#!/usr/bin/env python
""" """


from lib.models import FeedingSampleModel
from lib.repositories.feeding_sample_repository import (
    FeedingSampleRepository,
)
from lib.schemas.feeding_sample import (
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
