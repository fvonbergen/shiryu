"""template module."""

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Final, final

import jinja2

from ..shiryu import SHIRYU_PACKAGE_NAME, SHIRYU_PACKAGE_PATH

PACKAGE_NAME: Final = "shiryu"
PACKAGE_TEMPLATES_PATH: Final = Path("templates")
TEMPLATE_FILE_SUFFIX: Final = "jinja2"


def get_jinja_environment(file_path: Path) -> jinja2.Environment:
    """Get jinja environment based on current file path.

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
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined,
    )


@final
@dataclass(frozen=True, slots=True)
class TemplateFile:
    """TemplateFile class."""

    file_name: Path
    output_directory: PurePosixPath = field(default_factory=PurePosixPath, kw_only=True)
    output_file_name: PurePosixPath = field(default_factory=PurePosixPath, kw_only=True)

    def __post_init__(self) -> None:
        """Normalize default output paths."""
        if self.output_file_name == PurePosixPath():
            object.__setattr__(self, "output_file_name", PurePosixPath(self.file_name))

    @property
    def output_path(self) -> PurePosixPath:
        """Get output path.

        Returns:
            Output path.
        """
        return self.output_directory / self.output_file_name


Mapping = dict[str, Any]


@final
@dataclass(frozen=True, slots=True)
class Template:
    """Template class."""

    jinja_environment: jinja2.Environment = field(repr=False)
    template_file: TemplateFile
    # TODO: we should replace Mapping with a hashable solution
    mapping: Mapping = field(hash=False)

    @property
    def contents(self) -> str:
        """Get file contents.

        Returns:
            File contents.
        """
        jinja_template = self.jinja_environment.get_template(
            f"{self.template_file.file_name}.{TEMPLATE_FILE_SUFFIX}"
        )
        return jinja_template.render(**self.mapping)
