#!/usr/bin/env python
""" """


from lib.models import FlourModel
from lib.repositories.flour_repository import (
    FlourRepository,
)
from fermento_service_schemas.api.flour import (
    FlourCreateSchema,
    FlourSchema,
    FlourUpdateSchema,
)
from lib.services.base_service import BaseCrudService


class FlourService(
    BaseCrudService[
        FlourRepository,
        FlourModel,
        FlourCreateSchema,
        FlourUpdateSchema,
        FlourSchema,
    ]
):
    def _convert_to_model(
        self,
        item: FlourCreateSchema | FlourUpdateSchema,
        exclude_unset: bool = False,
    ) -> FlourModel:
        return FlourModel(**item.model_dump(exclude_unset=exclude_unset))

    def _convert_to_schema(self, model: FlourModel) -> FlourSchema:
        return FlourSchema(**model.__dict__)
