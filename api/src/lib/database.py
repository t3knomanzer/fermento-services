#!/usr/bin/env python
"""
Database module to handle database connections and operations.
"""


from sqlite3 import DatabaseError

from sqlalchemy import MetaData, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from lib.config import Config
from lib.models import BaseModel

_engine = create_engine(
    Config().db_url,
    connect_args=Config().db_connect_args,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def create_database():
    """
    Create the database tables based on the defined models.
    """
    BaseModel.metadata.create_all(bind=_engine)


def close_database():
    """
    Ensures all created sessions are closed.
    """
    SessionLocal.close_all()


def purge_database():
    """
    Deletes and recreates all tables in the database.
    """
    try:
        metadata = MetaData()
        metadata.reflect(bind=_engine)
        metadata.drop_all(bind=_engine)

        create_database()
    except SQLAlchemyError as e:
        raise DatabaseError("Error purging database.") from e


def get_session():
    """
    Provides a transactional scope around a series of operations.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
