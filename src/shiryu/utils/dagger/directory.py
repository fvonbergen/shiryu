"""directory module."""

import dagger

from ..template import Template


def directory_with_new_file(directory: dagger.Directory, template: Template) -> dagger.Directory:
    """Return the input directory with the template file.

    Args:
        directory: Input directory.
        template: Template.

    Returns:
        The input directory with the template file.
    """
    return directory.with_new_file(str(template.template_file.output_path), template.contents)
