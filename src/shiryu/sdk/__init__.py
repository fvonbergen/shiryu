"""sdk subpackage."""

from enum import Enum
from importlib import import_module
from pathlib import Path
from typing import Final

from ..shiryu import SHIRYU_PACKAGE_PATH
from ..utils.enum import create_enum
from ..utils.module import path_to_module_str
from .common.module import SDKModule


def get_sub_directories(directory: Path, *, ignore: set[str] | None = None) -> set[Path]:
    """Get immediate sub-directories in directory.

    Args:
        directory: Root directory.
        ignore: Sub-directories to ignore.

    Returns:
        A set of sub-directories from root directory.

    Raises:
        NotADirectoryError: If the provided directory path does not exist or is not a directory.
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
    """Get SDK languages options.

    Returns:
        An enumeration with SDK options.
    """
    root_directory = Path(__file__).parent
    package = path_to_module_str(
        root_directory.relative_to(SHIRYU_PACKAGE_PATH.parent), is_package=False
    )
    sdk_enum_dict: dict[str, type[SDKModule]] = {}
    for sub_directory in get_sub_directories(root_directory, ignore={"__pycache__", "common"}):
        sdk_module = import_module(path_to_module_str(sub_directory), package=package)
        sdk_class: type[SDKModule] = sdk_module.SDKLanguage
        sdk_enum_dict[sub_directory.name.upper()] = sdk_class
    sdk_options = create_enum("SDKOptions", sdk_enum_dict, is_unique=True)
    sdk_options.__doc__ = """SDK options."""
    return sdk_options


SDKOptions: Final = __get_sdk_options()
