"""function module."""

from collections.abc import Callable
from enum import Enum
from typing import final

import dagger

# Generic class type.
type ClassType = type
type EnumValueType = type


def add_enum_values_as_methods(
    enum_options: type[Enum],
) -> Callable[[ClassType], ClassType]:
    """
    Add enum values as dagger class methods to class decorator wrapper.

    Args:
        enum_options: Enum options.

    Returns:
        Decorator that adds enum values as dagger class methods to class.
    """

    def __add_enum_values(cls: ClassType) -> ClassType:
        """
        Add enum values as dagger class methods to class decorator.

        Args:
            cls: Class.

        Returns:
            Decorated class.
        """

        def lambda_enum_value_template(
            enum_option: Enum,
        ) -> Callable[[], EnumValueType]:
            """
            Lambda enum value template.

            Args:
                enum_option: Enum option.

            Returns:
                Enum value method.
            """

            def __enum_value_template() -> EnumValueType:
                """
                Enum value method.

                Returns:
                    Enum value class.
                """
                return enum_option.value

            __enum_value_template.__name__ = enum_option.name.lower()
            __enum_value_template.__doc__ = enum_option.value.__doc__
            __enum_value_template.__annotations__ = {"return": enum_option.value}
            return __enum_value_template

        for enum_option in enum_options:
            enum_value_template = lambda_enum_value_template(enum_option)
            setattr(
                cls,
                enum_value_template.__name__,
                final(staticmethod(dagger.function(enum_value_template))),
            )

        return cls

    return __add_enum_values
