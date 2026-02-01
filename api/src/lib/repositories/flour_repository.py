#!/usr/bin/env python
""" """


from lib.models import FlourModel
from lib.repositories.base_repository import BaseCrudRepository


class FlourRepository(BaseCrudRepository[FlourModel]):
    """Repository for FlourModel."""

    model_class = FlourModel
