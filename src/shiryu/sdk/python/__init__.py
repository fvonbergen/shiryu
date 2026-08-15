"""python subpackage."""

from typing import Final

from ..common.module import get_sdk_language
from .module import PythonModule
from .modules import sdk_module_modules

SDKLanguage: Final = get_sdk_language(PythonModule, sdk_module_modules)
