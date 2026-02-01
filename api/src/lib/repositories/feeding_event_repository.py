#!/usr/bin/env python
""" """


from lib.models import FeedingEventModel
from lib.repositories.base_repository import BaseCrudRepository


class FeedingEventRepository(BaseCrudRepository[FeedingEventModel]):
    """Repository for FeedingModel."""

    model_class = FeedingEventModel
