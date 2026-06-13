"""module package."""

import asyncio
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from enum import Enum, unique
from pathlib import Path, PurePosixPath
from typing import Annotated, Final, final

import dagger

from ...utils.class_name import ClassName
from ...utils.dagger.client import container_git
from ...utils.dagger.directory import directory_with_new_file
from ...utils.dagger.function import add_enum_values_as_methods
from ...utils.template import Mapping, Template, TemplateFile
from .context import (
    DaggerModuleMetadata,
    SDKModuleInitContextContainer,
    SDKModuleInitContextDirectory,
    SDKModuleInitContextDirectoryScm,
    SDKModuleInitContextDirectoryVcs,
)
from .scm import (
    _PROJECT_DIRECTORY_ANNOTATION,
    GITLAB_FOLDER,
    GITLAB_JOBS_FOLDER,
    SCM,
    GitLabJob,
    github_init,
    gitlab_init,
)
from .templates import COMMON_JINJA_ENVIRONMENT
from .vcs import VCS_PRIMARY_BRANCH, VCS_USER_EMAIL_DEFAULT, VCS_USER_NAME_DEFAULT

DAGGER_VERSION = "0.21.3"


def warning(message: str) -> None:
    """
    Helper function to print a formatted warning to stderr.

    Args:
        message: Warning message.
    """
    print(message, file=sys.stderr)


PROJECT_VERSION_DEFAULT: Final = "0.0.0+unknown"
ProjectNameType = str
PROJECT_NAME_DEFAULT: Final = "no-project-name"
ProjectNameDaggerType = Annotated[ProjectNameType | None, dagger.Doc("Project name")]
PROJECT_NAME_DAGGER_DEFAULT: Final = None
# dagger.Platform is build with: <os>/<platform_variant>
# opencontainers image spec documentation: https://github.com/opencontainers/image-spec/blob/main/image-index.md#image-index-property-descriptions
# Go Language documentation:
# - GOOS/GOARCH: https://go.dev/doc/install/source#environment
PlatformType = dagger.Platform
PlatformDaggerType = Annotated[
    PlatformType, dagger.Doc("Platform config OS and architecture in a Container.")
]
PLATFORM_DAGGER_DEFAULT: Final = dagger.Platform("linux/amd64")
ProjectDirectoryType = dagger.Directory
ProjectDirectoryDaggerType = Annotated[
    ProjectDirectoryType, dagger.Doc(_PROJECT_DIRECTORY_ANNOTATION)
]
IsUpdateType = bool
IsUpdateDaggerType = Annotated[IsUpdateType, dagger.Doc("Whether to update project files or not.")]
IS_UPDATE_DAGGER_DEFAULT: Final = False


SCMType = list[SCM]
SCMDaggerType = Annotated[
    SCMType,
    dagger.Doc("Project Source Code Management (SCM) list to be targeted or configured."),
]
SCM_DAGGER_DEFAULT: Final = [SCM.GITLAB]


