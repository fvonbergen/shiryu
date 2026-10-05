"""common module."""

from typing import Any, NamedTuple, final

Paths = tuple[str, ...]


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
