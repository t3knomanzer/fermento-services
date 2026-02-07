#!/usr/bin/env python
""" """


from sqlalchemy.orm import Session

from lib.models import FeedingEventModel
from lib.repositories.feeding_event_repository import (
    FeedingEventRepository,
)
from fermento_service_schemas.api.feeding_event import (
    FeedingEventCreateSchema,
    FeedingEventExpandedSchema,
    FeedingEventSchema,
    FeedingEventUpdateSchema,
)
from fermento_service_schemas.api.flour_blend import FlourBlendSchema
from fermento_service_schemas.api.jar import JarSchema
from fermento_service_schemas.api.starter import StarterSchema
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
        return FeedingEventSchema.model_validate(model, from_attributes=True)

    def _convert_to_expanded_schema(
        self, model: FeedingEventModel
    ) -> FeedingEventExpandedSchema:
        """Convert a model with eagerly-loaded relationships to an expanded schema."""
        data = FeedingEventExpandedSchema.model_validate(model, from_attributes=True)
        return data

    def read_expanded(
        self, session: Session, item_id: int
    ) -> FeedingEventExpandedSchema:
        """Read a single feeding event with nested related objects."""
        model = self._repository.read_expanded(session, item_id)
        return self._convert_to_expanded_schema(model)

    def all_expanded(self, session: Session) -> list[FeedingEventExpandedSchema]:
        """List all feeding events with nested related objects."""
        models = self._repository.all_expanded(session)
        return [self._convert_to_expanded_schema(m) for m in models]
