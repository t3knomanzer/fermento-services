#!/usr/bin/env python
"""
Module for handling io operations.
"""


from pathlib import Path
from typing import BinaryIO

import aiofiles


async def write_file(file: BinaryIO, file_path: str, create_dirs: bool = True) -> None:
    """
    Asynchronously write data to a file.

    Args:
        file (BinaryIO): A file-like object to read data from.
        file_path (str): The path to the file where data will be written.
        create_dirs (bool): If True, create the directory path to the file if it does not exist.
    """
    if create_dirs:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(file_path, "wb+") as target_file:
        await target_file.write(file.read())
