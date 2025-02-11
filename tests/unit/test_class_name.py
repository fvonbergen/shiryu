"""test_class_name module."""

from shiryu.utils.class_name import ClassName


class SubClassName(ClassName):
    """SubClassName class."""


def test_class_name() -> None:
    """Test ClassName class."""
    assert ClassName.name() == "class_name"
    assert SubClassName.name() == "sub_class_name"
