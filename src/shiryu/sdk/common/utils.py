"""utils module."""

from pathlib import PurePosixPath
from typing import Final

PROJECT_SOURCE_CODE_FOLDER: Final = "src"
PROJECT_TESTS_FOLDER: Final = "tests"
TESTS_UNIT_FOLDER: Final = "unit"
TESTS_UNIT_PATH: Final = PurePosixPath(PROJECT_TESTS_FOLDER) / TESTS_UNIT_FOLDER
