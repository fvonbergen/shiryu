"""template module."""

from pathlib import Path
from typing import Dict, List, Union

import jinja2

from ..shiryu import SHIRYU_PACKAGE_NAME, SHIRYU_PACKAGE_PATH

PACKAGE_NAME = "shiryu"
PACKAGE_TEMPLATES_PATH = Path("templates")


def get_jinja_environment(file_path: Path) -> jinja2.Environment:
    """
    Get jinja environment based on current file path.

    Args:
        file_path: Current file path.

    Returns:
        A jinja environment positioned on the current file path.
    """
    templates_file_path = file_path.parent
    if not templates_file_path.is_dir():
        exception_message = f"Inexistent templates file path: {templates_file_path}"
        raise Exception(exception_message)
    return jinja2.Environment(
        loader=jinja2.PackageLoader(
            SHIRYU_PACKAGE_NAME,
            package_path=str(templates_file_path.relative_to(SHIRYU_PACKAGE_PATH)),
        ),
        autoescape=jinja2.select_autoescape(),
    )


Mapping = Dict[str, Union[str, List[str]]]


class TemplateFile:
    """TemplateFile class."""

    def __init__(self, file_name: Path, output_directory: Path) -> None:
        """
        Class initializer.

        Args:
            file_name: File name.
            output_directory: Output directory.
        """
        self.__file_name = file_name
        self.__output_directory = output_directory

    @property
    def file_name(self) -> Path:
        """
        Get file name.

        Returns:
            File name.
        """
        return self.__file_name

    @property
    def output_directory(self) -> Path:
        """
        Get output directory.

        Returns:
            Output directory.
        """
        return self.__output_directory

    @property
    def output_path(self) -> Path:
        """
        Get output path.

        Returns:
            Output path.
        """
        return self.output_directory / self.file_name


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

        Rerurns:
            The template file.
        """
        return self.__template_file

    @property
    def contents(self) -> str:
        """
        Get file contents.

        Args:
            mapping: Template mapping.

        Returns:
            File contents.
        """
        jinja_template = self.__jinja_environment.get_template(
            f"{self.template_file.file_name}.template"
        )
        return jinja_template.render(**(self.__mapping))
