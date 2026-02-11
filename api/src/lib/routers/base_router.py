#!/usr/bin/env python
""" """


from typing import List, Type

from fastapi import APIRouter, Depends, HTTPException

from lib.database import get_session
from lib.exceptions import DatabaseError
from lib.log import LogLevel, logger
from pydantic import BaseModel
from lib.repositories.base_repository import BaseCrudRepository
from lib.services.base_service import BaseCrudService
from lib.utils.decorators import time_it


def crud_router(
    prefix: str,
    repository_class: Type[BaseCrudRepository],
    service_class: Type[BaseCrudService],
    create_schema: Type[BaseModel],
    update_schema: Type[BaseModel],
    schema: Type[BaseModel],
    include_routes: List[str] = ["create", "read", "update", "delete", "read_all"],
) -> APIRouter:
    router = APIRouter(tags=[prefix[1:]])

    if "create" in include_routes:

        @router.post(f"{prefix}", response_model=schema)
        @time_it(logger.info)
        def create(item: create_schema, session=Depends(get_session)):  # type: ignore
            logger.info(f"{router.prefix} Creating item: {item}")
            service = service_class(repository_class())
            try:
                schema = service.create(session, item)
            except DatabaseError as e:
                raise HTTPException(500, str(e.__cause__ or e))
            return schema

    if "read" in include_routes:

        @router.get(f"{prefix}/{{item_id}}", response_model=schema)
        @time_it(logger.info)
        def read(item_id: int, session=Depends(get_session)):
            logger.info(f"{router.prefix} Reading item id: {item_id}")
            service = service_class(repository_class())
            try:
                schema = service.read(session, item_id)
            except DatabaseError as e:
                raise HTTPException(500, str(e.__cause__ or e))
            return schema

    if "update" in include_routes:

        @router.put(f"{prefix}/{{item_id}}", response_model=schema)
        @time_it(logger.info)
        def update(item_id: int, item: update_schema, session=Depends(get_session)):  # type: ignore
            logger.log(
                LogLevel.INFO,
                f"{router.prefix} Updating item id: {item_id} with: {item}",
            )
            service = service_class(repository_class())
            try:
                schema = service.update(session, item_id, item)
            except DatabaseError as e:
                raise HTTPException(500, str(e.__cause__ or e))
            return schema

    if "delete" in include_routes:

        @time_it(logger.info)
        @router.delete(f"{prefix}/{{item_id}}", response_model=schema)
        def delete(item_id: int, session=Depends(get_session)):
            logger.log(LogLevel.INFO, f"{router.prefix} Deleting item id: {item_id}")
            service = service_class(repository_class())
            try:
                schema = service.delete(session, item_id)
            except DatabaseError as e:
                raise HTTPException(500, str(e.__cause__ or e))
            return schema

    if "read_all" in include_routes:

        @router.get(f"{prefix}s", response_model=List[schema])
        @time_it(logger.info)
        def read_all(session=Depends(get_session)):
            service = service_class(repository_class())
            try:
                schemas = service.all(session)
                logger.log(
                    LogLevel.INFO, f"{router.prefix} Getting {len(schemas)} items"
                )
            except DatabaseError as e:
                raise HTTPException(500, str(e.__cause__ or e))
            return schemas

    return router
