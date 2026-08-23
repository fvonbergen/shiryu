"""test_case module."""

from shiryu.utils.case import CamelCase, to_camel_case, to_kebab_case, to_snake_case


def __any_case_to_snake_or_kebab_case_test_examples(separator: str) -> set[tuple[str, str]]:
    """Build input to snake or kebab case test examples.

    Args:
        separator: Snake (_) or kebab (-) case separator.

    Returns:
        Any case to snake or kebab case test examples.
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


def __any_case_to_camel_case_test_examples(
    separator: str, camel_case: CamelCase
) -> set[tuple[str, str]]:
    """Build input case to camel or Pascal case test examples.

    Args:
        separator: Separator character (e.g., '_' or '-').
        camel_case: Test examples for the camel case type.

    Returns:
        Input case to camel or Pascal case test examples.

    Raises:
        AssertionError: If an invalid CamelCase enum value is passed.
    """
    test_examples = set()
    if camel_case is CamelCase.LOWER:
        test_examples.update(
            {
                ("a", "a"),
                ("aa", "aa"),
                (f"a{separator}a", "aA"),
                ("aaa", "aaa"),
                (f"a{separator}aa", "aAa"),
                (f"aa{separator}a", "aaA"),
            }
        )
    elif camel_case is CamelCase.UPPER:
        test_examples.update(
            {("a", "A"), ("aa", "Aa"), (f"a{separator}aa", "AAa"), (f"aa{separator}a", "AaA")}
        )
    else:
        exception_message = f"Invalid camel case {camel_case}"
        raise AssertionError(exception_message)
    return test_examples


def __snake_to_kebab_case_test_examples() -> set[tuple[str, str]]:
    """Build snake case to kebab case test examples.

    Returns:
        Snake case to kebab case test examples.
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


def test_to_snake_case() -> None:
    """Test string conversion to snake_case."""
    snake_case_separator = "_"
    for test_example in __any_case_to_snake_or_kebab_case_test_examples(snake_case_separator):
        assert to_snake_case(test_example[0]) == test_example[1], (
            f"Test example failed: {test_example}"
        )


def test_to_kebab_case() -> None:
    """Test string conversion to kebab-case."""
    kebab_case_separator = "-"
    for test_example in __any_case_to_snake_or_kebab_case_test_examples(kebab_case_separator):
        assert to_kebab_case(test_example[0]) == test_example[1], (
            f"Test example failed: {test_example}"
        )

    for test_example in __snake_to_kebab_case_test_examples():
        assert to_kebab_case(test_example[0]) == test_example[1], (
            f"Test example failed: {test_example}"
        )


def test_to_camel_case() -> None:
    """Test string conversion to lower camelCase and PascalCase (UPPER)."""
    snake_case_separator = "_"

    camel_case = CamelCase.LOWER
    for test_example in __any_case_to_camel_case_test_examples(snake_case_separator, camel_case):
        assert to_camel_case(test_example[0], camel_case=camel_case) == test_example[1], (
            f"Test example failed: {test_example}"
        )

    camel_case = CamelCase.UPPER
    for test_example in __any_case_to_camel_case_test_examples(snake_case_separator, camel_case):
        assert to_camel_case(test_example[0], camel_case=camel_case) == test_example[1], (
            f"Test example failed: {test_example}"
        )
