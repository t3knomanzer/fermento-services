#!/usr/bin/env python
"""
Utility module for generating file paths.
"""


import uuid
from pathlib import Path

from lib.config import Config


def create_root_path() -> None:
    """
    Creates the root path folder if it doesn't exist.
    """
    get_root_path().mkdir(exist_ok=True, parents=True)


def get_root_path() -> Path:
    """
    Retrieves the root path for the application data storage.

    Returns:
        Path: The path to the root directory of the application.
    """
    result = Config().root_path
    if not result.exists():
        result.mkdir(exist_ok=True)
    return result


def generate_path(*args) -> Path:
    """
    Generates a full path by appending the given subpaths to the root path.

    Args:
        *args: Subpaths to append to the root path.

    Returns:
        Path: The generated full path.
    """
    return get_root_path().joinpath(*args)


def generate_unique_filename(extension: str = ".txt") -> str:
    """
    Generates a unique filename using a UUID with the specified file extension.

    Args:
        extension (str): The file extension to append to the filename.

    Returns:
        str: The generated unique filename.
    """
    # Generate a unique identifier
    unique_id = uuid.uuid4()

    # Create the filename by appending the extension
    filename = f"{unique_id}{extension}"

    return filename
