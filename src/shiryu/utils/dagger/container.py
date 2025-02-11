"""container module."""

import asyncio
import logging
from pathlib import Path

import dagger

from ..template import Template, TemplateFile

logger = logging.getLogger(__name__)


class FSDirectory:
    """FSDirectory class."""

    @classmethod
    async def from_container(
        cls, path: Path, container: dagger.Container
    ) -> "FSDirectory":
        """
        Build FSDirectory from a container.

        Args:
            path: Path directory.
            container: Dagger container.

        Returns:
            A file system directory.
        """
        path_str = str(path)
        if not await container.exists(
            path_str, expected_type=dagger.ExistsType.DIRECTORY_TYPE
        ):
            container = container.with_exec(["mkdir", "--parents", path_str])
        return cls(path, container.directory(path_str))

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
    return await fs_directory.directory.exists(
        str(template_file.output_file_name),
        expected_type=dagger.ExistsType.REGULAR_TYPE,
    )


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
        await FSDirectory.from_container(template_file.output_directory, container),
        template_file,
    )


# async def directory_with_file(
#    fs_directory: FSDirectory, template: Template
# ) -> FSDirectory:
#    """
#    Directory with file. If it already exists it doesn't modify it.
#
#    Args:
#        fs_directory: File system directory.
#        template: Template.
#
#    Returns:
#        The file system directory with file.
#    """
#    is_write = not await is_directory_with_file(fs_directory, template.template_file)
#    return (
#        FSDirectory(
#            fs_directory.path,
#            fs_directory.directory.with_new_file(
#                path=str(
#                    template.template_file.output_path.relative_to(fs_directory.path)
#                ),
#                contents=template.contents,
#            ),
#        )
#        if is_write
#        else fs_directory
#    )


async def container_with_files(
    container: dagger.Container, templates: tuple[Template, ...], is_overwrite: bool
) -> dagger.Container:
    """
    Container with files. If file already exists it doesn't modify it.

    Args:
        container: Dagger container.
        templates: Templates.
        is_overwrite: Whether to overwrite files or not.

    Returns:
        The dagger container with files.
    """
    is_not_writes_tasks = tuple(
        is_container_with_file(container, template.template_file)
        for template in templates
    )
    is_not_writes = await asyncio.gather(*is_not_writes_tasks)
    for template, is_not_write in zip(templates, is_not_writes, strict=True):
        if is_overwrite or not is_not_write:
            container = container.with_new_file(
                path=str(template.template_file.output_path),
                contents=template.contents,
            )
    return container
