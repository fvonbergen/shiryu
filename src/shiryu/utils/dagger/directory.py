"""directory module."""

from dagger_clients.core import Directory

from ..template import Template


def directory_with_new_file(directory: Directory, template: Template) -> Directory:
    """Return the input directory with the template file.

    Args:
        directory: Input directory.
        template: Template.

    Returns:
        The input directory with the template file.
    """
    return directory.with_new_file(str(template.template_file.output_path), template.contents)
