"""file module."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Self, final

from dagger_clients.core import File, core

from ..template import Template


@final
@dataclass(frozen=True, slots=True)
class TargetFile:
    """Immutable file paired with its target output directory.

    Attributes:
        file: File object to be written.
        output_directory: Target directory path for the file.
    """

    file: File
    output_path: PurePosixPath

    @classmethod
    def from_template(cls, template: Template) -> Self:
        """Build an instance from a template.

        Args:
            template: Source template.

        Returns:
            A new instance containing the initialized file and output directory.
        """
        template_file = template.template_file
        file_obj = core().file(
            str(template_file.output_file_name), template.contents, permissions=0o644
        )
        return cls(file=file_obj, output_path=template_file.output_path)
