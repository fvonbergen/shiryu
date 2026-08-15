"""enum module."""

from collections.abc import Mapping
from enum import Enum, unique
from typing import TypeVar, cast

EnumType = TypeVar("EnumType", bound=Enum)


def get_enum_keys(enum: type[Enum]) -> set[str]:
    """
    Get a set of the enumeration keys.

    Args:
        enum: Enumeration class.

    Returns:
        A set of enumeration keys.
    """
    return {key for key in enum.__members__}


def get_enum_values(enum: type[Enum]) -> set[object]:
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


def create_enum(
    name: str, members: Mapping[str, object], *, is_unique: bool = True
) -> type[EnumType]:  # pyright: ignore [reportInvalidTypeVarUse]
    """
    Programmatically create a dynamic Enum with proper type annotations.

    Args:
        name: The class name for the generated Enum.
        members: A dictionary/mapping of member names to values.
        is_unique: Whether to enforce unique enum values using @unique.

    Returns:
        The generated Enum class type.
    """
    return cast(
        type[EnumType],
        unique(Enum(name, members)) if is_unique else Enum(name, members),  # pyright: ignore [reportArgumentType]
    )
