"""case module."""

import re
from enum import Enum, auto, unique
from typing import final


@final
@unique
class CamelCase(Enum):
    """CamelCase options for controlling casing variant."""

    LOWER = auto()  # e.g., camelCase
    UPPER = auto()  # e.g., PascalCase


def _split_into_words(string: str) -> list[str]:
    """
    Internal helper to split any string identifier into separate word tokens.

    Args:
        string: The raw input string to split into words.

    Returns:
        A list of lower-level word tokens extracted from the input string.
    """
    # Handle acronyms and consecutive capitals (e.g., "HTTPRequest" -> "HTTP_Request")
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", string)
    # Handle camelCase transitions (e.g., "camelCase" -> "camel_Case")
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    # Replace non-alphanumeric characters with underscores
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s)
    # Tokenize by underscores
    return [word for word in s.split("_") if word]


def to_kebab_case(string: str) -> str:
    """
    Convert any string identifier (snake, camel, Pascal, space-separated) to kebab-case.

    Args:
        string: An input string.

    Returns:
        A kebab-case string (e.g., "lint-code").
    """
    words = _split_into_words(string)
    return "-".join(words).lower()


def to_snake_case(string: str) -> str:
    """
    Convert any string identifier (camel, Pascal, kebab, space-separated) to snake_case.

    Args:
        string: An input string.

    Returns:
        A snake_case string (e.g., "lint_code").
    """
    words = _split_into_words(string)
    return "_".join(words).lower()


def to_camel_case(string: str, *, camel_case: CamelCase = CamelCase.UPPER) -> str:
    """
    Convert any string identifier to a camelCase or PascalCase string.

    Args:
        string: An input string.
        camel_case: The camel case variant to produce.

    Returns:
        A camelCase or PascalCase string.
    """
    words = _split_into_words(string)
    if not words:
        return ""

    first_word = words[0].capitalize() if camel_case is CamelCase.UPPER else words[0].lower()
    rest = "".join(word.capitalize() for word in words[1:])
    return first_word + rest
