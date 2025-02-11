"""dagger module."""

import logging
from pathlib import Path

import dagger

from .template import Template, TemplateFile

logger = logging.getLogger(__name__)


class FSDirectory:
    """FSDirectory class."""

    @classmethod
    def from_container(cls, path: Path, container: dagger.Container) -> "FSDirectory":
        """
        Build FSDirectory from a container.

        Args:
            path: Path directory.
            container: Dagger container.

        Returns:
            A file system directory.
        """
        path_str = str(path)
        return cls(
            path,
            container.with_exec(["mkdir", "--parents", path_str]).directory(path_str),
        )

    def __init__(self, path: Path, directory: dagger.Directory) -> None:
        """
        Class initializer.

        Args:
            path: Directory path.
            directory: Dagger directory.
        """
        self._path = path
        self._directory = directory

    @property
    def path(self) -> Path:
        """
        Get directory path.

        Returns:
            Directory path.
        """
        return self._path

    @property
    def directory(self) -> dagger.Directory:
        """
        Get dagger directory.

        Returns:
            Dagger directory.
        """
        return self._directory

    def with_new_directory(self, path: Path) -> "FSDirectory":
        """
        File system directory with new directory.

        Returns:
            File system directory with new directory.
        """
        return FSDirectory(
            self.path,
            self.directory.with_new_directory(
                str(path.relative_to(self.path)), permissions=0o755
            ),
        )

    def with_directory(self, fs_directory: "FSDirectory") -> "FSDirectory":
        """
        File system directory merged with file system directory.

        Returns:
            File system directory merged with file system directory.
        """
        return FSDirectory(
            self.path,
            self.directory.with_directory(
                str(fs_directory.path.relative_to(self.path)), fs_directory.directory
            ),
        )


# TODO: Function can also match directories with the same name.
async def is_directory_with_file(
    fs_directory: FSDirectory, template_file: TemplateFile
) -> bool:
    """
    Whether directory has the file or not.

    Args:
        fs_directory: File system directory.
        template_file: File template.

    Returns:
        Whether the directory has the file or not.
    """
    return str(template_file.file_name) in await fs_directory.directory.entries()


async def is_container_with_file(
    container: dagger.Container, template_file: TemplateFile
) -> bool:
    """
    Whether container has the file or not.

    Args:
        container: Dagger container.
        template_file: File template.

    Returns:
        Whether the container has the file or not.
    """
    return await is_directory_with_file(
        FSDirectory.from_container(template_file.output_directory, container),
        template_file,
    )


async def directory_with_file(
    fs_directory: FSDirectory, template: Template
) -> FSDirectory:
    """
    Directory with file. If it already exists it doesn't modify it.

    Args:
        fs_directory: File system directory.
        template: Template.

    Returns:
        The file system directory with file.
    """
    is_write = not await is_directory_with_file(fs_directory, template.template_file)
    return (
        FSDirectory(
            fs_directory.path,
            fs_directory.directory.with_new_file(
                path=str(
                    template.template_file.output_path.relative_to(fs_directory.path)
                ),
                contents=template.contents,
            ),
        )
        if is_write
        else fs_directory
    )


async def container_with_file(
    container: dagger.Container, template: Template
) -> dagger.Container:
    """
    Container with file. If it already exists it doesn't modify it.

    Args:
        container: Dagger container.
        template: Template.

    Returns:
        The dagger container with file.
    """
    is_write = not await is_container_with_file(container, template.template_file)
    return (
        container.with_new_file(
            path=str(template.template_file.output_path),
            contents=template.contents,
        )
        if is_write
        else container
    )
