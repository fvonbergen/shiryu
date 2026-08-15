"""module module."""

import tomllib
from dataclasses import replace
from enum import Enum, auto, unique
from pathlib import Path, PurePosixPath
from typing import Final, final

import dagger

from ...utils.dagger.client import container_uv
from ...utils.dagger.directory import directory_with_new_file
from ...utils.template import Mapping, Template, TemplateFile
from ..common.context import DaggerModuleMetadata, SDKModuleInitContextContainer
from ..common.module import (
    PlatformType,
    ProjectAuthor,
    ProjectDirectoryType,
    ProjectMetadata,
    SCMType,
    SDKModule,
    SDKModuleInitializer,
)
from ..common.utils import PROJECT_SOURCE_CODE_FOLDER
from .context import PythonModuleInitContextDirectory
from .templates import PYTHON_JINJA_ENVIRONMENT
from .utils import get_package_name_canonical

SDK_MODULE_NAME: Final = str(Path(__file__).parent.name)


@unique
class ExecutionMode(Enum):
    """Execution mode options."""

    SCRIPT = auto()
    MODULE = auto()


class PythonModuleInitializer(SDKModuleInitializer[PythonModuleInitContextDirectory]):
    """PythonModuleInitializer class."""

    @final
    @classmethod
    def _create_init_context_directory(cls) -> PythonModuleInitContextDirectory:
        """
        Create an initialization context directory.

        Returns:
            An initialization context directory.
        """
        return PythonModuleInitContextDirectory.create_default()

    @classmethod
    def _init_context_directory(
        cls,
        init_context_directory: PythonModuleInitContextDirectory,
        shiryu_metadata: DaggerModuleMetadata,
        project_metadata: ProjectMetadata,
    ) -> PythonModuleInitContextDirectory:
        """
        Initialization directory context used in the SDK module directory initialization.

        Args:
            init_context_directory: SDK module initialization directory context.
            shiryu_metadata: Shiryu metadata.
            project_metadata: Project metadata.

        Returns:
            The updated SDK module initialization directory context.
        """
        init_context_directory = super()._init_context_directory(
            init_context_directory, shiryu_metadata, project_metadata
        )
        return init_context_directory.evolve(
            source_code_files_folders=init_context_directory.source_code_files_folders
            | {PROJECT_SOURCE_CODE_FOLDER}
        )

    @final
    @classmethod
    def _pyproject_toml_template_file(cls) -> TemplateFile:
        """
        Get the pyproject.toml template file.

        Returns:
            The pyproject.toml template file.
        """
        return TemplateFile(Path("pyproject.toml"))

    @classmethod
    async def _init_directory(
        cls,
        init_directory: dagger.Directory,
        init_context_directory: PythonModuleInitContextDirectory,
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
        init_directory = await super()._init_directory(
            init_directory, init_context_directory, project_metadata, scm, platform
        )
        project_name = project_metadata.name
        project_authors = project_metadata.authors
        package_name_canonical = get_package_name_canonical(project_name)
        # A decision is made to not run uv init and let shiryu create the files.
        pyproject_toml_template_file = cls._pyproject_toml_template_file()
        # pyproject.toml
        pyproject_toml_template_mapping: Mapping = {
            "project_name": project_name,
            "project_authors": project_authors,
            "readme_file_name": str(cls._readme_md_template_file().output_file_name),
            "dependency_groups": init_context_directory.dependency_groups,
        }
        pyproject_toml_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            pyproject_toml_template_file,
            pyproject_toml_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, pyproject_toml_template)
        # py.typed
        py_typed_template_mapping: Mapping = {}
        py_typed_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("py.typed"), PurePosixPath(PROJECT_SOURCE_CODE_FOLDER) / package_name_canonical
            ),
            py_typed_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, py_typed_template)
        # uv.lock
        # uv run needs the project to be a package and have files.
        # __init__.py
        __init___py_template_mapping: Mapping = {"project_name": project_name}
        __init___py_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("__init__.py"),
                PurePosixPath(PROJECT_SOURCE_CODE_FOLDER) / package_name_canonical,
            ),
            __init___py_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, __init___py_template)
        return (
            container_uv(dagger.dag, platform)
            .with_directory(".", init_directory)
            .with_exec(["uv", "lock"])
            .directory(".")
        )


class PythonModule(SDKModule[PythonModuleInitializer, SDKModuleInitContextContainer]):
    """PythonModule class."""

    @final
    @staticmethod
    def _sdk_name() -> str:
        """
        Get the SDK name.

        Returns:
            The SDK name.
        """
        return SDK_MODULE_NAME

    @final
    @classmethod
    async def _get_project_metadata(
        cls, project_directory: ProjectDirectoryType, platform: PlatformType
    ) -> ProjectMetadata:
        """
        Get project metadata.

        Args:
            project_directory: Project directory.
            platform: The container platform.

        Returns:
            The project metadata.
        """
        initializer = cls._initializer_cls()
        project_metadata = await super()._get_project_metadata(project_directory, platform)
        project_container = container_uv(dagger.dag, platform, {"git"}).with_directory(
            ".", project_directory
        )
        try:
            pyproject_toml_file_contents = await project_container.file(
                str(initializer._pyproject_toml_template_file().output_path)
            ).contents()
            pyproject_toml = tomllib.loads(pyproject_toml_file_contents)
            pyproject_toml_project = pyproject_toml["project"]
            project_metadata = replace(
                project_metadata,
                name=pyproject_toml_project["name"],
                authors=frozenset(
                    {
                        ProjectAuthor(name=project_author["name"], email=project_author["email"])
                        for project_author in pyproject_toml_project["authors"]
                    }
                ),
            )
        except dagger.QueryError:
            ...
        try:
            project_version = (
                await project_container.with_exec(["uvx", "hatch", "version"]).stdout()
            ).strip()
            project_metadata = replace(project_metadata, version=project_version)
        except dagger.QueryError:
            ...
        return project_metadata

    @final
    @classmethod
    def _create_init_context_container(cls) -> SDKModuleInitContextContainer:
        """
        Create an initialization context container.

        Returns:
            An initialization context container.
        """
        return SDKModuleInitContextContainer.create_default()

    @final
    @classmethod
    def _base_container(
        cls, init_context_container: SDKModuleInitContextContainer, platform: PlatformType
    ) -> dagger.Container:
        """
        Base container.

        Args:
            init_context_container: SDK module initialization container context.
            platform: The container platform.

        Returns:
            A base container.
        """
        return container_uv(dagger.dag, platform, init_context_container.apt_packages)

    @final
    @classmethod
    def _build_uv_run_command(
        cls, command: list[str], execution_mode: ExecutionMode = ExecutionMode.MODULE
    ) -> list[str]:
        """
        Builds the uv run command.

        Args:
            command: A command as a list of strings.
            execution_mode: The execution mode to launch the target.

        Returns:
            The uv command to run.
        """
        return [
            "uv",
            "run",
            "--group",
            cls.name(),
            *(("--module",) if execution_mode is ExecutionMode.MODULE else ()),
            *command,
        ]
