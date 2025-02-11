"""base module."""

from pathlib import Path

import dagger
import tomllib

from ...utils.dagger import container_with_file, is_container_with_file
from ...utils.template import Mapping, Template, TemplateFile
from ..common import (
    PlatformType,
    ProjectNameType,
    ProjectProperties,
    ProjectType,
    SDKBase,
)
from .templates import PYTHON_JINJA_ENVIRONMENT


class PythonBase(SDKBase):
    """PythonBase class."""

    @classmethod
    def vcs_exclude_files_folders(cls) -> list[str]:
        """
        Files and folders to exclude from vcs.

        Returns:
            A list of files and folders to exclude from vcs.
        """
        vcs_exclude_files_folders = super(PythonBase, cls).vcs_exclude_files_folders()
        return [*vcs_exclude_files_folders, "/.venv/", "__pycache__/"]

    @classmethod
    def pyproject_toml_template_file(cls) -> TemplateFile:
        """
        Get the pyproject.toml template file.

        Returns:
            The pyproject.toml template file.
        """
        return TemplateFile(Path("pyproject.toml"), cls.project_path())

    @classmethod
    def py_typed_template_file(cls, project_name: ProjectNameType) -> TemplateFile:
        """pyproject.toml template file."""
        return TemplateFile(Path("py.typed"), cls.project_source_path() / project_name)

    @classmethod
    async def python_env(
        cls,
        project: ProjectType | None,
        platform: PlatformType,
    ) -> tuple[dagger.Container, ProjectProperties]:
        """Build environment for the provided project Directory."""
        container = cls.project_env(platform)
        pyproject_toml_template_file = cls.pyproject_toml_template_file()
        pyproject_toml_file_name = str(pyproject_toml_template_file.file_name)
        project_path_str = str(cls.project_path())
        venv_path_str = "/opt/venv_shiryu"
        apt_install = ("apt", "install", "--assume-yes", "--no-install-recommends")
        base_packages = ("pipx",)
        container = (
            container.with_mounted_cache(
                "/root/.cache/uv",
                dagger.dag.cache_volume("shiryu-uv-debian-trixie-slim"),
            )
            # .with_exec(["apt", "update"], redirect_stdout="/tmp/stdout1")
            .with_exec(["apt", "update"])
            .with_exec([*apt_install, *base_packages])
            .with_exec(["apt", "autoremove"])
            .with_exec(["apt", "clean"])
            .with_exec(["pipx", "ensurepath"])
            .with_env_variable(
                name="PATH", value="/root/.local/bin:${PATH}", expand=True
            )
            .with_env_variable(name="UV_LINK_MODE", value="copy")
            .with_exec(["pipx", "install", "uv"])
            .with_env_variable(name="VIRTUAL_ENV", value=venv_path_str)
            .with_exec(["uv", "venv", venv_path_str])
            .with_env_variable(
                name="PATH", value="${VIRTUAL_ENV}/bin:${PATH}", expand=True
            )
        )
        if project:
            container = container.with_mounted_directory(project_path_str, project)
        # Project layers.
        # TODO: Read project name from project directory (https://github.com/dagger/dagger/pull/9617)
        project_properties: ProjectProperties = {"name": "", "version": ""}
        if await is_container_with_file(container, pyproject_toml_template_file):
            pyproject_toml_data = tomllib.loads(
                await container.file(
                    str(pyproject_toml_template_file.output_path)
                ).contents()
            )
            project_name = pyproject_toml_data["project"]["name"]
            project_version = (
                await container.with_exec(["uv", "pip", "install", "hatch"])
                .with_exec(["hatch", "version"])
                .stdout()
            )
            project_properties = {"name": project_name, "version": project_version}
        container = await PythonBase._init(container, project_properties["name"])
        return (
            container.with_exec(
                [
                    "uv",
                    "pip",
                    "install",
                    "--no-sources",
                    "--requirement",
                    pyproject_toml_file_name,
                ]
            ),
            project_properties,
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
        container = await super(PythonBase, cls)._init(container, project_name)
        # pyproject.toml
        pyproject_toml_template_mapping: Mapping = {"project_name": project_name}
        pyproject_toml_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls.pyproject_toml_template_file(),
            pyproject_toml_template_mapping,
        )
        container = await container_with_file(container, pyproject_toml_template)
        # py.typed
        py_typed_template_mapping: Mapping = {}
        py_typed_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls.py_typed_template_file(project_name),
            py_typed_template_mapping,
        )
        return await container_with_file(container, py_typed_template)
