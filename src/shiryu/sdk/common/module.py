"""module package."""

import asyncio
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath
from typing import Annotated, Final, final

import dagger
from dagger_clients.core import Changeset, Container, Directory, ExistsType, Platform, core
from packaging.version import Version

from ...utils.class_name import ClassName
from ...utils.dagger.client import container_git
from ...utils.dagger.directory import directory_with_new_file
from ...utils.dagger.file import TargetFile
from ...utils.dagger.function import ProjectNameType, SourceType, add_enum_values_as_methods
from ...utils.enum import create_enum
from ...utils.template import Mapping, Template, TemplateFile
from .context import (
    DaggerModuleMetadata,
    SDKModuleInitContextContainer,
    SDKModuleInitContextDirectory,
    SDKModuleInitContextDirectoryScm,
    SDKModuleInitContextDirectoryVcs,
)
from .scm import GITLAB_FOLDER, GITLAB_JOBS_FOLDER, SCM, GitLabJob, github_init, gitlab_init
from .templates import COMMON_JINJA_ENVIRONMENT
from .vcs import VCS_PRIMARY_BRANCH, VCS_USER_EMAIL_DEFAULT, VCS_USER_NAME_DEFAULT

logger = logging.getLogger(__name__)


def warning(message: str) -> None:
    """Helper function to print a formatted warning to stderr.

    Args:
        message: Warning message.
    """
    print(message, file=sys.stderr)


# PINNED: gitlab docker version (2026/11/22)
GITLAB_DOCKER_VERSION: Final = Version("29.10.0")
PROJECT_VERSION_DEFAULT: Final = "0.0.0"
OptionalProjectNameType = ProjectNameType | None
OptionalProjectNameDaggerType = Annotated[OptionalProjectNameType, dagger.Doc("Project name")]
OPTIONAL_PROJECT_NAME_DAGGER_DEFAULT: Final = None
# dagger_clients.core.Platform is built with: <os>/<platform_variant>
# opencontainers image spec documentation: https://github.com/opencontainers/image-spec/blob/main/image-index.md#image-index-property-descriptions
# Go Language documentation:
# - GOOS/GOARCH: https://go.dev/doc/install/source#environment
PlatformType = Platform
PlatformDaggerType = Annotated[
    PlatformType, dagger.Doc("Platform config OS and architecture in a Container")
]
PLATFORM_DAGGER_DEFAULT: Final = Platform("linux/amd64")
IsUpdateType = bool
IsUpdateDaggerType = Annotated[
    IsUpdateType, dagger.Doc("Whether to update project directory files or not")
]
IS_UPDATE_DAGGER_DEFAULT: Final = False
SCMType = list[SCM]
SCMDaggerType = Annotated[
    SCMType, dagger.Doc("Project Source Code Management (SCM) list to be targeted or configured")
]
SCM_DAGGER_DEFAULT: Final = [SCM.GITLAB]


@final
@dataclass(frozen=True, slots=True)
class ProjectAuthor:
    """ProjectAuthor."""

    name: str = field(default=VCS_USER_NAME_DEFAULT, kw_only=True)
    email: str = field(default=VCS_USER_EMAIL_DEFAULT, kw_only=True)


@final
@dataclass(frozen=True, slots=True)
class ProjectMetadata:
    """ProjectMetadata class."""

    name: str
    version: str
    authors: frozenset[ProjectAuthor]


