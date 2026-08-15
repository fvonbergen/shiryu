"""modules subpackage."""

from importlib import import_module
from pathlib import Path
from typing import Final

from ....shiryu import SHIRYU_PACKAGE_PATH
from ....utils.module import path_to_module_str
from ...common.module import SDKModule


def get_files(directory: Path, *, ignore: list[str] | None = None) -> list[Path]:
    """
    Get files in directory.

    Args:
        directory: Root directory.
        ignore: Files to ignore.

    Returns:
        A list of files in root directory.

    Raises:
        NotADirectoryError: If the provided directory path does not exist or is not a directory.
    """
    if not directory.is_dir():
        exception_message = f"Invalid directory: {directory}"
        raise NotADirectoryError(exception_message)
    for _, _, sdk_files in directory.walk():
        return [
            Path(sdk_file) for sdk_file in sdk_files if ignore is None or sdk_file not in ignore
        ]
    return []


def __get_sdk_module_modules() -> set[type[SDKModule]]:
    """
    Get SDK module modules.

    Returns:
        SDK module modules.
    """
    file = Path(__file__)
    root_directory = file.parent
    sdk_module_modules_paths = get_files(file.parent, ignore=[file.name])
    sdk_module_modules: set[type[SDKModule]] = set()
    for sdk_module_module_path in sdk_module_modules_paths:
        sdk_module_module = import_module(
            path_to_module_str(sdk_module_module_path),
            package=path_to_module_str(
                root_directory.relative_to(SHIRYU_PACKAGE_PATH.parent), is_package=False
            ),
        )
        sdk_module_modules.add(sdk_module_module.sdk_module)
    return sdk_module_modules


sdk_module_modules: Final = __get_sdk_module_modules()
