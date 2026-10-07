"""function module."""

from collections.abc import Callable
from enum import Enum
from types import FunctionType
from typing import Self

import dagger

SourceType = dagger.Directory


@dagger.object_type
class DaggerBase:
    """DaggerBase class."""

    source: SourceType

    @classmethod
    def create(cls, ws: dagger.Workspace) -> Self:
        """
        Dagger factory class method.

        Args:
            ws: Dagger auto-populates it from the current workspace. The caller passes nothing for
                it, and no project files are uploaded up front. The module pulls only the paths it
                asks for.

        Returns:
            An instance built with `cls(...)`.
        """
        return cls(
            source=ws.directory(
                "/",
                # exclude=[
                #     "**/.dagger",
                #     "**/.git",
                #     "**/.venv",
                #     "**/__pycache__",
                #     "**/node_modules",
                #     "**/dist",
                # ],
                gitignore=True,
            )
        )


# Generic class type.
type EnumValueType = type


def add_enum_values_as_methods(
    enum_options: type[Enum],
) -> Callable[[type[DaggerBase]], type[DaggerBase]]:
    """Add enum values as dagger class methods to class decorator wrapper.

    Args:
        enum_options: Enum options.

    Returns:
        Decorator that adds enum values as dagger class methods to class.
    """

    def __add_enum_values(cls: type[DaggerBase]) -> type[DaggerBase]:
        """Add enum values as dagger class methods to class decorator.

        Args:
            cls: Class type.

        Returns:
            Decorated class.
        """

        def lambda_enum_value_template(enum_option: Enum) -> FunctionType:
            """Lambda enum value template.

            Args:
                enum_option: Enum option.

            Returns:
                Enum value method.
            """

            def __enum_value_template(self: DaggerBase) -> EnumValueType:
                """Enum value method.

                Returns:
                    Enum value class.
                """
                return enum_option.value(source=self.source)

            __enum_value_template.__name__ = enum_option.name.lower()
            __enum_value_template.__doc__ = enum_option.value.__doc__
            __enum_value_template.__annotations__ = {"self": cls, "return": enum_option.value}
            return __enum_value_template

        for enum_option in enum_options:
            enum_value_template = lambda_enum_value_template(enum_option)
            setattr(cls, enum_value_template.__name__, dagger.function(enum_value_template))

        return cls

    return __add_enum_values
