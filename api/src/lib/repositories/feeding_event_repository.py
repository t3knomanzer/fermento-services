#!/usr/bin/env python
""" """


from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from lib.exceptions import DatabaseError
from lib.models import FeedingEventModel
from lib.repositories.base_repository import BaseCrudRepository


class FeedingEventRepository(BaseCrudRepository[FeedingEventModel]):
    """Repository for FeedingModel."""

    model_class = FeedingEventModel

    def read_expanded(self, session: Session, item_id: int) -> FeedingEventModel:
        """Read a single feeding event with starter, flour_blend, jar eagerly loaded."""
        try:
            db_item = (
                session.query(self.model_class)
                .options(
                    joinedload(FeedingEventModel.starter),
                    joinedload(FeedingEventModel.flour_blend),
                    joinedload(FeedingEventModel.jar),
                )
                .filter(self.model_class.id == item_id)
                .first()
            )
        except SQLAlchemyError as e:
            raise DatabaseError(
                f"Error reading expanded item with id {item_id}."
            ) from e
        return db_item

    def all_expanded(self, session: Session) -> list[FeedingEventModel]:
        """List all feeding events with starter, flour_blend, jar eagerly loaded."""
        try:
            db_items = (
                session.query(self.model_class)
                .options(
                    selectinload(FeedingEventModel.starter),
                    selectinload(FeedingEventModel.flour_blend),
                    selectinload(FeedingEventModel.jar),
                )
                .all()
            )
        except SQLAlchemyError as e:
            raise DatabaseError("Error retrieving expanded items.") from e
        return db_items