class SDKModuleInitializer[SDKModuleInitContextDirectoryType: SDKModuleInitContextDirectory](ABC):
    """SDKModuleInitializer class."""

    @classmethod
    @abstractmethod
    def _create_init_context_directory(cls) -> SDKModuleInitContextDirectoryType:
        """Create an initialization context.

        Returns:
            An initialization context.
        """
        ...

    @classmethod
    def _init_context_directory(
        cls,
        init_context_directory: SDKModuleInitContextDirectoryType,
        shiryu_metadata: DaggerModuleMetadata,
        project_metadata: ProjectMetadata,
    ) -> SDKModuleInitContextDirectoryType:
        """Initialization directory context used in the SDK module directory initialization.

        Args:
            init_context_directory: SDK module initialization directory context.
            shiryu_metadata: Shiryu metadata.
            project_metadata: Project metadata.

        Returns:
            The updated SDK module initialization directory context.
        """
        dagger_name = "dagger"
        job_name = f".{dagger_name}"
        dagger_yml_template_mapping: Mapping = {
            "docker_version": str(GITLAB_DOCKER_VERSION),
            "dagger_version": str(shiryu_metadata.dagger_version),
        }
        dagger_yml_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path(f"{job_name}.yml"),
                output_directory=PurePosixPath(GITLAB_FOLDER) / GITLAB_JOBS_FOLDER,
            ),
            dagger_yml_template_mapping,
        )
        dagger_job = GitLabJob(dagger_name, job_name, dagger_yml_template, ())
        return init_context_directory.evolve(
            scm=init_context_directory.scm.evolve(
                gitlab_jobs_stages=init_context_directory.scm.gitlab_jobs_stages.evolve(
                    jobs=init_context_directory.scm.gitlab_jobs_stages.jobs | {dagger_job}
                )
            )
        )

    @final
    @classmethod
    async def __vcs_init(
        cls,
        project_authors: frozenset[ProjectAuthor],
        init_context_vcs: SDKModuleInitContextDirectoryVcs,
        directory: Directory,
        platform: PlatformType,
        container_security_audit_file: TargetFile,
    ) -> Directory:
        """Initialize the directory with the VCS folders and files.

        Args:
            project_authors: Project authors.
            init_context_vcs: SDK module initialization directory VCS context.
            directory: A directory to VCS initialize.
            platform: The container platform used for initialization.
            container_security_audit_file: Container security audit file.

        Returns:
            Returns a directory with the VCS folders and files.
        """
        _project_authors = sorted(project_authors, key=lambda author: author.name)
        project_author = _project_authors[0] if len(_project_authors) else ProjectAuthor()
        _directory = (
            (await container_git(platform, container_security_audit_file))
            .with_directory(".", directory)
            .with_exec(["git", "init", "--initial-branch", VCS_PRIMARY_BRANCH])
            .with_exec(["git", "config", "user.name", project_author.name])
            .with_exec(["git", "config", "user.email", project_author.email])
            .directory(".")
        )
        # .gitignore
        _gitignore_template_mapping: Mapping = {
            "exclude": sorted(init_context_vcs.exclude_files_folders)
        }
        _gitignore_template = Template(
            COMMON_JINJA_ENVIRONMENT, TemplateFile(Path(".gitignore")), _gitignore_template_mapping
        )
        return directory_with_new_file(_directory, _gitignore_template)

    @final
    @staticmethod
    def __scm_init(
        directory: Directory,
        init_context_directory_scm: SDKModuleInitContextDirectoryScm,
        scm: SCMType,
    ) -> Directory:
        """Initialize the directory with the SCM's files and folders.

        Args:
            directory: A directory to SCM initialize.
            init_context_directory_scm: SDK module initialization SCM directory context.
            scm: Project Source Code Management (SCM) list to be targeted or configured.

        Returns:
            Returns a directory with the SCM's initialized.
        """
        if len(scm):
            if SCM.GITHUB in scm:
                directory = github_init(
                    directory, init_context_directory_scm.github_actions_workflows
                )
            if SCM.GITLAB in scm:
                directory = gitlab_init(directory, init_context_directory_scm.gitlab_jobs_stages)
        return directory

    @final
    @classmethod
    def _readme_md_template_file(cls) -> TemplateFile:
        """README.md template file.

        Returns:
            The README.md template file.
        """
        return TemplateFile(Path("README.md"))

    @final
    @classmethod
    def _readme_md_template(cls, project_name: ProjectNameType) -> Template:
        """README.md template.

        Args:
            project_name: Project name.

        Returns:
            The README.md template.
        """
        readme_md_template_mapping: Mapping = {"project_name": project_name.capitalize()}
        return Template(
            COMMON_JINJA_ENVIRONMENT, cls._readme_md_template_file(), readme_md_template_mapping
        )

    @final
    @classmethod
    def _license_template_file(cls) -> TemplateFile:
        """LICENSE template file.

        Returns:
            The LICENSE template file.
        """
        # License file names must be SPDX compliant.
        # https://spdx.dev/learn/handling-license-info/
        return TemplateFile(Path("Apache-2.0"), output_file_name=PurePosixPath("LICENSE"))

    @final
    @classmethod
    def _trivyignore_template_file(cls) -> TemplateFile:
        """.trivyignore template file.

        Returns:
            The .trivyignore template file.
        """
        return TemplateFile(Path(".trivyignore.shiryu"))

    @final
    @classmethod
    def _trivyignore_template(cls) -> Template:
        """.trivyignore template.

        Returns:
            The .trivyignore template.
        """
        _trivyignore_template_mapping: Mapping = {}
        return Template(
            COMMON_JINJA_ENVIRONMENT,
            cls._trivyignore_template_file(),
            _trivyignore_template_mapping,
        )

    @classmethod
    async def _init_directory(  # noqa: PLR0913, PLR0917
        cls,
        init_directory: Directory,
        init_context_directory: SDKModuleInitContextDirectoryType,
        project_metadata: ProjectMetadata,
        scm: SCMType,
        platform: PlatformType,
        container_security_audit_file: TargetFile,
    ) -> Directory:
        """Build the initialization directory.

        Args:
            init_directory: The dagger directory to initialize.
            init_context_directory: SDK module initialization directory context.
            project_metadata: Project metadata.
            scm: Project Source Code Management (SCM) list to be targeted or configured.
            platform: The container platform used for initialization.
            container_security_audit_file: Container security audit file.

        Returns:
            The initialization directory.
        """
        directory = init_directory
        directory = await cls.__vcs_init(
            project_metadata.authors,
            init_context_directory.vcs,
            directory,
            platform,
            container_security_audit_file,
        )
        # README.md
        readme_md_template = cls._readme_md_template(project_metadata.name)
        directory = directory_with_new_file(directory, readme_md_template)
        # LICENSE
        license_template_mapping: Mapping = {}
        license_template = Template(
            COMMON_JINJA_ENVIRONMENT, cls._license_template_file(), license_template_mapping
        )
        directory = directory_with_new_file(directory, license_template)
        # CHANGELOG.md
        changelog_md_template_mapping: Mapping = {}
        changelog_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(Path("CHANGELOG.md")),
            changelog_md_template_mapping,
        )
        directory = directory_with_new_file(directory, changelog_md_template)
        directory = cls.__scm_init(directory, init_context_directory.scm, scm)
        return directory


