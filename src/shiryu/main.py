"""main module."""

from typing import final

import dagger

from .sdk import SDKOptions
from .utils.dagger.function import DaggerBase, add_enum_values_as_methods


@dagger.object_type
@final
@add_enum_values_as_methods(SDKOptions)
class Shiryu(DaggerBase):
    """Shiryu class."""
