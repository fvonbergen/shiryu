"""main module."""

import asyncio
from pathlib import Path
from typing import Annotated, List

import dagger

from .dagger_utils import (
    FSDirectory,
    container_with_file,
    directory_with_file,
    is_container_with_file,
)
from .template import Mapping, Template, TemplateFile


@dagger.enum_type
class SDK(dagger.Enum):
    """SDK options."""

    C = "c"
    PYTHON = "python"


# class Platform(Enum):
#     """Platform options."""
#
#     # Reference: https://go.dev/wiki/MinimumRequirements#amd64
#     AMD64 = "linux/amd64"
#     # Reference: https://go.dev/wiki/GoArm
#     ARM32V7 = "linux/arm/v7"
#     ARM64 = "linux/arm64"


class Project:
    """Project class."""

    @staticmethod
    def project_path() -> Path:
        """
        Get the container project path.

        Returns:
            The container project path.
        """
        return Path("/project")

    @staticmethod
    def source_folder() -> str:
        """
        Get the source folder name.

        Returns:
            The source folder name.
        """
        return "src"

    @classmethod
    def project_source_path(cls) -> Path:
        """
        Get the container project source path.

        Returns:
            The container project source path.
        """
        return cls.project_path() / cls.source_folder()

    @classmethod
    def vcs_exclude_files_folders(cls) -> List[str]:
        """
        Files and folders to exclude from vcs.

        Returns:
            A list of files and folders to exclude from vcs.
        """
        return []

    @classmethod
    def github_actions_jobs(cls) -> List[Template]:
        """
        Get the github actions jobs files.

        Returns:
            A list of github actions job files
        """
        return []

    @classmethod
    def project_env(cls, platform: str) -> dagger.Container:
        """
        Get a container with the project environment set.

        Args:
            platform: The container platform.

        Returns:
            A container with the project environment set.
        """
        project_path_str = str(cls.project_path())
        apt_install = ("apt", "install", "--assume-yes", "--no-install-recommends")
        base_packages = ("git",)
        return (
            dagger.dag.container(platform=dagger.Platform(platform))
            .from_("debian:trixie-slim")
            .with_exec(["mkdir", "--parents", project_path_str])
            .with_exec(["apt", "update"])
            .with_exec([*apt_install, *base_packages])
            .with_exec(["apt", "autoremove"])
            .with_exec(["apt", "clean"])
            .with_workdir(project_path_str)
        )

    @classmethod
    async def _init(cls, project_name: str, platform: str) -> FSDirectory:
        """
        Get a directory that contains an initialized project.

        Args:
            project_name: The project name.
            platform: The container platform.

        Returns:
            A directory with an initialized project.
        """
        project_source_path_str = str(cls.project_source_path())
        _gitignore_template_mapping: Mapping = {
            "exclude": cls.vcs_exclude_files_folders()
        }
        _gitignore_template = Template(
            TemplateFile(Path(".gitignore"), cls.project_path()),
            _gitignore_template_mapping,
        )
        container = (
            cls.project_env(platform)
            .with_exec(["git", "init", "--initial-branch", "main"])
            .with_exec(["mkdir", "--parents", project_source_path_str])
        )
        container = await container_with_file(container, _gitignore_template, False)
        return FSDirectory.from_container(cls.project_path(), container)


class Python(Project):
    """Python class."""

    @classmethod
    def vcs_exclude_files_folders(cls) -> List[str]:
        """
        Files and folders to exclude from vcs.

        Returns:
            A list of files and folders to exclude from vcs.
        """
        vcs_exclude_files_folders = super(Python, cls).vcs_exclude_files_folders()
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
    def py_typed_template_file(cls, project_name: str) -> TemplateFile:
        """pyproject.toml template file."""
        return TemplateFile(Path("py.typed"), cls.project_source_path() / project_name)

    @classmethod
    async def python_env(
        cls, project: dagger.Directory, platform: str
    ) -> dagger.Container:
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
            .with_mounted_directory(project_path_str, project)
        )
        # Project layers.
        if not await is_container_with_file(container, pyproject_toml_template_file):
            exception_message = (
                f"Project is not initialized. Missing: {pyproject_toml_file_name}"
            )
            raise Exception(exception_message)
        return container.with_exec(
            [
                "uv",
                "pip",
                "install",
                "--no-sources",
                "--requirement",
                pyproject_toml_file_name,
            ]
        )

    @classmethod
    async def _init(cls, project_name: str, platform: str) -> FSDirectory:
        """
        Get a directory that contains an initialized project.

        Args:
            project_name: The project name.
            platform: The container platform.

        Returns:
            A directory with an initialized project.
        """
        project_source_package_path = cls.project_source_path() / project_name
        pyproject_toml_template_mapping: Mapping = {"project_name": project_name}
        pyproject_toml_template = Template(
            cls.pyproject_toml_template_file(), pyproject_toml_template_mapping
        )
        fs_directory = (
            await super(Python, cls)._init(project_name, platform)
        ).with_new_directory(project_source_package_path)
        fs_directory = await directory_with_file(fs_directory, pyproject_toml_template)
        py_typed_template = Template(cls.py_typed_template_file(project_name), {})
        return await directory_with_file(fs_directory, py_typed_template)


