"""common module."""

from typing import Any, Final, NamedTuple, final

Paths = tuple[str, ...]

PROJECT_NAME_DEFAULT: Final = "no-project-name"


@final
class DirectoryOutput(NamedTuple):
    """DirectoryOutput class."""

    paths: Paths


def ignore_pytest[T: type](cls: T) -> T:
    """Mark a class to be ignored by pytest's test collection.

    Args:
        cls: The class to shield from pytest.

    Returns:
        The input class with `__test__ = False` dynamically applied.
    """
    target: Any = cls
    target.__test__ = False
    return cls
