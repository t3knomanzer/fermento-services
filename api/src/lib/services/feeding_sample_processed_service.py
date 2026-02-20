#!/usr/bin/env python
""" """


from lib.models import FeedingSampleProcessedModel
from lib.repositories.feeding_sample_processed_repository import (
    FeedingSampleProcessedRepository,
)
from fermento_service_schemas.api.feeding_sample_processed import (
    FeedingSampleProcessedCreateSchema,
    FeedingSampleProcessedSchema,
    FeedingSampleProcessedUpdateSchema,
)
from lib.services.base_service import BaseCrudService


class FeedingSampleProcessedService(
    BaseCrudService[
        FeedingSampleProcessedRepository,
        FeedingSampleProcessedModel,
        FeedingSampleProcessedCreateSchema,
        FeedingSampleProcessedUpdateSchema,
        FeedingSampleProcessedSchema,
    ]
):
    def _convert_to_model(
        self,
        item: FeedingSampleProcessedCreateSchema | FeedingSampleProcessedUpdateSchema,
        exclude_unset: bool = False,
    ) -> FeedingSampleProcessedModel:
        return FeedingSampleProcessedModel(
            **item.model_dump(exclude_unset=exclude_unset)
        )

    def _convert_to_schema(
        self, model: FeedingSampleProcessedModel
    ) -> FeedingSampleProcessedSchema:
        return FeedingSampleProcessedSchema(**model.__dict__)
