"""lint module."""

from pathlib import Path

import dagger

from ...utils.dagger import container_with_file
from ...utils.template import Mapping, Template, TemplateFile
from ..common import PlatformType, ProjectNameType, ProjectType
from .base import PythonBase
from .templates import PYTHON_JINJA_ENVIRONMENT


class PythonLint(PythonBase):
    """PythonLint class."""

    @staticmethod
    def cache_folder() -> str:
        """
        Get the linter cache folder.

        Returns:
            The linter cache folder.
        """
        return ".ruff_cache"

    @classmethod
    def vcs_exclude_files_folders(cls) -> list[str]:
        """
        Files and folders to exclude from vcs.

        Returns:
            A list of files and folders to exclude from vcs.
        """
        vcs_exclude_files_folders = super(PythonLint, cls).vcs_exclude_files_folders()
        return [*vcs_exclude_files_folders, f"/{cls.cache_folder()}/"]

    @classmethod
    def __ruff_toml_template_file(cls) -> TemplateFile:
        """pyproject.toml template file."""
        return TemplateFile(Path("ruff.toml"), cls.project_path())

    @classmethod
    async def _init(
        cls, container: dagger.Container, project_name: ProjectNameType
    ) -> dagger.Container:
        """
        Get a container that has an initialized project.

        Args:
            container: Container to initialize.
            project_name: The project name.

        Returns:
            A container with an initialized project.
        """
        container = await super(PythonLint, cls)._init(container, project_name)
        # ruff.toml
        ruff_toml_template_mapping: Mapping = {"cache_folder": cls.cache_folder()}
        ruff_toml_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls.__ruff_toml_template_file(),
            ruff_toml_template_mapping,
        )
        return await container_with_file(container, ruff_toml_template)

    @classmethod
    async def __pipeline(
        cls, project: ProjectType, platform: PlatformType, fix: bool
    ) -> dagger.Container:
        """
        Lint pipeline.

        Args:
            project: Project directory.
            platform: The container platform.
            fix: Whether to fix the project files or not.

        Returns:
            A container with the project lint command executed.
        """
        container, project_properties = await cls.python_env(project, platform)
        container = await PythonLint._init(container, project_properties["name"])
        ruff_toml_file_name = cls.__ruff_toml_template_file().file_name
        ruff_check_command = [
            "ruff",
            "check",
            "--show-fixes",
            f"--config={ruff_toml_file_name}",
            ".",
        ]
        ruff_format_command = ["ruff", "format", f"--config={ruff_toml_file_name}", "."]
        if fix:
            ruff_check_command = [*ruff_check_command, "--fix"]
        else:
            ruff_format_command = [*ruff_format_command, "--diff"]
        container = container.with_exec(["uv", "pip", "install", "ruff"])
        return await (
            container.with_exec(ruff_check_command)
            .with_exec(ruff_format_command)
            .sync()
        )

    @classmethod
    async def lint(cls, project: ProjectType, platform: PlatformType) -> str:
        """Run lint checks in the project of the provided source Directory."""
        await cls.__pipeline(project, platform, True)
        return "Lint successfull"

    @classmethod
    async def lint_fix(
        cls, project: ProjectType, platform: PlatformType
    ) -> dagger.Directory:
        """Run lint fixes in the project of the provided source Directory."""
        container = await cls.__pipeline(project, platform, True)
        return await container.directory(str(cls.project_path()))
