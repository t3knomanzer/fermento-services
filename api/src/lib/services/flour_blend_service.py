#!/usr/bin/env python
""" """


from lib.models import FlourBlendModel
from lib.repositories.flour_blend_repository import (
    FlourBlendRepository,
)
from fermento_schemas.api.flour_blend import (
    FlourBlendCreateSchema,
    FlourBlendSchema,
    FlourBlendUpdateSchema,
)
from lib.services.base_service import BaseCrudService


class FlourBlendService(
    BaseCrudService[
        FlourBlendRepository,
        FlourBlendModel,
        FlourBlendCreateSchema,
        FlourBlendUpdateSchema,
        FlourBlendSchema,
    ]
):
    def _convert_to_model(
        self,
        item: FlourBlendCreateSchema | FlourBlendUpdateSchema,
        exclude_unset: bool = False,
    ) -> FlourBlendModel:
        return FlourBlendModel(**item.model_dump(exclude_unset=exclude_unset))

    def _convert_to_schema(self, model: FlourBlendModel) -> FlourBlendSchema:
        return FlourBlendSchema(**model.__dict__)
