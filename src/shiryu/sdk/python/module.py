"""module module."""

import tomllib
from dataclasses import replace
from enum import Enum, auto, unique
from pathlib import Path, PurePosixPath
from typing import Final, final

from dagger_clients.core import Container, Directory
from packaging.version import Version

from ...utils.dagger.client import container_uv
from ...utils.dagger.directory import directory_with_new_file
from ...utils.dagger.file import TargetFile
from ...utils.dagger.function import ProjectNameType, SourceType
from ...utils.template import Mapping, Template, TemplateFile
from ..common.context import DaggerModuleMetadata, SDKModuleInitContextContainer
from ..common.module import (
    PlatformType,
    ProjectAuthor,
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

# PINNED: latest python 0.x version
# https://www.python.org/download/releases/early/
LATEST_PYTHON_0_VERSION: Final = Version("0.9")
# PINNED: latest python 1.x version
# https://www.python.org/download/releases/
LATEST_PYTHON_1_VERSION: Final = Version("1.6")
# PINNED: latest python 2.x version and 3.y version
# https://peps.python.org/pep-0361/
# https://devguide.python.org/versions/#full-chart
# EOL:
# - 2.7: 2020-01-01
# - 3.10: 2026-10-01
LATEST_PYTHON_2_VERSION: Final = Version("2.7")
LATEST_PYTHON_3_VERSION: Final = Version("3.15")
# LATEST_PYTHON_4_VERSION: Final = Version("4.0")


def _python_supported_versions(python_lower_bound_version: Version) -> frozenset[Version]:
    """Python supported versions.

    Args:
        python_lower_bound_version: Python lower_bound_version.

    Returns:
        Python supported versions.
    """
    latest_versions = {
        LATEST_PYTHON_0_VERSION,
        LATEST_PYTHON_1_VERSION,
        LATEST_PYTHON_2_VERSION,
        LATEST_PYTHON_3_VERSION,
        # LATEST_PYTHON_4_VERSION,
    }
    lower_bound = python_lower_bound_version
    versions = set()
    current_major = lower_bound.major
    max_major = max(version.major for version in latest_versions)

    while current_major <= max_major:
        # Find the specific upper bound for this major version
        upper_bound = next(version for version in latest_versions if version.major == current_major)
        start_minor = lower_bound.minor if current_major == lower_bound.major else 0
        current_minor = start_minor

        while current_minor <= upper_bound.minor:
            versions.add(Version(f"{current_major}.{current_minor}"))
            current_minor += 1

        current_major += 1

    return frozenset(versions)


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
        """Create an initialization context directory.

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
        """Initialization directory context used in the SDK module directory initialization.

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
            | {PROJECT_SOURCE_CODE_FOLDER},
            vcs=init_context_directory.vcs.evolve(
                exclude_files_folders=init_context_directory.vcs.exclude_files_folders
                | {"__pycache__/"},
            ),
        )

    @final
    @classmethod
    def _pyproject_toml_template_file(cls) -> TemplateFile:
        """Get the pyproject.toml template file.

        Returns:
            The pyproject.toml template file.
        """
        return TemplateFile(Path("pyproject.toml"))

    @final
    @classmethod
    def _uv_lower_bound_requires_python(cls) -> Version:
        """Uv lower bound requires python.

        Returns:
            Uv lower bound requires python.
        """
        # PINNED: minimal uv python version
        # - uv minium python support - https://docs.astral.sh/uv/reference/policies/python/#python-versions
        return Version("3.6")

    @final
    @classmethod
    def _uv_toml_template_file(cls) -> TemplateFile:
        """uv.toml template file.

        Returns:
            The uv.toml template file.
        """
        return TemplateFile(Path("uv.toml"))

    @final
    @classmethod
    def _uv_toml_template(cls) -> Template:
        """uv.toml template.

        Returns:
            The uv.toml template.
        """
        uv_toml_template_mapping: Mapping = {}
        return Template(
            PYTHON_JINJA_ENVIRONMENT, cls._uv_toml_template_file(), uv_toml_template_mapping
        )

    @final
    @classmethod
    def _uv_cmd(cls) -> list[str]:
        """Build the base ``uv`` command pre-configured with the config file.

        Returns:
            Command argument list starting with ``uv`` and ``--config-file``
            pointing to the resolved ``uv.toml`` path.
        """
        return ["uv", f"--config-file={cls._uv_toml_template_file().file_name}"]

    @classmethod
    async def _init_directory(  # noqa: PLR0913, PLR0917
        cls,
        init_directory: Directory,
        init_context_directory: PythonModuleInitContextDirectory,
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
        init_directory = await super()._init_directory(
            init_directory,
            init_context_directory,
            project_metadata,
            scm,
            platform,
            container_security_audit_file,
        )
        project_name = project_metadata.name
        project_authors = project_metadata.authors
        package_name_canonical = get_package_name_canonical(project_name)
        # A decision is made to not run uv init and let shiryu create the files.
        pyproject_toml_template_file = cls._pyproject_toml_template_file()
        # pyproject.toml
        dependency_groups = init_context_directory.dependency_groups
        lower_bound_requires_python = max(
            cls._uv_lower_bound_requires_python(), dependency_groups.lower_bound_requires_python
        )
        pyproject_toml_template_mapping: Mapping = {
            "project_name": project_name,
            "project_authors": project_authors,
            "project_version": project_metadata.version,
            "readme_file_name": str(cls._readme_md_template_file().output_file_name),
            "license": str(cls._license_template_file().file_name),
            "license_file_name": str(cls._license_template_file().output_file_name),
            "requires_python": lower_bound_requires_python,
            "python_versions": _python_supported_versions(lower_bound_requires_python),
            "dependency_groups_specifiers": dependency_groups.specifiers,
        }
        pyproject_toml_template = Template(
            PYTHON_JINJA_ENVIRONMENT, pyproject_toml_template_file, pyproject_toml_template_mapping
        )
        init_directory = directory_with_new_file(init_directory, pyproject_toml_template)
        source_code_package_name_canonical_path = (
            PurePosixPath(PROJECT_SOURCE_CODE_FOLDER) / package_name_canonical
        )
        # py.typed
        py_typed_template_mapping: Mapping = {}
        py_typed_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("py.typed"), output_directory=source_code_package_name_canonical_path
            ),
            py_typed_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, py_typed_template)
        # uv.toml
        uv_toml_template = cls._uv_toml_template()
        init_directory = directory_with_new_file(init_directory, uv_toml_template)
        # uv.lock
        # uv run needs the project to be a package and have files.
        # <source_code>/<package_name>/__init__.py
        __init___py_template_mapping: Mapping = {"project_name": project_name}
        __init___py_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("__init__.py"), output_directory=source_code_package_name_canonical_path
            ),
            __init___py_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, __init___py_template)
        return (
            (
                await container_uv(
                    platform,
                    container_security_audit_file,
                    TargetFile.from_template(uv_toml_template),
                )
            )
            .with_directory(".", init_directory)
            .with_exec([*cls._uv_cmd(), "lock"])
            .directory(".")
        )


