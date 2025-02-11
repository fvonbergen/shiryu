"""test_install module."""

from ..common import PlatformType, ProjectType
from .base import PythonBase
from .build import PythonBuild


class PythonTestInstall(PythonBase):
    """PythonTestInstall class."""

    @classmethod
    async def test_install(cls, project: ProjectType, platform: PlatformType) -> str:
        """Test the project installation process for the provided source Directory."""
        container, project_properties = await PythonBuild._pipeline(project, platform)
        package_name = project_properties["name"]
        package_name_version = f"{package_name}=={project_properties['version']}"
        await (
            container.with_exec(
                [
                    "uv",
                    "pip",
                    "install",
                    "--no-build-isolation",
                    "--no-index",
                    f"--find-links={PythonBuild.project_distributable_path() / platform}",
                    package_name_version,
                ]
            )
            .with_exec(["uv", "pip", "uninstall", package_name])
            .sync()
        )
        return "Test install successfull"
