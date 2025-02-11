"""module module."""

import tomllib
from pathlib import Path
from typing import Any, Final

import dagger

from ...utils.case import camel_case_to_dash_case
from ...utils.dagger.container import container_with_files, is_container_with_file
from ...utils.template import Mapping, Template, TemplateFile
from ..common.module import (
    PROJECT_NAME_DEFAULT,
    PlatformType,
    ProjectAuthor,
    ProjectNameType,
    ProjectProperties,
    SCMListType,
    SDKEnv,
    SDKModule,
    SDKModuleInit,
    VCSUser,
)
from .templates import PYTHON_JINJA_ENVIRONMENT
from .utils import get_package_name_canonical

MODULE_NAME: Final = str(Path(__file__).parent.name)

ModulesPythonPackages = dict[str, set[str]]


class PythonModuleInit(SDKModuleInit):
    """PythonModuleInit class."""

    @staticmethod
    def _sdk_name() -> str:
        """
        Get the SDK name.

        Returns the SDK name.
        """
        return MODULE_NAME

    @classmethod
    def _vcs_exclude_files_folders(cls, project_name: ProjectNameType) -> set[str]:
        """
        Files and folders to exclude from vcs.

        Args:
            project_name: Project name.

        Returns:
            Files and folders to exclude from vcs.
        """
        vcs_exclude_files_folders = super()._vcs_exclude_files_folders(project_name)
        vcs_exclude_files_folders.update({"/.venv/", "__pycache__/"})
        return vcs_exclude_files_folders

    @classmethod
    def _pyproject_toml_template_file(cls) -> TemplateFile:
        """
        Get the pyproject.toml template file.

        Returns:
            The pyproject.toml template file.
        """
        return TemplateFile(Path("pyproject.toml"), cls._container_project_path())

    @classmethod
    def _sdk_source_code_python_packages(cls) -> set[str]:
        """
        Python packages used in modules source code.

        Returns:
            Python packages used in modules source code.
        """
        return set()

    @classmethod
    async def _module_init(
        cls, sdk_env: SDKEnv, is_overwrite: bool, scm: SCMListType
    ) -> SDKEnv:
        """
        Initialize the SDK module environment.

        Args:
            sdk_env: SDK environment.
            is_overwrite: Whether to overwrite files or not.
            scm: Project Source Code Management (SCM) list to be targeted or configured.

        Returns:
            Returns an SDK module environment.
        """
        _sdk_env = await super()._module_init(sdk_env, is_overwrite, scm)
        container = _sdk_env.container
        project_properties = _sdk_env.project_properties
        package_name_canonical = get_package_name_canonical(project_properties.name)
        # py.typed
        py_typed_template_mapping: Mapping = {}
        py_typed_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("py.typed"),
                cls._container_project_source_path() / package_name_canonical,
            ),
            py_typed_template_mapping,
        )
        container = await container_with_files(
            container, (py_typed_template,), is_overwrite
        )
        return SDKEnv(container, project_properties)


