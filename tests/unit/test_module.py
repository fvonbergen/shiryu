"""test_module module."""

from pathlib import PurePath

import pytest

from shiryu.utils.module import path_to_module_str


def test_path_to_module_str() -> None:
    """Test path to module conversion."""
    path_module = PurePath()
    assert path_to_module_str(path_module) == "."
    assert path_to_module_str(path_module, False) == ""
    path_module = PurePath("shiryu")
    assert path_to_module_str(path_module) == ".shiryu"
    assert path_to_module_str(path_module, False) == "shiryu"
    path_module = PurePath("shiryu.py")
    assert path_to_module_str(path_module) == ".shiryu"
    path_module = PurePath("shiryu/SDK")
    assert path_to_module_str(path_module) == ".shiryu.SDK"
    assert path_to_module_str(path_module, False) == "shiryu.SDK"
    path_module = PurePath("shiryu/SDK.py")
    assert path_to_module_str(path_module) == ".shiryu.SDK"
    path_module = PurePath("/shiryu")
    with pytest.raises(ValueError, match=f"Path module {path_module} must be relative"):
        path_to_module_str(path_module)
