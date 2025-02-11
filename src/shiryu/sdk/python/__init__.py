"""python subpackage."""

import dagger

from ..common import PlatformType, ProjectNameType
from .build import PythonBuild
from .check import PythonCheck
from .lint import PythonLint
from .test_install import PythonTestInstall


class Python(PythonBuild, PythonCheck, PythonLint, PythonTestInstall):
    """Python class."""

    @classmethod
    async def init(
        cls, project_name: ProjectNameType, platform: PlatformType
    ) -> dagger.Directory:
        """Returns a directory with a new project initialized."""
        # TODO: project_name will be returned by python_env when issue is fixed (https://github.com/dagger/dagger/pull/9617)
        container, _ = await cls.python_env(None, platform)
        container = await super(Python, cls)._init(container, project_name)
        return container.directory(str(cls.project_path()))