class PythonModule(SDKModule[PythonModuleInitializer, SDKModuleInitContextContainer]):
    """PythonModule class."""

    @final
    @staticmethod
    def _sdk_name() -> str:
        """Get the SDK name.

        Returns:
            The SDK name.
        """
        return SDK_MODULE_NAME

    @final
    @classmethod
    async def _get_project_metadata(
        cls,
        source: SourceType,
        project_name: ProjectNameType,
        platform: PlatformType,
        container_security_audit_file: TargetFile,
    ) -> ProjectMetadata:
        """Get project metadata.

        Args:
            source: Project source directory.
            project_name: Project name.
            platform: The container platform.
            container_security_audit_file: Container security audit file.

        Returns:
            The project metadata.
        """
        initializer = cls._initializer_cls()
        project_metadata = await super()._get_project_metadata(
            source, project_name, platform, container_security_audit_file
        )
        pyproject_toml_path_str = str(initializer._pyproject_toml_template_file().output_path)
        if await source.exists(pyproject_toml_path_str):
            pyproject_toml_file_contents = await source.file(pyproject_toml_path_str).contents()
            pyproject_toml = tomllib.loads(pyproject_toml_file_contents)
            pyproject_toml_project = pyproject_toml["project"]
            project_metadata = replace(
                project_metadata,
                name=pyproject_toml_project["name"],
                version=pyproject_toml_project.get("version", project_metadata.version),
                authors=frozenset(
                    {
                        ProjectAuthor(project_author["name"], project_author["email"])
                        for project_author in pyproject_toml_project["authors"]
                    }
                ),
            )
        return project_metadata

    @final
    @classmethod
    def _create_init_context_container(cls) -> SDKModuleInitContextContainer:
        """Create an initialization context container.

        Returns:
            An initialization context container.
        """
        return SDKModuleInitContextContainer.create_default()

    @final
    @classmethod
    async def _dependencies_security_audit_file(cls, source: SourceType) -> TargetFile:
        """Get the project dependencies security audit file.

        Args:
            source: Project source directory.

        Returns:
            The project dependencies security audit file.
        """
        initializer_cls = cls._initializer_cls()
        uv_toml_output_path = initializer_cls._uv_toml_template().template_file.output_path
        uv_toml_output_path_str = str(uv_toml_output_path)

        return TargetFile(source.file(uv_toml_output_path_str), uv_toml_output_path)

    @final
    @classmethod
    async def _base_container(
        cls,
        init_context_container: SDKModuleInitContextContainer,
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
        return await container_uv(
            platform,
            container_security_audit_file,
            dependencies_security_audit_file,
            apt_packages=init_context_container.container_packages,
        )

    @final
    @classmethod
    def _build_uv_run_command(
        cls, command: list[str], *, execution_mode: ExecutionMode = ExecutionMode.MODULE
    ) -> list[str]:
        """Builds the uv run command.

        Args:
            command: A command as a list of strings.
            execution_mode: The execution mode to launch the target.

        Returns:
            The uv command to run.
        """
        initializer = cls._initializer_cls()
        return [
            *initializer._uv_cmd(),
            "run",
            "--locked",
            f"--group={cls.name()}",
            *(("--module",) if execution_mode is ExecutionMode.MODULE else ()),
            *command,
        ]
