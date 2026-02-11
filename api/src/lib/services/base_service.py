#!/usr/bin/env python
"""
Base service module for handling CRUD operations using generic types.
"""

from typing import Generic, List, TypeVar

from sqlalchemy.orm import Session

from lib.exceptions import DatabaseError
from lib.log import logger
from lib.repositories.base_repository import BaseCrudRepository
from lib.utils.decorators import time_it

# Define type variables
TRepository = TypeVar("TRepository", bound="BaseCrudRepository")
TModel = TypeVar("TModel")
TCreateSchema = TypeVar("TCreateSchema")
TUpdateSchema = TypeVar("TUpdateSchema")
TSchema = TypeVar("TSchema")


class BaseCrudService(
    Generic[TRepository, TModel, TCreateSchema, TUpdateSchema, TSchema]
):
    """
    Generic base class for CRUD services, providing basic CRUD operations.
    """

    def __init__(self, repository: TRepository):
        """
        Initialize the service with a repository.

        Args:
            repository (TRepository): The repository associated with the CRUD operations.
        """
        self._repository: TRepository = repository

    def create(self, session: Session, item: TCreateSchema) -> TSchema:
        """
        Create a new item in the database.

        Args:
            session (Session): Database session.
            item (TCreateSchema): Item to be created.

        Returns:
            TSchema: The created item converted to schema.
        """
        logger.debug(f"Creating item: {item}")
        model = self._convert_to_model(item)
        self._repository.create(session, model)
        return self._convert_to_schema(model)

    def create_if_unique(self, session: Session, item: TCreateSchema) -> TSchema:
        """
        Create a new item in the database only if it does not already exist.

        Args:
            session (Session): Database session.
            item (TCreateSchema): Item to be created.

        Returns:
            TSchema: The created or found item converted to schema.
        """
        logger.debug(f"Creating item if it doesn't exist: {item}")
        model = self._convert_to_model(item)
        db_model = self._repository.find(session, model)
        if db_model is not None:
            logger.debug("Item found, skipping")
            model = db_model
        else:
            logger.debug("Item not found, creating...")
            self._repository.create(session, model)
        return self._convert_to_schema(model)

    def find(self, session: Session, item: TCreateSchema) -> TSchema | None:
        """
        Find an item in the database.

        Args:
            session (Session): Database session.
            item (TCreateSchema): Item to find.

        Returns:
            TSchema: The item found converted to schema.
        """
        model = self._convert_to_model(item)
        try:
            return self._repository.find(session, model)
        except DatabaseError:
            return None

    def read(self, session: Session, item_id: int) -> TSchema:
        """
        Read an item from the database by its ID.

        Args:
            session (Session): Database session.
            item_id (int): ID of the item to be retrieved.

        Returns:
            TSchema: The retrieved item converted to schema.
        """
        logger.debug(f"Reading item {item_id}")
        model = self._repository.read(session, item_id)
        return self._convert_to_schema(model)

    def update(self, session: Session, item_id: int, item: TUpdateSchema) -> TSchema:
        """
        Update an existing item in the database.

        Args:
            session (Session): Database session.
            item_id (int): ID of the item to be updated.
            item (TUpdateSchema): Updated data for the item.

        Returns:
            TSchema: The updated item converted to schema.
        """
        logger.debug(f"Updating item: {item_id} with: {item}")
        model = self._convert_to_model(item, exclude_unset=True)
        model = self._repository.update(session, item_id, model)
        return self._convert_to_schema(model)

    def delete(self, session: Session, item_id: int) -> TSchema:
        """
        Delete an item from the database by its ID.

        Args:
            session (Session): Database session.
            item_id (int): ID of the item to be deleted.

        Returns:
            TSchema: The schema of the deleted item.
        """
        logger.debug(f"Deleting item: {item_id}")
        model = self._repository.delete(session, item_id)
        return self._convert_to_schema(model)

    def all(self, session: Session) -> List[TSchema]:
        """
        Read all items from the database.

        Args:
            session (Session): Database session.

        Returns:
            List[TSchema]: The retrieved items converted to schemas.
        """
        models = self._repository.all(session)
        logger.debug(f"Reading {len(models)} items")
        return [self._convert_to_schema(o) for o in models]

    def _convert_to_model(
        self, schema: TCreateSchema | TUpdateSchema, exclude_unset: bool = False
    ) -> TModel:
        """
        Abstract method to convert a schema to a model. Must be implemented in subclasses.

        Args:
            schema (TCreateSchema | TUpdateSchema): Schema to be converted.
            exclude_unset (bool): Flag indicating whether to exclude unset fields.

        Returns:
            TModel: The converted model.
        """
        raise NotImplementedError

    def _convert_to_schema(self, model: TModel) -> TSchema:
        """
        Abstract method to convert a model to a schema. Must be implemented in subclasses.

        Args:
            model (TModel): Model to be converted.

        Returns:
            TSchema: The converted schema.
        """
        raise NotImplementedError
