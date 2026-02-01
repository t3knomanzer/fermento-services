#!/usr/bin/env python
""" """


from lib.models import StarterModel
from lib.repositories.base_repository import BaseCrudRepository


class StarterRepository(BaseCrudRepository[StarterModel]):
    """Repository for StarterModel."""

    model_class = StarterModel
