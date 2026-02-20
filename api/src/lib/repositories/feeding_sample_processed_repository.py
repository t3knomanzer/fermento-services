#!/usr/bin/env python
""" """


from lib.models import FeedingSampleModel, FeedingSampleProcessedModel
from lib.repositories.base_repository import BaseCrudRepository


class FeedingSampleProcessedRepository(BaseCrudRepository[FeedingSampleProcessedModel]):
    """Repository for FeedingSampleModel."""

    model_class = FeedingSampleProcessedModel
