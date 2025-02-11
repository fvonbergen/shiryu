"""case module."""

import re
from enum import Enum, auto, unique
from typing import final


def camel_case_to_snake_case(string: str) -> str:
    """
    Convert a camel case string to a snake case string.

    Args:
        string: An input string.

    Returns:
        A snake case string.
    """
    # Camel case to snake case: https://stackoverflow.com/a/1176023
    case_separator = "_"
    _string = string
    _string = re.sub("(.)([A-Z][a-z]+)", rf"\1{case_separator}\2", _string)
    _string = re.sub("__([A-Z])", rf"{case_separator}\1", _string)
    _string = re.sub("([a-z0-9])([A-Z])", rf"\1{case_separator}\2", _string)
    return _string.lower()


def camel_case_to_dash_case(string: str) -> str:
    """
    Convert a camel case string to a dash case string.

    Args:
        string: An input string.

    Returns:
        A dash case string.
    """
    # Camel case to snake case: https://stackoverflow.com/a/1176023
    case_separator = "-"
    _string = string
    _string = re.sub("(.)([A-Z][a-z]+)", rf"\1{case_separator}\2", _string)
    _string = re.sub("__([A-Z])", rf"{case_separator}\1", _string)
    _string = re.sub("([a-z0-9])([A-Z])", rf"\1{case_separator}\2", _string)
    return _string.lower()


@final
@unique
class CamelCase(Enum):
    """CamelCase options."""

    LOWER = auto()
    UPPER = auto()


def snake_case_to_camel_case(
    string: str, camel_case: CamelCase = CamelCase.UPPER
) -> str:
    """
    Convert a snake case string to a camel case string.

    Args:
        string: An input string.
        camel_case: Camel case type.

    Returns:
        A camel case string.
    """
    string_split = string.split("_")
    _string = ""
    _string = (
        string_split[0].capitalize()
        if camel_case is CamelCase.UPPER
        else string_split[0]
    )
    _string += "".join(word.capitalize() for word in string_split[1:])
    return _string


def snake_case_to_dash_case(string: str) -> str:
    """
    Convert a snake case string to a dash case string.

    Args:
        string: An input string.

    Returns:
        A dash case string.
    """
    return string.replace("_", "-")
