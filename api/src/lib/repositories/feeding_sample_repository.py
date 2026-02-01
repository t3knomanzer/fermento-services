#!/usr/bin/env python
""" """


from lib.models import FeedingSampleModel
from lib.repositories.base_repository import BaseCrudRepository


class FeedingSampleRepository(BaseCrudRepository[FeedingSampleModel]):
    """Repository for FeedingSampleModel."""

    model_class = FeedingSampleModel
