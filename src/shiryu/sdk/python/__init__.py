"""python subpackage."""

from typing import Final

from ...utils.case import snake_case_to_camel_case
from ..common.module import get_sdk_language
from .module import MODULE_NAME, PythonModule
from .modules import sdk_modules

SDKLanguage: Final = get_sdk_language(
    snake_case_to_camel_case(MODULE_NAME), PythonModule, sdk_modules
)
