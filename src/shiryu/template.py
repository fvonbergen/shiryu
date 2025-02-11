"""template module."""

from pathlib import Path
from typing import Dict, List, Union

import jinja2

PACKAGE_NAME = "shiryu"
PACKAGE_TEMPLATES_PATH = Path("templates")

jinja_environment = jinja2.Environment(
    loader=jinja2.PackageLoader(PACKAGE_NAME, package_path=str(PACKAGE_TEMPLATES_PATH)),
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
        self._file_name = file_name
        self._output_directory = output_directory

    @property
    def file_name(self) -> Path:
        """
        Get file name.

        Returns:
            File name.
        """
        return self._file_name

    @property
    def output_directory(self) -> Path:
        """
        Get output directory.

        Returns:
            Output directory.
        """
        return self._output_directory

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

    def __init__(self, template_file: TemplateFile, mapping: Mapping) -> None:
        """
        Class initializer.

        Args:
            template_file: Template file.
            mapping: Default template mapping.
        """
        self._template_file = template_file
        self._mapping = mapping

    @property
    def template_file(self) -> TemplateFile:
        """
        Get template file.

        Rerurns:
            The template file.
        """
        return self._template_file

    @property
    def contents(self) -> str:
        """
        Get file contents.

        Args:
            mapping: Template mapping.

        Returns:
            File contents.
        """
        jinja_template = jinja_environment.get_template(
            f"{self.template_file.file_name}.template"
        )
        return jinja_template.render(**(self._mapping))