@dataclass
class SDKModule[
    SDKModuleInitializerType: SDKModuleInitializer,
    SDKModuleInitContextContainerType: SDKModuleInitContextContainer,
](ABC, ClassName):
    """SDKModule class."""

    source: SourceType
    project_name: ProjectNameType

    @staticmethod
    @abstractmethod
    def _sdk_name() -> str:
        """Get the SDK name.

        Returns:
            The SDK name.
        """
        ...

    @staticmethod
    @abstractmethod
    def _initializer_cls() -> type[SDKModuleInitializerType]:
        """Initializer class.

        Returns:
            The initializer class.
        """
        ...

    @final
    @staticmethod
    async def __get_module_tag_or_branch(
        platform: PlatformType, container_security_audit_file: TargetFile, module_source: Directory
    ) -> str:
        """Get the exact Git tag or current branch name for the module source.

        Args:
            platform: The target platform type.
            container_security_audit_file: Container security audit file.
            module_source: The directory containing the module source.

        Returns:
            The exact Git tag if available, otherwise the current branch name.
        """
        container = (await container_git(platform, container_security_audit_file)).with_directory(
            ".", module_source
        )
        try:
            return (
                await container.with_exec(["git", "describe", "--tags", "--exact-match"]).stdout()
            ).strip()
        except dagger.QueryError:
            return (
                await container.with_exec(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout()
            ).strip()

    @final
    @classmethod
    async def __get_shiryu_metadata(
        cls, platform: PlatformType, container_security_audit_file: TargetFile
    ) -> DaggerModuleMetadata:
        """Returns shiryu metadata.

        Args:
            platform: The container platform used for initialization.
            container_security_audit_file: Container security audit file.

        Returns:
            Shiryu metadata.
        """
        # Get module exact git tag. Falls back to the branch name if the commit is not tagged.
        try:
            # TODO: it seems that something changed again and the module source is not returning
            # with the .git/ folder so no git information is retrieved.
            # TODO: read class ModuleSource in the sdk code
            module_source = core().current_module().source()
            dagger_engine_version, git_tag_or_branch = await asyncio.gather(
                module_source.as_module_source().engine_version(),
                cls.__get_module_tag_or_branch(
                    platform, container_security_audit_file, module_source
                ),
            )
            return DaggerModuleMetadata(
                dagger_version=Version(dagger_engine_version),
                git_tag_or_branch=git_tag_or_branch,
            )
        except dagger.QueryError:
            # TODO: https://github.com/dagger/dagger/issues/13054
            # TODO: the try-exception block is necessary because dagger.dag.current_module() fails
            # in dagger-in-dagger used in our tester unit module call with a QueryError
            # TODO: we must get somehow the sdk/entrypoint/dang.toml
            # TODO: I will pick the latest version
            # PINNED: dagger engine version (2026/11/25)
            dagger_version = Version("v1.0.0-beta.29")
            git_tag_or_branch = "undefined"
            return DaggerModuleMetadata(
                dagger_version=dagger_version, git_tag_or_branch=git_tag_or_branch
            )

    @classmethod
    @abstractmethod
    async def _get_project_metadata(
        cls,
        source: SourceType,
        project_name: ProjectNameType,
        platform: PlatformType,
        container_security_audit_file: TargetFile,
    ) -> ProjectMetadata:
        """Get project metadata.

        Warning: It depends on the generated project files.

        Args:
            source: Project source directory.
            project_name: Project name.
            platform: The container platform.
            container_security_audit_file: Container security audit file.

        Returns:
            The project metadata.
        """
        project_author = ProjectAuthor()
        project_container = (
            await container_git(platform, container_security_audit_file)
        ).with_directory(".", source)
        try:
            project_author_name = (
                await project_container.with_exec(["git", "config", "user.name"]).stdout()
            ).strip()
            project_author = replace(project_author, name=project_author_name)
        except dagger.QueryError:
            ...
        try:
            project_author_email = (
                await project_container.with_exec(["git", "config", "user.email"]).stdout()
            ).strip()
            project_author = replace(project_author, email=project_author_email)
        except dagger.QueryError:
            ...
        return ProjectMetadata(project_name, PROJECT_VERSION_DEFAULT, frozenset({project_author}))

    @final
    @classmethod
    async def _get_metadata(
        cls,
        source: SourceType,
        project_name: ProjectNameType,
        platform: PlatformType,
        container_security_audit_file: TargetFile,
    ) -> tuple[DaggerModuleMetadata, ProjectMetadata]:
        """Helper function to return metadata for the SDK module and project.

        Args:
            source: Project source directory.
            project_name: Project name.
            platform: The container platform.
            container_security_audit_file: Container security audit file.

        Returns:
            The shiryu module and project metadata.
        """
        shiryu_metadata, project_metadata = await asyncio.gather(
            cls.__get_shiryu_metadata(platform, container_security_audit_file),
            cls._get_project_metadata(
                source, project_name, platform, container_security_audit_file
            ),
        )
        return (shiryu_metadata, project_metadata)

    @final
    @classmethod
    async def __is_vcs_init(
        cls, source: SourceType, platform: PlatformType, container_security_audit_file: TargetFile
    ) -> bool:
        """Whether the dagger directory is initialized or not.

        Args:
            source: The project source directory.
            platform: The container platform used for initialization.
            container_security_audit_file: Container security audit file.

        Returns:
            `True` if directory is git initialized, `False` otherwise.
        """
        is_vcs_init: bool
        try:
            await (
                (await container_git(platform, container_security_audit_file))
                .with_directory(".", source)
                .with_exec(["git", "rev-parse", "--is-inside-work-tree"])
                .sync()
            )
            is_vcs_init = True
        except dagger.QueryError:
            is_vcs_init = False
        return is_vcs_init

    @final
    @classmethod
    async def __build_init_directory(
        cls,
        shiryu_metadata: DaggerModuleMetadata,
        project_metadata: ProjectMetadata,
        scm: SCMType,
        platform: PlatformType,
        container_security_audit_file: TargetFile,
    ) -> Directory:
        """Returns a SDK module initialized directory.

        Args:
            shiryu_metadata: Shiryu metadata.
            project_metadata: Project metadata.
            scm: Project Source Code Management (SCM) list to be targeted or configured.
            platform: The container platform.
            container_security_audit_file: Container security audit file.

        Returns:
            A SDK module initialized directory.
        """
        # Build the initialization context directory.
        initializer_cls = cls._initializer_cls()
        init_context_directory = initializer_cls._create_init_context_directory()
        init_context_directory = initializer_cls._init_context_directory(
            init_context_directory, shiryu_metadata, project_metadata
        )
        # Build initialized directory.
        init_directory = core().directory()
        return await initializer_cls._init_directory(
            init_directory,
            init_context_directory,
            project_metadata,
            scm,
            platform,
            container_security_audit_file,
        )

    @final
    @classmethod
    async def __build_output_directory(
        cls,
        init_directory: Directory,
        source: SourceType,
        is_update: IsUpdateType,
        platform: PlatformType,
        container_security_audit_file: TargetFile,
    ) -> Changeset:
        """Returns a project output directory merged with the SDK module initialized directory.

        Args:
            init_directory: SDK module initialization directory.
            source: Project source directory.
            is_update: Whether to update project directory files or not.
            platform: The container platform.
            container_security_audit_file: Container security audit file.

        Returns:
            A project directory merged with the SDK module initialized directory.
        """
        # Check if project is git initialized.
        is_vcs_init = await cls.__is_vcs_init(source, platform, container_security_audit_file)
        # Merge directories.
        vcs_excludes = [".git/"] if is_vcs_init else []
        init_directory_filtered = init_directory.filter(exclude=vcs_excludes)
        changeset = (
            source.with_directory(".", init_directory_filtered)
            if is_update
            else init_directory_filtered.with_directory(".", source)
        ).changes(source)
        return changeset

    @final
    @classmethod
    async def _container_security_audit_file(cls, source: SourceType) -> TargetFile:
        """Get the container security audit file.

        Args:
            source: Project source directory.

        Returns:
            The container security audit file.
        """
        initializer_cls = cls._initializer_cls()
        _trivyignore_template = initializer_cls._trivyignore_template()
        _trivyignore_output_path = _trivyignore_template.template_file.output_path
        _trivyignore_output_path_str = str(_trivyignore_output_path)

        return (
            TargetFile(source.file(_trivyignore_output_path_str), _trivyignore_output_path)
            if await source.exists(
                _trivyignore_output_path_str, expected_type=ExistsType.REGULAR_TYPE
            )
            else TargetFile.from_template(_trivyignore_template)
        )

    async def _init(
        self,
        project_name: OptionalProjectNameType,
        is_update: IsUpdateType,
        scm: SCMType,
        platform: PlatformType,
    ) -> Changeset:
        """Returns a changeset to initialize a project with the SDK module directory.

        Args:
            project_name: Project name.
            is_update: Whether to update project directory files or not.
            scm: Project Source Code Management (SCM) list to be targeted or configured.
            platform: The container platform.

        Returns:
            A changeset to initialize a project with the SDK module directory.
        """
        source = self.source
        _project_name = self.project_name if project_name is None else project_name
        container_security_audit_file = await self._container_security_audit_file(source)
        # Gather metadata.
        shiryu_metadata, project_metadata = await self._get_metadata(
            source, _project_name, platform, container_security_audit_file
        )
        # Build an initialized directory.
        init_directory = await self.__build_init_directory(
            shiryu_metadata, project_metadata, scm, platform, container_security_audit_file
        )
        # Merge the SDK module initialized directory with the project output directory.
        return await self.__build_output_directory(
            init_directory, source, is_update, platform, container_security_audit_file
        )

    @dagger.function(
        doc="Returns a changeset to initialize a project with the SDK module directory."
    )
    async def init(
        self,
        *,
        project_name: OptionalProjectNameDaggerType = OPTIONAL_PROJECT_NAME_DAGGER_DEFAULT,
        is_update: IsUpdateDaggerType = IS_UPDATE_DAGGER_DEFAULT,
        scm: SCMDaggerType = SCM_DAGGER_DEFAULT,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> Changeset:
        """Returns a changeset to initialize a project with the SDK module directory.

        Args:
            project_name: Project name.
            is_update: Whether to update project directory files or not.
            scm: Project Source Code Management (SCM) list to be targeted or configured.
            platform: The container platform.

        Returns:
            A changeset to initialize a project with the SDK module directory.
        """
        return await self._init(project_name, is_update, scm, platform)

    @classmethod
    @abstractmethod
    def _create_init_context_container(cls) -> SDKModuleInitContextContainerType:
        """Create an initialization context container.

        Returns:
            An initialization context container.
        """
        ...

    @classmethod
    def _init_context_container(
        cls, init_context_container: SDKModuleInitContextContainerType
    ) -> SDKModuleInitContextContainerType:
        """Initialization container context used in the SDK module container initialization.

        Args:
            init_context_container: SDK module initialization container context.

        Returns:
            The updated SDK module initialization container context.
        """
        return init_context_container.evolve(
            container_packages=init_context_container.container_packages | {"git"}
        )

    @classmethod
    @abstractmethod
    async def _dependencies_security_audit_file(cls, source: SourceType) -> TargetFile:
        """Get the project dependencies security audit file.

        Args:
            source: Project source directory.

        Returns:
            The project dependencies security audit file.
        """
        ...

    @classmethod
    @abstractmethod
    async def _base_container(
        cls,
        init_context_container: SDKModuleInitContextContainerType,
        platform: PlatformType,
        container_security_audit_file: TargetFile,
        dependencies_security_audit_file: TargetFile,
    ) -> Container:
        """Base container.

        Args:
            init_context_container: SDK module initialization container context.
            platform: The container platform.
            container_security_audit_file: Container security audit file.
            dependencies_security_audit_file: Project dependencies security audit file.

        Returns:
            A base container.
        """
        ...

    @final
    @classmethod
    async def _init_container(
        cls,
        init_context_container: SDKModuleInitContextContainerType,
        source: SourceType,
        exclude: list[str],
        platform: PlatformType,
    ) -> Container:
        """Helper function to return an initialized container for the SDK module.

        Args:
            init_context_container: SDK module initialization container context.
            source: Project source directory.
            exclude: Exclude source files and folders.
            platform: The container platform.

        Returns:
            An initialized container for the SDK module.
        """
        container_security_audit_file, dependencies_security_audit_file = await asyncio.gather(
            cls._container_security_audit_file(source),
            cls._dependencies_security_audit_file(source),
        )
        return (
            await cls._base_container(
                init_context_container,
                platform,
                container_security_audit_file,
                dependencies_security_audit_file,
            )
        ).with_directory(".", source, exclude=exclude)

    @final
    async def _exec_container(
        self, source: SourceType, exclude: list[str], platform: PlatformType
    ) -> Container:
        """Helper function to return an initialized container for the SDK module.

        Args:
            source: Project source directory.
            exclude: Exclude source files and folders.
            platform: The container platform.

        Returns:
            An initialized container for the SDK module.
        """
        init_context_container = self._create_init_context_container()
        init_context_container = self._init_context_container(init_context_container)
        return await self._init_container(init_context_container, source, exclude, platform)


def get_sdk_language(
    sdk_module: type[SDKModule], sdk_module_modules: set[type[SDKModule]]
) -> type[SDKModule]:
    """Get SDK language.

    Args:
        sdk_module: SDK module.
        sdk_module_modules: SDK modules.

    Returns:
        A SDK Language class.
    """
    sdk_module_options_dict: dict[str, type[SDKModule]] = {}
    sdk_module_initializer_classes: list[type[SDKModuleInitializer]] = []
    for sdk_module_module in sdk_module_modules:
        sdk_module_initializer_classes.insert(0, sdk_module_module._initializer_cls())
        sdk_module_options_dict[sdk_module_module.name().upper()] = sdk_module_module

    init_initializer = type(
        "InitInitializer", (*sdk_module_initializer_classes, SDKModuleInitializer), {}
    )

    def _initializer_cls() -> type[SDKModuleInitializer]:
        """Initializer class.

        Returns:
            The initializer class.
        """
        return init_initializer

    @dagger.function(
        doc="Returns a changeset to initialize a project with the SDK module directory."
    )
    @dagger.generate
    async def init(
        self,
        *,
        project_name: OptionalProjectNameDaggerType = OPTIONAL_PROJECT_NAME_DAGGER_DEFAULT,
        is_update: IsUpdateDaggerType = IS_UPDATE_DAGGER_DEFAULT,
        scm: SCMDaggerType = SCM_DAGGER_DEFAULT,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> Changeset:
        """Returns a changeset to initialize a project with the SDK module directory.

        Args:
            self: The current instance of the SDKModule class.
            project_name: Project name.
            is_update: Whether to update project directory files or not.
            scm: Project Source Code Management (SCM) list to be targeted or configured.
            platform: The container platform.

        Returns:
            A changeset to initialize a project with the SDK module directory.
        """
        # Call the wrapped init method
        return await self._init(
            project_name=project_name, is_update=is_update, scm=scm, platform=platform
        )

    sdk_module_options = create_enum("SDKModuleOptions", sdk_module_options_dict, is_unique=True)
    sdk_module_options.__doc__ = """SDKModule options."""
    sdk_module_name = sdk_module.name()
    sdk_language = dagger.object_type(
        add_enum_values_as_methods(sdk_module_options)(
            type(
                sdk_module_name,
                (sdk_module,),
                {"_initializer_cls": _initializer_cls(), "init": init},
            )
        )
    )

    return sdk_language  # ty: ignore[invalid-explicit-return]
