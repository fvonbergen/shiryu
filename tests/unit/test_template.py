"""test_template module."""

from pathlib import Path

from shiryu.utils.template import TemplateFile


def test_template_file() -> None:
    """Test the TemplateFile class."""
    file_name = Path("file_name")
    output_directory = Path("output_directory")
    template_file = TemplateFile(file_name, output_directory)
    assert (
        template_file.file_name == file_name
        and template_file.output_directory == output_directory
        and template_file.output_file_name == file_name
        and template_file.output_path == output_directory / file_name
    )
    output_file_name = Path("output_file_name")
    template_file = TemplateFile(file_name, output_directory, output_file_name)
    assert (
        template_file.file_name == file_name
        and template_file.output_directory == output_directory
        and template_file.output_file_name == output_file_name
        and template_file.output_path == output_directory / output_file_name
    )
