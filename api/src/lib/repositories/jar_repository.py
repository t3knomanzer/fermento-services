#!/usr/bin/env python
""" """


from lib.models import JarModel
from lib.repositories.base_repository import BaseCrudRepository


class JarRepository(BaseCrudRepository[JarModel]):
    """Repository for JarModel."""

    model_class = JarModel
