"""test_module module."""

from pathlib import Path

import pytest

from shiryu.utils.module import path_to_module_str


def test_path_to_module_str() -> None:
    """Test path to module conversion."""
    path_module = Path("shiryu")
    assert path_to_module_str(path_module) == ".shiryu"
    path_module = Path("shiryu.py")
    assert path_to_module_str(path_module) == ".shiryu"
    path_module = Path("shiryu")
    assert path_to_module_str(path_module, False) == "shiryu"
    path_module = Path("shiryu/SDK")
    assert path_to_module_str(path_module) == ".shiryu.SDK"
    path_module = Path("shiryu/SDK.py")
    assert path_to_module_str(path_module) == ".shiryu.SDK"
    path_module = Path("shiryu/SDK")
    assert path_to_module_str(path_module, False) == "shiryu.SDK"
    path_module = Path("/shiryu")
    with pytest.raises(ValueError, match=f"Path module {path_module} must be relative"):
        path_to_module_str(path_module)