@final
@dataclass(frozen=True, slots=True)
class ProjectAuthor:
    """ProjectAuthor."""

    name: str = VCS_USER_NAME_DEFAULT
    email: str = VCS_USER_EMAIL_DEFAULT


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
        """
        Create an initialization context.

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
        """
        Initialization directory context used in the SDK module directory initialization.

        Args:
            init_context_directory: SDK module initialization directory context.
            shiryu_metadata: Shiryu metadata.
            project_metadata: Project metadata.

        Returns:
            The updated SDK module initialization directory context.
        """
        dagger_name = "dagger"
        job_name = f".{dagger_name}"
        dagger_yml_template_mapping: Mapping = {"dagger_version": shiryu_metadata.dagger_version}
        dagger_yml_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path(f"{job_name}.yml"), PurePosixPath(GITLAB_FOLDER) / GITLAB_JOBS_FOLDER
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
        directory: dagger.Directory,
        platform: PlatformType,
    ) -> dagger.Directory:
        """
        Initialize the directory with the VCS folders and files.

        Args:
            project_authors: Project authors.
            init_context_vcs: SDK module initialization directory VCS context.
            directory: A directory to VCS initialize.
            platform: The container platform used for initialization.

        Returns:
            Returns a directory with the VCS folders and files.
        """
        _project_authors = sorted(project_authors, key=lambda author: author.name)
        project_author = _project_authors[0] if len(_project_authors) else ProjectAuthor()
        container = container_git(dagger.dag, platform)
        _directory = (
            container.with_directory(".", directory)
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
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(Path(".gitignore")),
            _gitignore_template_mapping,
        )
        return directory_with_new_file(_directory, _gitignore_template)

    @final
    @staticmethod
    def __scm_init(
        directory: dagger.Directory,
        init_context_directory_scm: SDKModuleInitContextDirectoryScm,
        scm: SCMType,
    ) -> dagger.Directory:
        """
        Initialize the directory with the SCM's files and folders.

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
        """
        README.md template file.

        Returns:
            The README.md template file.
        """
        return TemplateFile(Path("README.md"))

    @final
    @classmethod
    def _readme_md_template(cls, project_name: ProjectNameType) -> Template:
        """
        README.md template.

        Returns:
            The README.md template.
        """
        readme_md_template_mapping: Mapping = {"project_name": project_name.capitalize()}
        return Template(
            COMMON_JINJA_ENVIRONMENT, cls._readme_md_template_file(), readme_md_template_mapping
        )

    @classmethod
    async def _init_directory(
        cls,
        init_directory: dagger.Directory,
        init_context_directory: SDKModuleInitContextDirectoryType,
        project_metadata: ProjectMetadata,
        scm: SCMType,
        platform: PlatformType,
    ) -> dagger.Directory:
        """
        Build the initialization directory.

        Args:
            init_directory: The dagger directory to initialize.
            init_context_directory: SDK module initialization directory context.
            project_metadata: Project metadata.
            scm: Project Source Code Management (SCM) list to be targeted or configured.
            platform: The container platform used for initialization.

        Returns:
            The initialization directory.
        """
        directory = init_directory
        directory = await cls.__vcs_init(
            project_metadata.authors, init_context_directory.vcs, directory, platform
        )
        # README.md
        readme_md_template = cls._readme_md_template(project_metadata.name)
        directory = directory_with_new_file(directory, readme_md_template)
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


