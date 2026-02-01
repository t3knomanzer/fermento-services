#!/usr/bin/env python
""" """


from lib.models import FlourBlendModel
from lib.repositories.base_repository import BaseCrudRepository


class FlourBlendRepository(BaseCrudRepository[FlourBlendModel]):
    """Repository for FlourBlendModel."""

    model_class = FlourBlendModel
