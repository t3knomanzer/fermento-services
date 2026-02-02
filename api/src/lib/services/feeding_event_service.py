#!/usr/bin/env python
""" """


from lib.models import FeedingEventModel
from lib.repositories.feeding_event_repository import (
    FeedingEventRepository,
)
from lib.schemas.feeding_event import (
    FeedingEventCreateSchema,
    FeedingEventSchema,
    FeedingEventUpdateSchema,
)
from lib.services.base_service import BaseCrudService


class FeedingEventService(
    BaseCrudService[
        FeedingEventRepository,
        FeedingEventModel,
        FeedingEventCreateSchema,
        FeedingEventUpdateSchema,
        FeedingEventSchema,
    ]
):
    def _convert_to_model(
        self,
        item: FeedingEventCreateSchema | FeedingEventUpdateSchema,
        exclude_unset: bool = False,
    ) -> FeedingEventModel:
        return FeedingEventModel(**item.model_dump(exclude_unset=exclude_unset))

    def _convert_to_schema(self, model: FeedingEventModel) -> FeedingEventSchema:
        return FeedingEventSchema(**model.__dict__)
