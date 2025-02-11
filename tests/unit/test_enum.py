"""test_enum module."""

from enum import Enum

from shiryu.utils.enum import get_enum_elements, get_enum_keys, get_enum_values


class SubEnum(Enum):
    """SubEnum options."""

    KEY_1 = "value_1"
    KEY_2 = "value_2"


def test_get_enum_keys() -> None:
    """Test enumeration keys getter."""
    assert get_enum_keys(SubEnum) == {"KEY_1", "KEY_2"}


def test_get_enum_values() -> None:
    """Test enumeration values getter."""
    assert get_enum_values(SubEnum) == {"value_1", "value_2"}


def test_get_enum_elements() -> None:
    """Test enumeration elements getter."""
    assert get_enum_elements(SubEnum) == {SubEnum.KEY_1, SubEnum.KEY_2}
