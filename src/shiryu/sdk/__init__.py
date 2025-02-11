"""sdk subpackage."""

from enum import Enum, unique
from importlib import import_module
from pathlib import Path
from typing import Final, final

from ..shiryu import SHIRYU_PACKAGE_PATH
from ..utils.module import path_to_module_str
from .common.module import SDK


def get_sub_directories(directory: Path, ignore: set[str] | None = None) -> set[Path]:
    """
    Get immediate sub-directories in directory.

    Args:
        directory: Root directory.
        ignore: Sub-directories to ignore.

    Returns:
        A set of sub-directories from root directory.
    """
    if not directory.is_dir():
        exception_message = f"Invalid directory: {directory}"
        raise NotADirectoryError(exception_message)
    _ignore = ignore or set()
    return {
        # .relative_to(directory) strips the absolute /src/.../ path prefix off
        path.relative_to(directory)
        for path in directory.iterdir()
        if path.is_dir() and path.name not in _ignore
    }


def __get_sdk_options() -> type[Enum]:
    """
    Get SDK languages options.

    Returns:
        An enumeration with SDK options.
    """
    root_directory = Path(__file__).parent
    package = path_to_module_str(
        root_directory.relative_to(SHIRYU_PACKAGE_PATH.parent), False
    )
    sdk_enum_dict: dict[str, type[SDK]] = {}
    for sub_directory in get_sub_directories(root_directory, {"__pycache__", "common"}):
        sdk_module = import_module(path_to_module_str(sub_directory), package=package)
        sdk_class: type[SDK] = sdk_module.SDKLanguage
        sdk_enum_dict[sub_directory.name.upper()] = sdk_class
    sdk_options = final(unique(Enum("SDKOptions", sdk_enum_dict)))  # type: ignore[type-var]
    sdk_options.__doc__ = """SDK options."""
    # mypy bug: https://github.com/python/mypy/issues/17147
    return sdk_options  # type: ignore[return-value]


SDKOptions: Final = __get_sdk_options()
