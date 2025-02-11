"""common subpackage."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Annotated, TypedDict

import dagger

from ...utils.dagger import container_with_file
from ...utils.template import Mapping, Template, TemplateFile
from ..main import SDK
from .templates import COMMON_JINJA_ENVIRONMENT

ProjectType = Annotated[
    dagger.Directory, dagger.Doc("Project location"), dagger.DefaultPath(".")
]
PlatformType = Annotated[
    str, dagger.Doc("Platform config OS and architecture in a Container")
]
PLATFORM_DEFAULT = "linux/amd64"

LanguageType = Annotated[
    SDK, dagger.Doc("Software Development Kit programming language")  # type: ignore[valid-type]
]

LANGUAGE_DEFAULT = SDK("python")

ProjectNameType = Annotated[str, dagger.Doc("Project name")]


class ProjectProperties(TypedDict):
    """ProjectProperties class."""

    name: ProjectNameType
    version: str


class SDKBase:
    """SDKBase class."""

    @staticmethod
    def project_path() -> Path:
        """
        Get the container project path.

        Returns:
            The container project path.
        """
        return Path("/project")

    @staticmethod
    def source_folder() -> str:
        """
        Get the source folder name.

        Returns:
            The source folder name.
        """
        return "src"

    @classmethod
    def project_source_path(cls) -> Path:
        """
        Get the container project source path.

        Returns:
            The container project source path.
        """
        return cls.project_path() / cls.source_folder()

    @classmethod
    def vcs_exclude_files_folders(cls) -> list[str]:
        """
        Files and folders to exclude from vcs.

        Returns:
            A list of files and folders to exclude from vcs.
        """
        return []

    @classmethod
    def github_actions_jobs(cls) -> list[Template]:
        """
        Get the github actions jobs files.

        Returns:
            A list of github actions job files
        """
        return []

    @classmethod
    def project_env(cls, platform: PlatformType) -> dagger.Container:
        """
        Get a container with the project environment set.

        Args:
            platform: The container platform.

        Returns:
            A container with the project environment set.
        """
        project_path_str = str(cls.project_path())
        apt_install = ("apt", "install", "--assume-yes", "--no-install-recommends")
        base_packages = ("git",)
        return (
            dagger.dag.container(platform=dagger.Platform(platform))
            .from_("debian:trixie-slim")
            .with_exec(["mkdir", "--parents", project_path_str])
            .with_exec(["apt", "update"])
            .with_exec([*apt_install, *base_packages])
            .with_exec(["apt", "autoremove"])
            .with_exec(["apt", "clean"])
            .with_workdir(project_path_str)
        )

    @classmethod
    async def _init(
        cls,
        container: dagger.Container,
        project_name: ProjectNameType,
    ) -> dagger.Container:
        """
        Get a container that has an initialized project.

        Args:
            container: Container to initialize.
            project_name: The project name.

        Returns:
            A container with an initialized project.
        """
        # README.md
        readme_md_template_mapping: Mapping = {
            "project_name": project_name.capitalize()
        }
        readme_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(Path("README.md"), cls.project_path()),
            readme_md_template_mapping,
        )
        container = await container_with_file(container, readme_md_template)
        # CHANGELOG.md
        changelog_md_template_mapping: Mapping = {}
        changelog_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(Path("CHANGELOG.md"), cls.project_path()),
            changelog_md_template_mapping,
        )
        container = await container_with_file(container, changelog_md_template)
        # .gitignore
        project_source_path_str = str(cls.project_source_path())
        _gitignore_template_mapping: Mapping = {
            "exclude": cls.vcs_exclude_files_folders()
        }
        _gitignore_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(Path(".gitignore"), cls.project_path()),
            _gitignore_template_mapping,
        )
        container = container.with_exec(
            ["git", "init", "--initial-branch", "main"]
        ).with_exec(["mkdir", "--parents", project_source_path_str])
        return await container_with_file(container, _gitignore_template)


class SDKInterface(ABC):
    """SDKInterface class."""

    @classmethod
    @abstractmethod
    async def build(
        cls, project: ProjectType, platform: PlatformType
    ) -> dagger.Directory:
        """Run build in the project of the provided source Directory."""
        ...

    @classmethod
    @abstractmethod
    async def check(cls, project: ProjectType, platform: PlatformType) -> str:
        """Run type checks in the project of the provided source Directory."""
        ...

    @classmethod
    @abstractmethod
    async def lint(cls, project: ProjectType, platform: PlatformType) -> str:
        """Run lint checks in the project of the provided source Directory."""
        ...

    @classmethod
    @abstractmethod
    async def lint_fix(
        cls, project: ProjectType, platform: PlatformType
    ) -> dagger.Directory:
        """Run lint fixes in the project of the provided source Directory."""
        ...

    @classmethod
    @abstractmethod
    async def test_install(cls, project: ProjectType, platform: PlatformType) -> str:
        """Test the project installation process."""
        ...

    @classmethod
    @abstractmethod
    async def init(
        cls,
        project_name: ProjectNameType,
        platform: PlatformType,
    ) -> dagger.Directory:
        """Returns a directory with a new project initialized."""
        ...
