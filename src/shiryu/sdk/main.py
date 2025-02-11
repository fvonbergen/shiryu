"""main module."""

from pathlib import Path

import dagger


def get_sub_directories(directory: Path) -> list[Path]:
    """
    Get sub-directories in directory.

    Args:
        directory: Root directory.

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
            if sub_directory not in ["__pycache__", "common"]
        ]
    return []


def get_sdk_class() -> type[dagger.Enum]:
    """
    Get SDK enum class.

    Returns:
        SDK enum class.
    """
    sdk_enum_dict = {}
    for sdk_directory in get_sub_directories(Path(__file__).parent):
        sdk_directory_str = str(sdk_directory)
        sdk_enum_dict[sdk_directory_str.upper()] = (
            sdk_directory_str,
            f"{sdk_directory_str} value",
        )
    sdk_class = dagger.enum_type()(dagger.Enum("SDK", sdk_enum_dict))  # type: ignore[type-var]
    sdk_class.__doc__ = """SDK options."""
    return sdk_class  # type: ignore[return-value]


SDK = get_sdk_class()


def get_files(directory: Path) -> list[Path]:
    """
    Get directories in directory.

    Args:
        directory: Root directory.

    Returns:
        A list of nested directories from root directory.
    """
    if not directory.is_dir():
        exception_message = f"Invalid directory: {directory}"
        raise Exception(exception_message)
    for _, _, sdk_files in directory.walk():
        return [Path(sdk_file) for sdk_file in sdk_files]
    return []


def path_to_module_str(path_module: Path, is_package: bool = True) -> str:
    """
    Convert path to module string.

    Args:
        path_module: Module path.
        is_package: Whether import is from current package or external.

    Returns:
        Convert path to module string.
    """
    # if not path_module.is_absolute():
    #    exception_message = f"Path module must be relative: {path_module}"
    #    raise Exception(exception_message)
    module_parts = list(path_module.parts)
    # Remove .py extension if present.
    if module_parts[-1].endswith(".py"):
        module_parts[-1] = module_parts[-1][:-3]
    module_path = ".".join(module_parts)
    if is_package:
        module_path = f".{module_path}"
    return module_path
