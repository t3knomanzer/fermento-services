#!/usr/bin/env python
"""
Custom exception module for handling specific application errors.
"""


class FileWriteError(Exception):
    """
    Exception raised when an error occurs during file writing operations.
    """

    def __init__(self, message="Error ocurred while writing to a file"):
        super().__init__(message)


class ItemNotFound(Exception):
    """
    Exception raised when an expected item is not found in the database.
    """

    def __init__(self, message="The requested item was not found."):
        super().__init__(message)


class InvalidData(Exception):
    """
    Exception raised for errors in data validation.
    """

    def __init__(self, message="The data provided was invalid."):
        super().__init__(message)


class DatabaseError(Exception):
    """
    Exception raised for general database related errors.
    """

    def __init__(self, message="Databse error ocurred."):
        super().__init__(message)
