#!/usr/bin/env python
""" """


from lib.models import JarModel
from lib.repositories.jar_repository import (
    JarRepository,
)
from lib.schemas.jar import JarCreateSchema, JarSchema, JarUpdateSchema
from lib.services.base_service import BaseCrudService


class JarService(
    BaseCrudService[
        JarRepository, JarModel, JarCreateSchema, JarUpdateSchema, JarSchema
    ]
):
    def _convert_to_model(
        self, item: JarCreateSchema | JarUpdateSchema, exclude_unset: bool = False
    ) -> JarModel:
        return JarModel(**item.model_dump(exclude_unset=exclude_unset))

    def _convert_to_schema(self, model: JarModel) -> JarSchema:
        return JarSchema(**model.__dict__)
