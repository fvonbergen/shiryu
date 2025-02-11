"""sdk subpackage."""

from enum import Enum, unique
from importlib import import_module
from pathlib import Path
from typing import Final

from ..shiryu import SHIRYU_PACKAGE_PATH
from ..utils.module import path_to_module_str
from .common.module import SDK


def get_sub_directories(directory: Path, ignore: list[str] | None = None) -> list[Path]:
    """
    Get sub-directories in directory.

    Args:
        directory: Root directory.
        ignore: Subdirectories to ignore.

    Returns:
        A list of sub-directories from root directory.
    """
    if not directory.is_dir():
        exception_message = f"Invalid directory: {directory}"
        raise Exception(exception_message)
    for _, sub_directories, _ in directory.walk():
        return [
            Path(sub_directory)
            for sub_directory in sub_directories
            if ignore is None or sub_directory not in ignore
        ]
    return []


def __get_sdk_options() -> type[Enum]:
    """
    Get SDK languages options.

    Returns:
        An enumeration with SDK options.
    """
    root_directory = Path(__file__).parent
    sdk_enum_dict: dict[str, SDK] = {}
    for sub_directory in get_sub_directories(root_directory, ["__pycache__", "common"]):
        sub_directory_str = str(sub_directory)
        sdk_module = import_module(
            path_to_module_str(sub_directory),
            package=path_to_module_str(
                root_directory.relative_to(SHIRYU_PACKAGE_PATH.parent), False
            ),
        )
        sdk_class: SDK = sdk_module.SDKLanguage
        sdk_enum_dict[sub_directory_str.upper()] = sdk_class
    sdk_options = unique(Enum("SDKOptions", sdk_enum_dict))  # type: ignore[type-var]
    sdk_options.__doc__ = """SDK options."""
    # mypy bug: https://github.com/python/mypy/issues/17147
    return sdk_options  # type: ignore[return-value]


SDKOptions: Final = __get_sdk_options()
