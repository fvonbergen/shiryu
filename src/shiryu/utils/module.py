"""module module."""

from pathlib import Path


def path_to_module_str(path_module: Path, is_package: bool = True) -> str:
    """
    Convert path to module string.

    Args:
        path_module: Module path.
        is_package: Whether import is from current package or external.

    Returns:
        Convert path to module string.

    Raises:
        ValueError: If `path_module` is an absolute path instead of being a relative path.
    """
    if path_module.is_absolute():
        exception_message = f"Path module {path_module} must be relative"
        raise ValueError(exception_message)
    module_parts = list(path_module.parts)
    # Remove .py extension if present.
    if module_parts[-1].endswith(".py"):
        module_parts[-1] = module_parts[-1][:-3]
    module_path = ".".join(module_parts)
    if is_package:
        module_path = f".{module_path}"
    return module_path
