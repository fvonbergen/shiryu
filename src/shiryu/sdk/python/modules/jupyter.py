"""jupyter module."""

from pathlib import Path
from typing import Annotated, Final, final

import dagger

from ....utils.dagger.container import container_with_files
from ....utils.template import Mapping, Template, TemplateFile
from ...common.module import (
    PLATFORM_DEFAULT,
    PlatformType,
    ProjectDirectoryType,
    SCMListType,
    SDKEnv,
    SDKModuleModule,
)
from ..module import PythonModule, PythonModuleInit
from ..templates import PYTHON_JINJA_ENVIRONMENT

PortType = Annotated[int, dagger.Doc("Jupyter notebooks port")]

JUPYTER_NOTEBOOKS_CACHE_VOLUME = dagger.dag.cache_volume("shiryu-jupyter-debian-trixie")


class JupyterInit(PythonModuleInit):
    """Python SDK jupyter initializer."""

    @final
    @staticmethod
    def _notebooks_folder() -> str:
        """
        Get the notebooks folder name.

        Returns:
            The notebooks folder name.
        """
        return "notebooks"

    @final
    @classmethod
    def _container_project_notebooks_path(cls) -> Path:
        """
        Get the container project notebooks path.

        Returns:
            The container project notebooks path.
        """
        return cls._container_project_path() / cls._notebooks_folder()

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
        # pyproject.toml: add group dependencies
        python_packages = {"notebook", "python-lsp-server"}
        container = container.with_exec(
            ["uv", "add", "--group", Jupyter.name(), *python_packages, "--no-sync"]
        )
        # <jupyter notebooks>/
        container = container.with_exec(
            [
                "mkdir",
                "--parents",
                str(cls._container_project_notebooks_path()),
            ]
        )
        # <jupyter notebooks>/playground.ipynb
        playground_ipynb_template_mapping: Mapping = {
            "project_name": project_properties.name
        }
        playground_ipynb_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("playground.ipynb"), cls._container_project_notebooks_path()
            ),
            playground_ipynb_template_mapping,
        )
        # <jupyter notebooks>/playground.ipynb
        container = await container_with_files(
            container, (playground_ipynb_template,), is_overwrite
        )
        return SDKEnv(container, project_properties)


@final
@dagger.object_type
class Jupyter(PythonModule, JupyterInit):
    """Python SDK jupyter."""

    @final
    @classmethod
    def __container_project_notebooks_cache_path(cls) -> Path:
        """
        Get the container project notebooks cache path.

        Returns:
            The container project notebooks cache path.
        """
        return cls._container_project_path() / "notebooks_cache"

    @final
    @classmethod
    async def __pipeline(
        cls,
        project_directory: ProjectDirectoryType,
        platform: PlatformType,
        jupyter_port: PortType,
    ) -> dagger.Service:
        """
        Jupyter pipeline.

        Args:
            project_directory: Project directory.
            platform: The container platform.
            jupyter_port: Jupyter notebooks port.

        Returns:
            A container with the project jupyter command executed.
        """
        container, _ = await cls.sdk_module_env(project_directory, platform)
        container_project_notebooks_path_str = str(
            cls._container_project_notebooks_path()
        )
        jupyter_notebooks_cache_path_str = str(
            cls.__container_project_notebooks_cache_path()
        )
        container = (
            await container.with_mounted_cache(
                jupyter_notebooks_cache_path_str, JUPYTER_NOTEBOOKS_CACHE_VOLUME
            )
            .with_exec(
                [
                    "cp",
                    "--no-clobber",
                    "--archive",
                    f"{container_project_notebooks_path_str}/.",
                    f"{jupyter_notebooks_cache_path_str}/",
                ]
            )
            .sync()
        )
        jupyter_command = [
            "uv",
            "run",
            "--group",
            Jupyter.name(),
            "--module",
            "jupyter",
            "notebook",
            "--ip=0.0.0.0",
            f"--port={jupyter_port}",
            "--no-browser",
            "--allow-root",
            jupyter_notebooks_cache_path_str,
        ]
        return container.as_service(args=jupyter_command)

    @final
    @dagger.function
    async def service(
        self,
        project_directory: ProjectDirectoryType,
        backend_port: PortType = 8888,
        platform: PlatformType = PLATFORM_DEFAULT,
    ) -> dagger.Service:
        """Returns a jupyter notebooks service with the project of the provided source Directory."""
        return await self.__pipeline(project_directory, platform, backend_port)

    @final
    @dagger.function
    def notebooks(self, platform: PlatformType = PLATFORM_DEFAULT) -> dagger.Directory:
        """Returns jupyter notebooks Directory."""
        jupyter_notebooks_cache_path_str = str(
            self.__container_project_notebooks_cache_path()
        )
        export_path_str = str(Path("/export"))
        # TODO: decide what to do with folders: .Trash-0, .ipynb_checkpoints
        return (
            self._base_container(platform)
            .with_mounted_cache(
                jupyter_notebooks_cache_path_str, JUPYTER_NOTEBOOKS_CACHE_VOLUME
            )
            .with_exec(
                [
                    "cp",
                    "--archive",
                    f"{jupyter_notebooks_cache_path_str}/.",
                    f"{export_path_str}/",
                ]
            )
            .directory(export_path_str)
        )


sdk_module: Final = SDKModuleModule(init=JupyterInit, module=Jupyter)
