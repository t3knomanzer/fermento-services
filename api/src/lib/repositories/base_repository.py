#!/usr/bin/env python
""" """


from typing import Any, Generic, List, Type, TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from lib.exceptions import DatabaseError
from lib.models import BaseModel

# Type variable to represent any subclass of BaseModel
TModel = TypeVar("TModel", bound="BaseModel")


class BaseCrudRepository(Generic[TModel]):
    """A generic repository base class for handling CRUD operations."""

    model_class: Type[TModel]

    def _generate_conditions(self, item: TModel) -> List[Any]:
        """Generate filter conditions for querying the database.

        Args:
            item (TModel): The item to generate conditions for.

        Returns:
            List[Any]: A list of conditions to filter the query.
        """
        return [
            getattr(type(item), field) == getattr(item, field)
            for field in item.compare_fields
        ]

    def _first(self, session: Session, item_id: int) -> TModel:
        """Retrieve first item with the given id.

        Args:
            session (Session): The database session.

        Returns:
            TModel: First item with the given id in the table.
        """
        try:
            db_item = (
                session.query(self.model_class)
                .filter(self.model_class.id == item_id)
                .first()
            )
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving item with id {item_id}.") from e

        return db_item

    def create(self, session: Session, item: TModel) -> TModel:
        """Add a new item to the database.

        Args:
            session (Session): The database session.
            item (TModel): The item to add.

        Returns:
            TModel: The added item.
        """
        try:
            session.add(item)
            session.commit()
            session.refresh(item)
        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError("Error creating item.") from e
        return item

    def read(self, session: Session, item_id: int) -> TModel:
        """Retrieve an item by its ID.

        Args:
            session (Session): The database session.
            id (int): The ID of the item to retrieve.

        Returns:
            TModel: The retrieved item.
        """
        return self._first(session, item_id)

    def update(self, session: Session, item_id: int, item: TModel) -> TModel:
        """Update an existing item in the database.

        Args:
            session (Session): The database session.
            id (int): The ID of the item to update.
            item (TModel): The item with updated values.

        Returns:
            TModel: The updated item.

        Raises:
            DatabaseError: If the item is not found or update fails.
        """
        db_item = self._first(session, item_id)
        if db_item is None:
            raise DatabaseError(f"Item id {item_id} not found.")

        for attr, value in vars(item).items():
            if hasattr(db_item, attr) and not attr.startswith("_"):
                setattr(db_item, attr, value)

        try:
            session.commit()
            session.refresh(db_item)
        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(f"Error updating item with id {item_id}") from e
        return db_item

    def delete(self, session: Session, item_id: int) -> TModel:
        """Delete an item from the database by its ID.

        Args:
            session (Session): The database session.
            id (int): The ID of the item to delete.

        Returns:
            TModel: The deleted item.

        Raises:
            DatabaseError: If the item is not found or deletion fails.
        """
        db_item = self._first(session, item_id)
        if db_item is None:
            raise DatabaseError(f"Item id {item_id} not found.")
        try:
            session.delete(db_item)
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(f"Error deleting item with id {item_id}") from e
        return db_item

    def all(self, session: Session) -> List[TModel]:
        """Retrieve all items.

        Args:
            session (Session): The database session.

        Returns:
            List[TModel]: All the items in the table.
        """
        try:
            db_item = session.query(self.model_class).all()
        except SQLAlchemyError as e:
            raise DatabaseError("Error retrieving items.") from e

        return db_item

    def find(self, session: Session, item: TModel) -> TModel:
        """Find the first item matching the given conditions.

        Args:
            session (Session): The database session.
            item (TModel): The item with conditions to search for.

        Returns:
            TModel: The first matching item.
        """
        conditions = self._generate_conditions(item)
        try:
            result = session.query(self.model_class).filter(*conditions).first()
        except SQLAlchemyError as e:
            raise DatabaseError("Error finding item.") from e
        return result
