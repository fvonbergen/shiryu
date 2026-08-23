"""module module."""

from pathlib import PurePath


def path_to_module_str(path_module: PurePath, *, is_package: bool = True) -> str:
    """Convert path to module string.

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
    # .parts gives us everything, but we want to drop the .py extension from the last item
    # stem extracts the filename without extension (e.g. 'utils' instead of 'utils.py')
    module_parts = list(path_module.parent.parts)
    if path_module.name:
        module_parts.append(path_module.stem)
    # Filter out empty strings if path was '.'
    module_parts = [
        module_part for module_part in module_parts if module_part and module_part != "."
    ]
    module_path = ".".join(module_parts)
    if is_package:
        module_path = f".{module_path}"
    return module_path
