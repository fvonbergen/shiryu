"""jupyter module."""

from pathlib import Path, PurePosixPath
from typing import Annotated, Final, final

import dagger

from ....utils.dagger.client import container_debian
from ....utils.dagger.directory import directory_with_new_file
from ....utils.template import Mapping, Template, TemplateFile
from ...common.context import DaggerModuleMetadata
from ...common.module import (
    PLATFORM_DAGGER_DEFAULT,
    PlatformDaggerType,
    PlatformType,
    ProjectDirectoryDaggerType,
    ProjectMetadata,
    SCMType,
)
from ..context import PythonModuleInitContextDirectory
from ..module import PythonModule, PythonModuleInitializer
from ..templates import PYTHON_JINJA_ENVIRONMENT

PortType = int
PortDaggerType = Annotated[PortType, dagger.Doc("Jupyter notebooks port")]

PROJECT_NOTEBOOKS_FOLDER: Final = "notebooks"
PORT_DAGGER_DEFAULT: Final = 8888
JUPYTER_NOTEBOOKS_CACHE_VOLUME = dagger.dag.cache_volume("shiryu-jupyter-debian-trixie")


class JupyterInitializer(PythonModuleInitializer):
    """JupyterInitializer class."""

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
        sdk_module_cls = Jupyter
        sdk_module_name = sdk_module_cls.name()
        return init_context_directory.evolve(
            dependency_groups=init_context_directory.dependency_groups.add(
                sdk_module_name, {"notebook", "python-lsp-server"}
            ),
        )

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

        # <jupyter notebooks>/playground.ipynb
        playground_ipynb_template_mapping: Mapping = {"project_name": project_metadata.name}
        playground_ipynb_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("playground.ipynb"), output_directory=PurePosixPath(PROJECT_NOTEBOOKS_FOLDER)
            ),
            playground_ipynb_template_mapping,
        )
        return directory_with_new_file(init_directory, playground_ipynb_template)


@dagger.object_type
class Jupyter(PythonModule):
    """Python SDK jupyter."""

    @staticmethod
    def _initializer_cls() -> type[JupyterInitializer]:
        """
        Initializer class.

        Returns:
            The initializer class.
        """
        return JupyterInitializer

    @final
    @classmethod
    def __notebooks_cache_folder(cls) -> str:
        """
        Get the container project notebooks cache folder.

        Returns:
            The container project notebooks cache folder.
        """
        return "notebooks_cache"

    @final
    @classmethod
    async def __serve(cls, container: dagger.Container, jupyter_port: PortType) -> dagger.Service:
        """
        Jupyter pipeline.

        Args:
            container: Project container.
            jupyter_port: Jupyter notebooks port.

        Returns:
            A container with the project jupyter command executed.
        """
        jupyter_notebooks_cache_folder = cls.__notebooks_cache_folder()
        container = (
            await container.with_mounted_cache(
                jupyter_notebooks_cache_folder, JUPYTER_NOTEBOOKS_CACHE_VOLUME
            )
            .with_exec(
                [
                    "cp",
                    "--no-clobber",
                    "--archive",
                    f"{PROJECT_NOTEBOOKS_FOLDER}/.",
                    f"{jupyter_notebooks_cache_folder}/",
                ]
            )
            .sync()
        )
        jupyter_command = cls._build_uv_run_command(
            [
                "jupyter",
                "notebook",
                "--ip=0.0.0.0",
                f"--port={jupyter_port}",
                "--no-browser",
                "--allow-root",
                jupyter_notebooks_cache_folder,
            ]
        )
        return container.as_service(args=jupyter_command)

    @final
    @dagger.function
    async def service(
        self,
        project_directory: ProjectDirectoryDaggerType,
        *,
        backend_port: PortDaggerType = PORT_DAGGER_DEFAULT,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> dagger.Service:
        """Returns a jupyter notebooks service with the project of the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        return await self.__serve(container, backend_port)

    @final
    @dagger.function
    def notebooks(
        self, *, platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT
    ) -> dagger.Directory:
        """Returns jupyter notebooks Directory."""
        jupyter_notebooks_cache_folder = self.__notebooks_cache_folder()
        export_path_str = "/export"
        # TODO: decide what to do with folders: .Trash-0, .ipynb_checkpoints
        return (
            container_debian(dagger.dag, platform)
            .with_mounted_cache(jupyter_notebooks_cache_folder, JUPYTER_NOTEBOOKS_CACHE_VOLUME)
            .with_exec(
                ["cp", "--archive", f"{jupyter_notebooks_cache_folder}/.", f"{export_path_str}/"]
            )
            .directory(export_path_str)
        )


sdk_module: Final = Jupyter
