#!/usr/bin/env python
""" """


from lib.models import StarterModel
from lib.repositories.starter_repository import (
    StarterRepository,
)
from lib.schemas.starter import (
    StarterCreateSchema,
    StarterSchema,
    StarterUpdateSchema,
)
from lib.services.base_service import BaseCrudService


class StarterService(
    BaseCrudService[
        StarterRepository,
        StarterModel,
        StarterCreateSchema,
        StarterUpdateSchema,
        StarterSchema,
    ]
):
    def _convert_to_model(
        self,
        item: StarterCreateSchema | StarterUpdateSchema,
        exclude_unset: bool = False,
    ) -> StarterModel:
        return StarterModel(**item.model_dump(exclude_unset=exclude_unset))

    def _convert_to_schema(self, model: StarterModel) -> StarterSchema:
        return StarterSchema(**model.__dict__)