class SDKModule[
    SDKModuleInitializerType: SDKModuleInitializer,
    SDKModuleInitContextContainerType: SDKModuleInitContextContainer,
](ABC, ClassName):
    """SDKModule class."""

    @staticmethod
    @abstractmethod
    def _sdk_name() -> str:
        """
        Get the SDK name.

        Returns the SDK name.
        """
        ...

    @staticmethod
    @abstractmethod
    def _initializer_cls() -> type[SDKModuleInitializerType]:
        """
        Initializer class.

        Returns:
            The initializer class.
        """
        ...

    @final
    @classmethod
    async def __get_shiryu_metadata(cls, platform: PlatformType) -> DaggerModuleMetadata:
        """
        Returns shiryu metadata.

        Args:
            platform: The container platform used for initialization.

        Return:
            Shiryu metadata.
        """
        module_source = dagger.dag.current_module().source()
        # Get locked dagger version.
        # Alternative 1
        # pylock.toml file: actually it is the dagger python sdk version not the dagger engine.
        # py_lock_file_contents = module_source.file("pylock.toml").contents()
        # py_lock_file = tomllib.loads(py_lock_file_contents)
        # dagger_pkg = next(
        #     (
        #         package
        #         for package in py_lock_file.get("packages", [])
        #         if package.get("name") == "dagger-io"
        #     ),
        #     None,
        # )
        # if dagger_pkg is None:
        #     exception_message = "dagger-io not found in py.lock"
        #     raise Exception(exception_message)
        # dagger_version = dagger_pkg.get("version")
        # Alternative 2
        # Read it from the dagger.json. It is the minimal dagger engine requirement. Not useful.
        # Alternative 3
        # Read it from the running engine
        # dagger_version = await dagger.dag.version()
        # Alternative 4
        # Use lockfile mechanism from next versions:
        # - https://github.com/dagger/dagger/pull/11995
        # - https://github.com/dagger/dagger/pull/12046
        # Alternative 5
        # Use a hard coded version
        dagger_version = DAGGER_VERSION
        # Get module exact git tag. Falls back to the branch name if the commit is not tagged.
        container = container_git(dagger.dag, platform).with_directory(".", module_source)
        try:
            module_tag = (
                await container.with_exec(["git", "describe", "--tags", "--exact-match"]).stdout()
            ).strip()
            return DaggerModuleMetadata(
                dagger_version=dagger_version, git_tag_or_branch=module_tag.strip()
            )
        except dagger.QueryError:
            # TODO: https://github.com/dagger/dagger/issues/13054
            # TODO: the try-exception block is necessary because dagger.dag.current_module() fails
            # in dagger-in-dagger used in our tester unit module call with a QueryError
            try:
                module_branch = (
                    await container.with_exec(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout()
                ).strip()
                return DaggerModuleMetadata(
                    dagger_version=dagger_version,
                    git_tag_or_branch=module_branch.strip(),
                )
            except dagger.QueryError:
                git_tag_or_branch = "undefined"
                return DaggerModuleMetadata(
                    dagger_version=dagger_version, git_tag_or_branch=git_tag_or_branch
                )

    @classmethod
    @abstractmethod
    async def _get_project_metadata(
        cls, project_directory: ProjectDirectoryType, platform: PlatformType
    ) -> ProjectMetadata:
        """
        Get project metadata.

        Warning: It depends on the generated project files.

        Args:
            project_directory: Project directory.
            platform: The container platform.

        Returns:
            The project metadata.
        """
        project_author = ProjectAuthor()
        project_container = container_git(dagger.dag, platform).with_directory(
            ".", project_directory
        )
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
        return ProjectMetadata(
            name=PROJECT_NAME_DEFAULT,
            version=PROJECT_VERSION_DEFAULT,
            authors=frozenset({project_author}),
        )

    @final
    async def _get_metadata(
        self,
        project_directory: ProjectDirectoryDaggerType,
        project_name: ProjectNameDaggerType,
        platform: PlatformType,
    ) -> tuple[DaggerModuleMetadata, ProjectMetadata]:
        """
        Helper function to return an initialized directory for the SDK module.

        Args:
            project_directory: Project directory.
            project_name: Project name,
            platform: The container platform.

        Returns:
            The shiryu module and project metadata.
        """
        shiryu_metadata, _project_metadata = await asyncio.gather(
            self.__get_shiryu_metadata(platform),
            self._get_project_metadata(project_directory, platform),
        )
        project_metadata = (
            replace(_project_metadata, name=project_name) if project_name else _project_metadata
        )
        return (shiryu_metadata, project_metadata)

    @final
    @classmethod
    async def __is_vcs_init(
        cls, project_directory: dagger.Directory, platform: PlatformType
    ) -> bool:
        """
        Whether the dagger directory is initialized or not.

        Args:
            project_directory: The project directory.
            platform: The container platform used for initialization.

        Returns:
            `True` if directory is git initialized, `False` otherwise.
        """
        is_vcs_init: bool
        try:
            await (
                container_git(dagger.dag, platform)
                .with_directory(".", project_directory)
                .with_exec(["git", "rev-parse", "--is-inside-work-tree"])
                .sync()
            )
            is_vcs_init = True
        except dagger.QueryError:
            is_vcs_init = False
        return is_vcs_init

    @final
    @classmethod
    async def _init(  # noqa: PLR0913
        cls,
        init_directory: dagger.Directory,
        project_directory: ProjectDirectoryDaggerType,
        project_metadata: ProjectMetadata,
        is_update: IsUpdateType,
        scm: SCMType,
        platform: PlatformType,
    ) -> dagger.Directory:
        """
        Helper function to return an initialized directory for the SDK module.

        Args:
            init_directory: SDK module initialization directory.
            project_directory: Project directory.
            project_metadata: Project metadata.
            is_update: Whether to update project files or not.
            scm: Project Source Code Management (SCM) list to be targeted or configured.
            platform: The container platform.

        Returns:
            An initialized directory for the SDK module.
        """
        # Check if project is git initialized.
        is_vcs_init = await cls.__is_vcs_init(project_directory, platform)
        # Merge directories.
        vcs_excludes = [".git/"] if is_vcs_init else []
        merged_directory = (
            project_directory.with_directory(".", init_directory, exclude=vcs_excludes)
            if is_update
            else init_directory.filter(exclude=vcs_excludes).with_directory(".", project_directory)
        ).directory(".")
        return merged_directory

    @dagger.function
    async def init(
        self,
        project_directory: ProjectDirectoryDaggerType,
        project_name: ProjectNameDaggerType = PROJECT_NAME_DAGGER_DEFAULT,
        is_update: IsUpdateDaggerType = IS_UPDATE_DAGGER_DEFAULT,
        scm: SCMDaggerType = SCM_DAGGER_DEFAULT,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> dagger.Directory:
        """Returns an initialized directory for the SDK module."""
        # Gather metadata.
        shiryu_metadata, project_metadata = await self._get_metadata(
            project_directory, project_name, platform
        )
        # TODO: When init() for all modules is done this can be moved to _init()
        # Build the initialization context directory.
        initializer_cls = self._initializer_cls()
        init_context_directory = initializer_cls._create_init_context_directory()
        init_context_directory = initializer_cls._init_context_directory(
            init_context_directory, shiryu_metadata, project_metadata
        )
        # Build initialized directory.
        init_directory = dagger.dag.directory()
        init_directory = await initializer_cls._init_directory(
            init_directory, init_context_directory, project_metadata, scm, platform
        )
        # Create the initialize directory.
        return await self._init(
            init_directory, project_directory, project_metadata, is_update, scm, platform
        )

    @classmethod
    @abstractmethod
    def _create_init_context_container(cls) -> SDKModuleInitContextContainerType:
        """
        Create an initialization context container.

        Returns:
            An initialization context container.
        """
        ...

    @classmethod
    def _init_context_container(
        cls, init_context_container: SDKModuleInitContextContainerType
    ) -> SDKModuleInitContextContainerType:
        """
        Initialization container context used in the SDK module container initialization.

        Args:
            init_context_container: SDK module initialization container context.

        Returns:
            The updated SDK module initialization container context.
        """
        return init_context_container.evolve(
            apt_packages=init_context_container.apt_packages | {"git"}
        )

    @classmethod
    @abstractmethod
    def _base_container(
        cls, init_context_container: SDKModuleInitContextContainerType, platform: PlatformType
    ) -> dagger.Container:
        """
        Base container.

        Args:
            init_context_container: SDK module initialization container context.
            platform: The container platform.

        Returns:
            A base container.
        """
        ...

    @final
    @classmethod
    def _init_container(
        cls,
        init_context_container: SDKModuleInitContextContainerType,
        project_directory: ProjectDirectoryDaggerType,
        platform: PlatformDaggerType,
    ) -> dagger.Container:
        """
        Helper function to return an initialized container for the SDK module.

        Args:
            init_context_container: SDK module initialization container context.
            project_directory: Project directory.
            platform: The container platform.

        Returns:
            An initialized directory for the SDK module.
        """
        return cls._base_container(init_context_container, platform).with_directory(
            ".", project_directory
        )

    @final
    @classmethod
    async def _exec_container(
        cls, project_directory: ProjectDirectoryDaggerType, platform: PlatformDaggerType
    ) -> dagger.Container:
        """
        Helper function to return an initialized container for the SDK module.

        Args:
            project_directory: Project directory.
            platform: The container platform.

        Returns:
            An initialized directory for the SDK module.
        """
        init_context_container = cls._create_init_context_container()
        init_context_container = cls._init_context_container(init_context_container)
        return cls._init_container(init_context_container, project_directory, platform)


def get_sdk_language(
    sdk_module: type[SDKModule], sdk_module_modules: set[type[SDKModule]]
) -> type[SDKModule]:
    """
    Get SDK language.

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
        """
        Initializer class.

        Returns:
            The initializer class.
        """
        return init_initializer

    SDKModuleOptions = final(  # noqa: N806
        unique(Enum("SDKModuleOptions", sdk_module_options_dict))  # type: ignore[type-var]
    )
    SDKModuleOptions.__doc__ = """SDKModule options."""
    sdk_module_name = sdk_module.name()
    sdk_language = dagger.object_type(
        final(
            # mypy bug: https://github.com/python/mypy/issues/17147
            add_enum_values_as_methods(SDKModuleOptions)(  # type: ignore[arg-type]
                type(sdk_module_name, (sdk_module,), {"_initializer_cls": _initializer_cls()})
            )
        )
    )

    return sdk_language
