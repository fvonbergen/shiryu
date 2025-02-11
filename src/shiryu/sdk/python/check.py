"""check module."""

from pathlib import Path

import dagger

from ...utils.dagger import container_with_file
from ...utils.template import Mapping, Template, TemplateFile
from ..common import PlatformType, ProjectNameType, ProjectType
from .base import PythonBase
from .templates import PYTHON_JINJA_ENVIRONMENT


class PythonCheck(PythonBase):
    """PythonCheck class."""

    @classmethod
    def __mypy_ini_template_file(cls) -> TemplateFile:
        """pyproject.toml template file."""
        return TemplateFile(Path("mypy.ini"), cls.project_path())

    @classmethod
    async def _init(
        cls, container: dagger.Container, project_name: ProjectNameType
    ) -> dagger.Container:
        """
        Get a container that has an initialized project.

        Args:
            container: Container to initialize.
            project_name: The project name.

        Returns:
            A container with an initialized project.
        """
        container = await super(PythonCheck, cls)._init(container, project_name)
        # mypy.ini
        # folders = ["src", "tests"]
        project_folders = [
            f"{cls.project_source_path().relative_to(cls.project_path())}"
        ]
        mypy_init_template_mapping: Mapping = {"project_folders": project_folders}
        mypy_ini_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls.__mypy_ini_template_file(),
            mypy_init_template_mapping,
        )
        return await container_with_file(container, mypy_ini_template)

    @classmethod
    async def __pipeline(
        cls, project: ProjectType, platform: PlatformType
    ) -> dagger.Container:
        """
        Check pipeline.

        Args:
            project: Project directory.
            platform: The container platform.

        Returns:
            A container with the project check command executed.
        """
        container, project_properties = await cls.python_env(project, platform)
        container = await PythonCheck._init(container, project_properties["name"])
        # MYPYPATH={PROJECT_SOURCE_CODE_FOLDER} mypy --config-file={mypy_ini_file.file_name} {' '.join(params)}
        mypy_command = [
            "mypy",
            f"--config-file={cls.__mypy_ini_template_file().file_name}",
        ]
        container = container.with_exec(["uv", "pip", "install", "mypy"])
        return await container.with_exec(mypy_command).sync()

    @classmethod
    async def check(cls, project: ProjectType, platform: PlatformType) -> str:
        """Run type checks in the project of the provided source Directory."""
        await cls.__pipeline(project, platform)
        return "Check successfull"
