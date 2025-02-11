"""enum module."""

from enum import Enum
from typing import Any


def get_enum_keys(enum: type[Enum]) -> set[str]:
    """
    Get a set of the enumeration keys.

    Args:
        enum: Enumeration class.

    Returns:
        A set of enumeration keys.
    """
    return {key for key in enum.__members__}


def get_enum_values(enum: type[Enum]) -> set[Any]:  # pyright: ignore [reportGeneralTypeIssues]
    """
    Get a set of the enumeration values.

    Args:
        enum: Enumeration class.

    Returns:
        A set of enumeration values.
    """
    return {element.value for element in enum}


def get_enum_elements(enum: type[Enum]) -> set[Enum]:
    """
    Get a set of enumeration elements.

    Args:
        enum: Enumeration class.

    Returns:
        A set of enumeration key value.
    """
    return set(enum)
