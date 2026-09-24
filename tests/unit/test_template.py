"""test_template module."""

from pathlib import Path, PurePosixPath

from shiryu.sdk.common.module import ProjectAuthor
from shiryu.sdk.python.context import DependencyGroups
from shiryu.sdk.python.templates import PYTHON_JINJA_ENVIRONMENT
from shiryu.utils.template import Template, TemplateFile


def test_template_file() -> None:
    """Test the TemplateFile class."""
    file_name = Path("file_name")
    output_directory = PurePosixPath("output_directory")
    template_file = TemplateFile(file_name, output_directory=output_directory)
    assert (
        template_file.file_name == file_name
        and template_file.output_directory == output_directory
        and template_file.output_file_name == file_name
        and template_file.output_path == output_directory / file_name
    )
    output_file_name = PurePosixPath("output_file_name")
    template_file = TemplateFile(
        file_name, output_directory=output_directory, output_file_name=output_file_name
    )
    assert (
        template_file.file_name == file_name
        and template_file.output_directory == output_directory
        and template_file.output_file_name == output_file_name
        and template_file.output_path == output_directory / output_file_name
    )


def test_pyproject_toml_multiple_authors() -> None:
    """Test rendering mulitple authors."""
    authors = frozenset({ProjectAuthor("Emma", "emma@sate.com"),
                         ProjectAuthor("Emma2", "emma2@sate.com")})
    content = Template(PYTHON_JINJA_ENVIRONMENT,
                       TemplateFile(Path("pyproject.toml")),
                       {
                           "project_name": "test",
                           "project_authors": authors,
                           "dependency_groups": DependencyGroups(),
                       }).contents

    assert content.index('name = "Emma"') < content.index('name = "Emma2"')

