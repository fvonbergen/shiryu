"""main module."""

from typing import final

import dagger

from .sdk import SDKOptions
from .utils.dagger.function import add_enum_values_as_methods


@final
@dagger.object_type
@add_enum_values_as_methods(SDKOptions)
class Shiryu:
    """Shiryu class."""
