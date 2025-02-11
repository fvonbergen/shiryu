"""build module."""

from pathlib import Path

import dagger

from ..common import PlatformType, ProjectProperties, ProjectType
from .base import PythonBase


class PythonBuild(PythonBase):
    """PythonBuild class."""

    @staticmethod
    def project_distributable_folder() -> str:
        """
        Get the project distributable folder.

        Returns:
            Project distributable folder.
        """
        return "dist"

    @classmethod
    def vcs_exclude_files_folders(cls) -> list[str]:
        """
        Files and folders to exclude from vcs.

        Returns:
            A list of files and folders to exclude from vcs.
        """
        vcs_exclude_files_folders = super(PythonBuild, cls).vcs_exclude_files_folders()
        return [*vcs_exclude_files_folders, f"/{cls.project_distributable_folder()}/"]

    @classmethod
    def project_distributable_path(cls) -> Path:
        """
        Get the project distributable path.

        Returns:
            Project distibutable path.
        """
        return cls.project_path() / cls.project_distributable_folder()

    @classmethod
    async def _pipeline(
        cls, project: ProjectType, platform: PlatformType
    ) -> tuple[dagger.Container, ProjectProperties]:
        """Build pipeline."""
        container, project_properties = await cls.python_env(project, platform)
        container = container.with_exec(["uv", "pip", "install", "build", "twine"])
        build_command = [
            "python",
            "-m",
            "build",
            "--installer=uv",
            f"--outdir={cls.project_distributable_path() / platform}",
        ]
        return (await container.with_exec(build_command).sync(), project_properties)

    @classmethod
    async def build(
        cls, project: ProjectType, platform: PlatformType
    ) -> dagger.Directory:
        """Run build in the project of the provided source Directory."""
        container, _ = await cls._pipeline(project, platform)
        return await container.directory(str(cls.project_path()))
