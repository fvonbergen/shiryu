"""function module."""

from collections.abc import Callable
from enum import Enum
from pathlib import Path
from types import FunctionType
from typing import Self
from urllib.parse import unquote, urlparse

import dagger
from dagger_clients.core import Directory, Workspace

SourceType = Directory
ProjectNameType = str


@dagger.object_type
class DaggerBase:
    """DaggerBase class."""

    source: SourceType
    project_name: ProjectNameType

    @classmethod
    async def create(cls, ws: Workspace) -> Self:
        """
        Dagger factory class method.

        Args:
            ws: Dagger auto-populates it from the current workspace. The caller passes nothing for
                it, and no project files are uploaded up front. The module pulls only the paths it
                asks for.

        Returns:
            An instance built with `cls(...)`.
        """
        workspace_address_uri = await ws.address()
        project_name = Path(unquote(urlparse(workspace_address_uri).path)).name
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
            ),
            project_name=project_name,
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
                return enum_option.value(source=self.source, project_name=self.project_name)

            __enum_value_template.__name__ = enum_option.name.lower()
            __enum_value_template.__doc__ = enum_option.value.__doc__
            __enum_value_template.__annotations__ = {"self": cls, "return": enum_option.value}
            return __enum_value_template

        for enum_option in enum_options:
            enum_value_template = lambda_enum_value_template(enum_option)
            setattr(cls, enum_value_template.__name__, dagger.function(enum_value_template))

        return cls

    return __add_enum_values
