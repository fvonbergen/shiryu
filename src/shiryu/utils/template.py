"""template module."""

from pathlib import Path, PurePosixPath
from typing import Any, Final, final

import jinja2

from ..shiryu import SHIRYU_PACKAGE_NAME, SHIRYU_PACKAGE_PATH

PACKAGE_NAME: Final = "shiryu"
PACKAGE_TEMPLATES_PATH: Final = Path("templates")
TEMPLATE_FILE_SUFFIX: Final = "jinja2"


def get_jinja_environment(file_path: Path) -> jinja2.Environment:
    """
    Get jinja environment based on current file path.

    Args:
        file_path: Current file path.

    Returns:
        A jinja environment positioned on the current file path.

    Raises:
        NotADirectoryError: If the parent directory of file_path does not exist or is not a
            directory.
        ValueError: If templates_file_path is not located within SHIRYU_PACKAGE_PATH.
        jinja2.TemplateError: If Jinja fail to initialize the environment or PackageLoader.
    """
    templates_file_path = file_path.parent
    if not templates_file_path.is_dir():
        exception_message = f"Inexistent templates file path: {templates_file_path}"
        raise NotADirectoryError(exception_message)
    return jinja2.Environment(
        loader=jinja2.PackageLoader(
            SHIRYU_PACKAGE_NAME,
            package_path=str(templates_file_path.relative_to(SHIRYU_PACKAGE_PATH)),
        ),
        autoescape=jinja2.select_autoescape(),
    )


Mapping = dict[str, Any]


@final
class TemplateFile:
    """TemplateFile class."""

    def __init__(
        self,
        file_name: Path,
        output_directory: PurePosixPath | None = None,
        output_file_name: PurePosixPath | None = None,
    ) -> None:
        """
        Class initializer.

        Args:
            file_name: Template file name.
            output_directory: Output directory.
            output_file_name: Alternative output file name.
        """
        self.__file_name = file_name
        self.__output_directory = output_directory if output_directory else PurePosixPath()
        self.__output_file_name = output_file_name if output_file_name else PurePosixPath(file_name)

    @property
    def file_name(self) -> Path:
        """
        Get file name.

        Returns:
            File name.
        """
        return self.__file_name

    @property
    def output_directory(self) -> PurePosixPath:
        """
        Get output directory.

        Returns:
            Output directory.
        """
        return self.__output_directory

    @property
    def output_file_name(self) -> PurePosixPath:
        """
        Get output file name.

        Returns:
            Output file name.
        """
        return self.__output_file_name

    @property
    def output_path(self) -> PurePosixPath:
        """
        Get output path.

        Returns:
            Output path.
        """
        return self.output_directory / self.output_file_name


@final
class Template:
    """Template class."""

    def __init__(
        self,
        jinja_environment: jinja2.Environment,
        template_file: TemplateFile,
        mapping: Mapping,
    ) -> None:
        """
        Class initializer.

        Args:
            jinja_environment: Jinja environment.
            template_file: Template file.
            mapping: Default template mapping.
        """
        self.__jinja_environment = jinja_environment
        self.__template_file = template_file
        self.__mapping = mapping

    @property
    def template_file(self) -> TemplateFile:
        """
        Get template file.

        Returns:
            The template file.
        """
        return self.__template_file

    @property
    def contents(self) -> str:
        """
        Get file contents.

        Returns:
            File contents.
        """
        jinja_template = self.__jinja_environment.get_template(
            f"{self.template_file.file_name}.{TEMPLATE_FILE_SUFFIX}"
        )
        return jinja_template.render(**(self.__mapping))
