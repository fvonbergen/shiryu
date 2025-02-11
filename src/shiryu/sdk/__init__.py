"""sdk subpackage."""

from importlib import import_module
from pathlib import Path

import dagger

from ..shiryu import SHIRYU_PACKAGE_PATH
from .common import SDK, SDKInterface
from .main import get_sub_directories, path_to_module_str

SDKDict = dict[dagger.Enum, type[SDKInterface]]


def get_sdk_languages() -> SDKDict:
    """
    Get SDK languages dictionary.

    Returns:
        A dictionary with SDK languages.
    """
    sdk_languages: SDKDict = {}
    root_directory = Path(__file__).parent
    for sub_directory in get_sub_directories(root_directory):
        sub_directory_str = str(sub_directory)
        module = import_module(
            path_to_module_str(sub_directory),
            package=path_to_module_str(
                root_directory.relative_to(SHIRYU_PACKAGE_PATH.parent), False
            ),
        )
        sdk_class = getattr(
            module,
            "".join(char for char in sub_directory_str.title() if not char.isspace()),
        )
        sdk_languages[SDK(sub_directory_str)] = sdk_class
    return sdk_languages
