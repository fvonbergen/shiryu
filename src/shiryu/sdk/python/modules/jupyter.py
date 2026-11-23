"""jupyter module."""

from pathlib import Path, PurePosixPath
from typing import Annotated, Final, final

import dagger
from dagger_clients.core import CacheSharingMode, Changeset, Container, Directory, Service, core
from packaging.version import Version

from shiryu.sdk.common.utils import PROJECT_SOURCE_CODE_FOLDER

from ....utils.dagger.client import container_debian
from ....utils.dagger.directory import directory_with_new_file
from ....utils.dagger.file import TargetFile
from ....utils.template import Mapping, Template, TemplateFile
from ...common.context import DaggerModuleMetadata
from ...common.module import (
    PLATFORM_DAGGER_DEFAULT,
    PlatformDaggerType,
    PlatformType,
    ProjectMetadata,
    SCMType,
)
from ..context import DistributionPackage, PythonModuleInitContextDirectory
from ..module import PythonModule, PythonModuleInitializer
from ..templates import PYTHON_JINJA_ENVIRONMENT

PortType = int
PortDaggerType = Annotated[PortType, dagger.Doc("Jupyter notebooks port")]
PruneType = bool
PruneDaggerType = Annotated[PruneType, dagger.Doc("Prune jupyter cache")]

PROJECT_NOTEBOOKS_FOLDER: Final = "notebooks"
PORT_DAGGER_DEFAULT: Final = 8888
PRUNE_DAGGER_DEFAULT: Final = False
JUPYTER_CACHE_VOLUME = core().cache_volume("shiryu-jupyter")


class JupyterInitializer(PythonModuleInitializer):
    """JupyterInitializer class."""

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
        sdk_module_cls = Jupyter
        sdk_module_name = sdk_module_cls.name()
        return init_context_directory.evolve(
            dependency_groups=init_context_directory.dependency_groups.add(
                sdk_module_name,
                {
                    # https://github.com/jupyter/notebook/releases/tag/5.0.0
                    # >= 5.0.0 The Notebook will refuse to run as root unless the --allow-root flag
                    #   is given (#1115).
                    # https://github.com/jupyter/notebook/blob/5.0.0/setup.py#L26
                    DistributionPackage("notebook", Version("5.0.0"), Version("2.7")),
                    # TODO: versions not studied.
                    DistributionPackage("python-lsp-server", Version("0.1.1"), Version("0.0")),
                    # TODO: versions not studied.
                    # https://github.com/astral-sh/uv/blob/0.0.5/pyproject.toml#L10
                    DistributionPackage("uv", Version("0.0.5"), Version("3.8")),
                },
            ),
        )

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
        """Initializer class.

        Returns:
            The initializer class.
        """
        return JupyterInitializer

    @final
    @classmethod
    def __cache_folder(cls) -> str:
        """Get the juyter cache folder.

        Returns:
            The jupyter cache folder.
        """
        return "jupyter_cache"

    @final
    @classmethod
    async def __serve(
        cls, container: Container, jupyter_port: PortType, prune: PruneType
    ) -> Service:
        """Jupyter pipeline.

        Args:
            container: Project container.
            jupyter_port: Jupyter notebooks port.
            prune: Prune jupyter cache.

        Returns:
            A Service running the jupyter notebook server.
        """
        cache_folder = cls.__cache_folder()
        cache_path_str = f"/{cache_folder}"
        jupyter_command = cls._build_uv_run_command(
            [
                "jupyter",
                "notebook",
                "--ip=0.0.0.0",
                f"--port={jupyter_port}",
                "--no-browser",
                "--allow-root",
                cache_path_str,
            ]
        )
        container = container.with_exec(["mkdir", cache_path_str]).with_mounted_cache(
            cache_path_str, JUPYTER_CACHE_VOLUME, sharing=CacheSharingMode.LOCKED
        )
        container = (
            container.with_exec(["rm", "--recursive", "--force", f"{cache_path_str}/*"]).with_exec(
                ["cp", "--archive", "./.", f"{cache_path_str}/"]
            )
            if prune
            else container.with_exec(
                ["cp", "--no-clobber", "--archive", "./.", f"{cache_path_str}/"]
            )
        )

        return container.as_service(args=jupyter_command)

    @final
    @dagger.function(
        doc="Returns a jupyter notebooks service with the project of the provided source Directory."
    )
    async def service(
        self,
        *,
        backend_port: PortDaggerType = PORT_DAGGER_DEFAULT,
        prune: PruneDaggerType = PRUNE_DAGGER_DEFAULT,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> Service:
        """Returns a jupyter notebooks service with the project of the provided source Directory.

        Args:
            backend_port: Jupyter notebooks port.
            prune: Prune jupyter cache.
            platform: The container platform.

        Returns:
            A jupyter notebooks service.
        """
        exclude = [".git/"]
        container = await self._exec_container(self.source, exclude, platform)
        return await self.__serve(container, backend_port, prune)

    @final
    @dagger.function(doc="Returns a jupyter notebooks Directory.")
    async def changeset(
        self, *, platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT
    ) -> Changeset:
        """Returns the source code and jupyter notebooks changes.

        Args:
            platform: The container platform.

        Returns:
            The changes of the modified source code and notebooks.
        """
        source = self.source
        container_security_audit_file = await self._container_security_audit_file(source)
        cache_folder = self.__cache_folder()
        exported_cache_folder = f"exported_{cache_folder}"
        # TODO: decide what to do with folders: .Trash-0, .ipynb_checkpoints
        exported_cache = (
            (await container_debian(platform, container_security_audit_file))
            .with_exec(["mkdir", cache_folder])
            .with_mounted_cache(cache_folder, JUPYTER_CACHE_VOLUME, sharing=CacheSharingMode.LOCKED)
            .with_exec(["mkdir", exported_cache_folder])
            .with_exec(["cp", "--archive", f"{cache_folder}/.", f"{exported_cache_folder}/"])
            .directory(exported_cache_folder)
        )
        include = [PROJECT_SOURCE_CODE_FOLDER + "/**", PROJECT_NOTEBOOKS_FOLDER + "/**"]
        return exported_cache.filter(
            include=include, exclude=[".Trash/**", ".ipynb_checkpoints/**"]
        ).changes(source.filter(include=include))


sdk_module: Final = Jupyter