class PythonModule(SDKModule, PythonModuleInit):
    """PythonModule class."""

    @classmethod
    def _base_container_base_packages(cls) -> set[str]:
        """
        Base container base packages.

        Returns:
            Base container base packages.
        """
        base_container_base_packages = super()._base_container_base_packages()
        base_container_base_packages.update({"pipx"})
        return base_container_base_packages

    @classmethod
    def _base_container(cls, platform: PlatformType) -> dagger.Container:
        """
        Base container.

        Args:
            platform: The container platform.

        Returns:
            A base container.
        """
        container = super()._base_container(platform)
        venv_path_str = "/opt/venv_shiryu"
        return (
            container.with_mounted_cache(
                "/root/.cache/pipx",
                dagger.dag.cache_volume("shiryu-pipx-debian-trixie-slim"),
            )
            .with_env_variable(
                name="PATH", value="/root/.local/bin:${PATH}", expand=True
            )
            .with_exec(["pipx", "install", "uv"])
            .with_mounted_cache(
                "/root/.cache/uv",
                dagger.dag.cache_volume("shiryu-uv-debian-trixie-slim"),
            )
            .with_exec(["uv", "venv", venv_path_str])
            .with_env_variable(name="VIRTUAL_ENV", value=venv_path_str)
            # .with_env_variable(name="UV_PROJECT_ENVIRONMENT", value=venv_path_str)
            # .with_env_variable(
            #    name="PATH", value="${VIRTUAL_ENV}/bin:${PATH}", expand=True
            # )
        )

    @classmethod
    def _base_container_modules_python_packages(cls) -> ModulesPythonPackages:
        """
        Base container modules python packages.

        Returns:
            Base container modules python packages.
        """
        return {}

    @classmethod
    async def _sdk_module_init(
        cls,
        container: dagger.Container,
        project_name: ProjectNameType | None,
        vcs_user: VCSUser,
        is_overwrite: bool,
        scm: SCMListType,
    ) -> SDKEnv:
        """
        Initialize the SDK module environment.

        Args:
            container: SDK container to initialize.
            project_name: Project name.
            vcs_user: VCS user.
            is_overwrite: Whether to overwrite files or not.
            scm: Project Source Code Management (SCM) list to be targeted or configured.

        Returns:
            Returns an SDK module environment.
        """
        pyproject_toml_template_file = cls._pyproject_toml_template_file()
        # pyproject.toml
        is_container_with_file_pyproject_toml = await is_container_with_file(
            container, pyproject_toml_template_file
        )
        _project_name: str
        pyproject_toml_data: dict[str, Any]
        pyproject_toml_data_project: dict[str, Any]
        if is_container_with_file_pyproject_toml and not is_overwrite:
            pyproject_toml_file_contents = await container.file(
                str(pyproject_toml_template_file.output_path)
            ).contents()
            pyproject_toml_data = tomllib.loads(pyproject_toml_file_contents)
            pyproject_toml_data_project = pyproject_toml_data["project"]
            _project_name = pyproject_toml_data_project["name"]
            if project_name is not None and project_name != _project_name:
                exception_message = f"{pyproject_toml_template_file.file_name} project name ({_project_name}) is different to the provided project name ({project_name})."
                raise Exception(exception_message)
            # TODO: print warning if project_author not in authors?
        else:
            _project_name = (
                project_name if project_name is not None else PROJECT_NAME_DEFAULT
            )
            pyproject_toml_template_mapping: Mapping = {
                "project_name": _project_name,
                "project_author": ProjectAuthor(vcs_user.name, vcs_user.email),
                "readme_file_name": str(
                    cls._readme_md_template_file().output_file_name
                ),
                "optional_dependencies": cls._base_container_modules_python_packages(),
            }
            pyproject_toml_template = Template(
                PYTHON_JINJA_ENVIRONMENT,
                pyproject_toml_template_file,
                pyproject_toml_template_mapping,
            )
            pyproject_toml_data = tomllib.loads(pyproject_toml_template.contents)
            pyproject_toml_data_project = pyproject_toml_data["project"]
            container = await container_with_files(
                container, (pyproject_toml_template,), is_overwrite
            )
        # pylock.toml
        pylock_toml_file_name = "pylock.toml"
        is_container_with_file_pylock_toml = (
            pylock_toml_file_name
            in await cls._container_project_directory(container).entries()
        )
        if not is_container_with_file_pylock_toml or is_overwrite:
            # uv export needs the README.md file to create the py.lock file.
            # README.md
            readme_md_template = cls._readme_md_template(_project_name)
            container = await container_with_files(
                container, (readme_md_template,), is_overwrite
            )
            # TODO: should we consider forcing users to use uv? Should we remove the uv.lock file?
            container = container.with_exec(
                ["uv", "export", f"--format={pylock_toml_file_name}"],
                redirect_stdout=pylock_toml_file_name,
            ).with_exec(["rm", "uv.lock"])
        # Project layers.
        project_authors = set(
            ProjectAuthor(author["name"], author["email"])
            for author in pyproject_toml_data_project["authors"]
        )
        project_version = (
            await container.with_exec(["uv", "pip", "install", "hatch"])
            .with_exec(["uv", "run", "--no-project", "--module", "hatch", "version"])
            .stdout()
        )
        project_properties = ProjectProperties(
            _project_name, project_authors, project_version
        )
        pyproject_toml_template_file = cls._pyproject_toml_template_file()
        pyproject_toml_file_name = str(pyproject_toml_template_file.file_name)
        install_project_dependencies_command = [
            "uv",
            "pip",
            "install",
            "--no-sources",
            "--requirement",
            pyproject_toml_file_name,
        ]
        if "optional-dependencies" in pyproject_toml_data_project:
            name_dash_case = camel_case_to_dash_case(cls.name())
            if name_dash_case in pyproject_toml_data_project["optional-dependencies"]:
                install_project_dependencies_command = [
                    *install_project_dependencies_command,
                    "--extra",
                    name_dash_case,
                ]
        base_container_python_packages = (
            cls._base_container_modules_python_packages().get(cls.name(), set())
        )
        if len(base_container_python_packages):
            container = container.with_exec(
                ["uv", "pip", "install", *base_container_python_packages]
            )
        return SDKEnv(
            container.with_exec(install_project_dependencies_command),
            project_properties,
        )
