"""test_case module."""

from shiryu.utils.case import (
    CamelCase,
    camel_case_to_dash_case,
    camel_case_to_snake_case,
    snake_case_to_camel_case,
    snake_case_to_dash_case,
)


def __camel_case_to_snake_or_dash_case_test_examples(
    separator: str,
) -> set[tuple[str, str]]:
    """
    Build camel case to snake or dash case test examples.

    Args:
        separator: Snake or dash case separator.

    Returns:
        Camel case to snake or dash case test examples.
    """
    return {
        ("a", "a"),
        ("aa", "aa"),
        ("aA", f"a{separator}a"),
        ("aaa", "aaa"),
        ("aAa", f"a{separator}aa"),
        ("aaA", f"aa{separator}a"),
        ("aAA", f"a{separator}aa"),
        ("A", "a"),
        ("Aa", "aa"),
        ("AA", "aa"),
        ("Aaa", "aaa"),
        ("AAa", f"a{separator}aa"),
        ("AaA", f"aa{separator}a"),
        ("AAA", "aaa"),
    }


def __snake_or_dash_case_to_camel_case_test_examples(
    separator: str, camel_case: CamelCase
) -> set[tuple[str, str]]:
    """
    Build snake or dash case to camel case test examples.

    Args:
        separator: Snake or dash case separator.
        camel_case: Test examples for the camel case type.

    Returns:
        Snake or dash case to camel case test examples.
    """
    test_examples = set()
    if camel_case is CamelCase.LOWER:
        # Commented cases are not possible.
        test_examples.update(
            {
                ("a", "a"),
                ("aa", "aa"),
                (f"a{separator}a", "aA"),
                ("aaa", "aaa"),
                (f"a{separator}aa", "aAa"),
                (f"aa{separator}a", "aaA"),
                # (f"a{separator}aa", "aAA"),
            }
        )
    elif camel_case is CamelCase.UPPER:
        # Commented cases are not possible.
        test_examples.update(
            {
                ("a", "A"),
                ("aa", "Aa"),
                # ("aa", "AA"),
                # ("aaa", "Aaa"),
                (f"a{separator}aa", "AAa"),
                (f"aa{separator}a", "AaA"),
                # ("aaa", "AAA"),
            }
        )
    else:
        exception_message = f"Invalid camel case {camel_case}"
        raise AssertionError(exception_message)
    return test_examples


def __snake_case_to_dash_case_test_examples() -> set[tuple[str, str]]:
    """
    Build snake case to dash case test examples.

    Returns:
        Snake case to dash case test examples.
    """
    return {
        ("a", "a"),
        ("aa", "aa"),
        ("a_a", "a-a"),
        ("aaa", "aaa"),
        ("a_aa", "a-aa"),
        ("aa_a", "aa-a"),
        ("a_a_a", "a-a-a"),
    }


def test_camel_case_to_snake_case() -> None:
    """Test camel case to snake case conversion."""
    snake_case_separator = "_"
    for test_example in __camel_case_to_snake_or_dash_case_test_examples(
        snake_case_separator
    ):
        assert camel_case_to_snake_case(test_example[0]) == test_example[1], (
            f"Test example: {test_example}"
        )


def test_camel_case_to_dash_case() -> None:
    """Test camel case to dash case conversion."""
    dash_case_separator = "-"
    for test_example in __camel_case_to_snake_or_dash_case_test_examples(
        dash_case_separator
    ):
        assert camel_case_to_dash_case(test_example[0]) == test_example[1], (
            f"Test example: {test_example}"
        )


def test_snake_case_to_camel_case() -> None:
    """Test snake case to camel case conversion."""
    snake_case_separator = "_"
    camel_case = CamelCase.LOWER
    for test_example in __snake_or_dash_case_to_camel_case_test_examples(
        snake_case_separator, camel_case
    ):
        assert (
            snake_case_to_camel_case(test_example[0], camel_case) == test_example[1]
        ), f"Test example: {test_example}"

    camel_case = CamelCase.UPPER
    for test_example in __snake_or_dash_case_to_camel_case_test_examples(
        snake_case_separator, camel_case
    ):
        assert (
            snake_case_to_camel_case(test_example[0], camel_case) == test_example[1]
        ), f"Test example: {test_example}"


def test_snake_case_to_dash_case() -> None:
    """Test snake case to dash case conversion."""
    for test_example in __snake_case_to_dash_case_test_examples():
        assert snake_case_to_dash_case(test_example[0]) == test_example[1], (
            f"Test example: {test_example}"
        )