class PythonBuild(Python):
    """PythonBuild class."""

    @staticmethod
    def project_distributable_folder() -> str:
        """
        Get the project distributable folder.

        Returns:
            Project distributable folder.
        """
        return "dist"

    @classmethod
    def vcs_exclude_files_folders(cls) -> List[str]:
        """
        Files and folders to exclude from vcs.

        Returns:
            A list of files and folders to exclude from vcs.
        """
        vcs_exclude_files_folders = super(Python, cls).vcs_exclude_files_folders()
        return [
            *vcs_exclude_files_folders,
            "/.ruff_cache/",
            cls.project_distributable_folder(),
        ]

    @classmethod
    def project_distributable_path(cls) -> Path:
        """
        Get the project distributable path.

        Returns:
            Project distibutable path.
        """
        return cls.project_path() / cls.project_distributable_folder()

    @classmethod
    async def pipeline(
        cls, project: dagger.Directory, platform: str
    ) -> dagger.Container:
        """Build pipeline."""
        container = (await cls.python_env(project, platform)).with_exec(
            ["uv", "pip", "install", "build", "twine"]
        )
        build_command = [
            "python",
            "-m",
            "build",
            "--installer=uv",
            f"--outdir={cls.project_distributable_path() / platform}",
        ]
        return container.with_exec(build_command)

    @classmethod
    async def build(cls, project: dagger.Directory, platform: str) -> dagger.Directory:
        """Run build in the project of the provided source Directory."""
        container = await cls.pipeline(project, platform)
        return await container.directory(str(cls.project_path()))


class PythonLint(Python):
    """PythonLint class."""

    @staticmethod
    def cache_folder() -> str:
        """
        Get the linter cache folder.

        Returns:
            The linter cache folder.
        """
        return ".ruff_cache"

    @classmethod
    def vcs_exclude_files_folders(cls) -> List[str]:
        """
        Files and folders to exclude from vcs.

        Returns:
            A list of files and folders to exclude from vcs.
        """
        vcs_exclude_files_folders = super(PythonLint, cls).vcs_exclude_files_folders()
        return [*vcs_exclude_files_folders, f"/{cls.cache_folder()}/"]

    @classmethod
    async def pipeline(
        cls, project: dagger.Directory, platform: str, fix: bool
    ) -> dagger.Container:
        """
        Lint pipeline.

        Args:
            project: Project directory.
            platform: The container platform.
            fix: Whether to fix the project files or not.

        Returns:
            A container with the project lint command executed.
        """
        ruff_toml_template = Template(
            TemplateFile(Path("ruff.toml"), cls.project_path()),
            {"cache_folder": cls.cache_folder()},
        )
        ruff_toml_file_name = ruff_toml_template.template_file.file_name
        ruff_check_command = [
            "ruff",
            "check",
            "--show-fixes",
            f"--config={ruff_toml_file_name}",
            ".",
        ]
        ruff_format_command = ["ruff", "format", f"--config={ruff_toml_file_name}", "."]
        if fix:
            ruff_check_command = [*ruff_check_command, "--fix"]
        else:
            ruff_format_command = [*ruff_format_command, "--diff"]
        container = (await cls.python_env(project, platform)).with_exec(
            ["uv", "pip", "install", "ruff"]
        )
        container = await container_with_file(container, ruff_toml_template)
        return container.with_exec(ruff_check_command).with_exec(ruff_format_command)

    @classmethod
    async def lint(cls, project: dagger.Directory, platform: str) -> str:
        """Run lint checks in the project of the provided source Directory."""
        await cls.pipeline(project, platform, True)
        return "Lint successfull"

    @classmethod
    async def lint_fix(
        cls, project: dagger.Directory, platform: str
    ) -> dagger.Directory:
        """Run lint fixes in the project of the provided source Directory."""
        container = await cls.pipeline(project, platform, True)
        return await container.directory(str(cls.project_path()))


class PythonCheck(Python):
    """PythonCheck class."""

    @classmethod
    async def pipeline(
        cls, project: dagger.Directory, platform: str
    ) -> dagger.Container:
        """
        Check pipeline.

        Args:
            project: Project directory.
            platform: The container platform.

        Returns:
            A container with the project check command executed.
        """
        # folders = ["src", "tests"]
        folders = [f"{cls.project_source_path().relative_to(cls.project_path())}"]
        contents = f"""
 [mypy]
 files = {", ".join(folders)}
 show_error_codes = True
 explicit_package_bases = True"""
        # MYPYPATH={PROJECT_SOURCE_CODE_FOLDER} mypy --config-file={mypy_ini_file.file_name} {' '.join(params)}
        mypy_command = ["mypy", "--config-file=mypy.ini"]
        return (
            (await cls.python_env(project, platform))
            .with_exec(["uv", "pip", "install", "mypy"])
            .with_new_file(path="/project/mypy.ini", contents=contents)
            .with_exec(mypy_command)
        )

    @classmethod
    async def check(cls, project: dagger.Directory, platform: str) -> str:
        """Run type checks in the project of the provided source Directory."""
        await cls.pipeline(project, platform)
        return "Check successfull"


class PythonInit(Python):
    """PythonInit class."""

    @classmethod
    async def init(cls, project_name: str, platform: str) -> dagger.Directory:
        """Returns a directory with a new project initialized."""
        commands = [PythonBuild, PythonLint, PythonCheck]
        fs_directory = await cls._init(project_name, platform)
        for command in commands:
            fs_directory.with_directory(await command._init(project_name, platform))
        return fs_directory.directory


class Build:
    """Init class."""

    @dagger.function
    async def build(
        self,
        project: Annotated[dagger.Directory, dagger.Doc("Project location")],
        platform: Annotated[
            str, dagger.Doc("Platform config OS and architecture in a Container")
        ] = "linux/amd64",
        sdk: Annotated[SDK, dagger.Doc("Software Development Kit")] = SDK.PYTHON,
    ) -> dagger.Directory:
        """Initialize project."""
        if sdk == SDK.PYTHON:
            return await PythonBuild.build(project, platform)
        else:
            exception_message = f"Not implemented sdk: {sdk}"
            raise Exception(exception_message)


class Lint:
    """Lint class."""

    @dagger.function
    async def lint(
        self,
        project: Annotated[dagger.Directory, dagger.Doc("Project location")],
        platform: Annotated[
            str, dagger.Doc("Platform config OS and architecture in a Container")
        ] = "linux/amd64",
        sdk: Annotated[SDK, dagger.Doc("Software Development Kit")] = SDK.PYTHON,
    ) -> str:
        """Run linter checks in the project of the provided source Directory."""
        if sdk == SDK.PYTHON:
            return await PythonLint.lint(project, platform)
        else:
            exception_message = f"Not implemented sdk: {sdk}"
            raise Exception(exception_message)

    @dagger.function
    async def lint_fix(
        self,
        project: Annotated[dagger.Directory, dagger.Doc("Project location")],
        platform: Annotated[
            str, dagger.Doc("Platform config OS and architecture in a Container")
        ] = "linux/amd64",
        sdk: Annotated[SDK, dagger.Doc("Software Development Kit")] = SDK.PYTHON,
    ) -> dagger.Directory:
        """Run linter fixes in the project of the provided source Directory."""
        if sdk == SDK.PYTHON:
            return await PythonLint.lint_fix(project, platform)
        else:
            exception_message = f"Not implemented sdk: {sdk}"
            raise Exception(exception_message)


class Check:
    """Check class."""

    @dagger.function
    async def check(
        self,
        project: Annotated[dagger.Directory, dagger.Doc("Project location")],
        platform: Annotated[
            str, dagger.Doc("Platform config OS and architecture in a Container")
        ] = "linux/amd64",
        sdk: Annotated[SDK, dagger.Doc("Software Development Kit")] = SDK.PYTHON,
    ) -> str:
        """Run type checks in the project of the provided source Directory."""
        if sdk == SDK.PYTHON:
            return await PythonCheck.check(project, platform)
        else:
            exception_message = f"Not implemented sdk: {sdk}"
            raise Exception(exception_message)


class Init:
    """Init class."""

    @dagger.function
    async def init(
        self,
        project_name: Annotated[str, dagger.Doc("Project name")],
        platform: Annotated[
            str, dagger.Doc("Platform config OS and architecture in a Container")
        ] = "linux/amd64",
        sdk: Annotated[SDK, dagger.Doc("Software Development Kit")] = SDK.PYTHON,
    ) -> dagger.Directory:
        """Initialize project."""
        if sdk == SDK.PYTHON:
            return await PythonInit.init(project_name, platform)
        else:
            exception_message = f"Not implemented sdk: {sdk}"
            raise Exception(exception_message)


@dagger.object_type
class Shiryu(Build, Check, Init, Lint):
    """Shiryu class."""

    @dagger.function
    async def quality(
        self,
        project: Annotated[dagger.Directory, dagger.Doc("Project location")],
        platform: Annotated[
            str, dagger.Doc("Platform config OS and architecture in a Container")
        ] = "linux/amd64",
        sdk: Annotated[SDK, dagger.Doc("Software Development Kit")] = SDK.PYTHON,
    ) -> str:
        """Run quality checks in the project of the provided source Directory."""
        await asyncio.gather(
            self.lint(project, platform, sdk), self.check(project, platform, sdk)
        )
        return "Quality successfull"
