"""linter module."""

from pathlib import Path
from typing import Final, final

import dagger

from ....utils.dagger.container import container_with_file
from ....utils.template import Mapping, Template, TemplateFile
from ...common.module import (
    PLATFORM_DEFAULT,
    GitHubActionsWorkflows,
    GitHubWorkflowId,
    GitLabJobsStages,
    GitLabStageId,
    PlatformType,
    ProjectType,
    SCMListType,
    SDKEnv,
    SDKModuleModule,
)
from ..module import ModulesPythonPackages, PythonModule, PythonModuleInit
from ..templates import PYTHON_JINJA_ENVIRONMENT


class LinterInit(PythonModuleInit):
    """Python SDK linter initializer."""

    @final
    @staticmethod
    def __cache_folder() -> str:
        """
        Get the linter cache folder.

        Returns:
            The linter cache folder.
        """
        return ".ruff_cache"

    @classmethod
    def _vcs_exclude_files_folders(cls) -> set[str]:
        """
        Files and folders to exclude from vcs.

        Returns:
            A list of files and folders to exclude from vcs.
        """
        vcs_exclude_files_folders = super(LinterInit, cls)._vcs_exclude_files_folders()
        vcs_exclude_files_folders.update({f"/{cls.__cache_folder()}/"})
        return vcs_exclude_files_folders

    @final
    @classmethod
    def _ruff_toml_template_file(cls) -> TemplateFile:
        """
        ruff.toml template file.

        Returns:
            The ruff.toml template file.
        """
        return TemplateFile(Path("ruff.toml"), cls._container_project_path())

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
        _sdk_env = await super(LinterInit, cls)._module_init(sdk_env, is_overwrite, scm)
        container = _sdk_env.container
        project_properties = _sdk_env.project_properties
        # ruff.toml
        ruff_toml_template_mapping: Mapping = {"cache_folder": cls.__cache_folder()}
        ruff_toml_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls._ruff_toml_template_file(),
            ruff_toml_template_mapping,
        )
        container = await container_with_file(
            container, ruff_toml_template, is_overwrite
        )
        return SDKEnv(container, project_properties)

    @classmethod
    def _github_actions_workflows(
        cls, dagger_version: str, shiryu_version: str
    ) -> GitHubActionsWorkflows:
        """
        Get the GitHub actions and workflows.

        Args:
            dagger_version: Dagger version.
            shiryu_version: Shiryu version.

        Returns:
            GitHub actions and workflows.
        """
        github_actions_workflows = super(LinterInit, cls)._github_actions_workflows(
            dagger_version, shiryu_version
        )
        github_actions = github_actions_workflows["actions"]
        github_workflows = github_actions_workflows["workflows"]
        github_action = cls._build_github_action(
            Linter,
            Linter.lint,  # pyright: ignore [reportArgumentType]
            dagger_version,
            shiryu_version,
            None,
        )
        github_actions.add(github_action)
        github_workflows.add(
            GitHubWorkflowId.QUALITY,
            cls._build_github_workflow_job(
                github_action, shiryu_version, None, tuple()
            ),
        )
        return {"actions": github_actions, "workflows": github_workflows}

    @classmethod
    def _gitlab_jobs_stages(
        cls, dagger_version: str, shiryu_version: str
    ) -> GitLabJobsStages:
        """
        Get the GitLab jobs and stages.

        Args:
            dagger_version: Dagger version.
            shiryu_version: Shiryu version.

        Returns:
            GitLab jobs and stages.
        """
        gitlab_jobs_stages = super(LinterInit, cls)._gitlab_jobs_stages(
            dagger_version, shiryu_version
        )
        gitlab_jobs = gitlab_jobs_stages["jobs"]
        gitlab_stages = gitlab_jobs_stages["stages"]
        gitlab_job = cls._build_gitlab_job(
            Linter,
            Linter.lint,  # pyright: ignore [reportArgumentType]
            shiryu_version,
            (),
            None,
            (),
            None,
        )
        gitlab_jobs.update({gitlab_job})
        gitlab_stages.add(
            GitLabStageId.QUALITY,
            cls._build_gitlab_stage_job(GitLabStageId.QUALITY, gitlab_job),
        )
        return {"jobs": gitlab_jobs, "stages": gitlab_stages}


@final
@dagger.object_type
class Linter(PythonModule, LinterInit):
    """Python SDK linter."""

    @classmethod
    def _base_container_modules_python_packages(cls) -> ModulesPythonPackages:
        """
        Base container modules python packages.

        Returns:
            Base container modules python packages.
        """
        base_container_modules_python_packages = super(
            Linter, cls
        )._base_container_modules_python_packages()
        base_container_modules_python_packages[Linter.name()] = {"ruff"}
        return base_container_modules_python_packages

    @final
    @classmethod
    async def __pipeline(
        cls, project: ProjectType, platform: PlatformType, fix: bool
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
        container, _ = await cls.sdk_module_env(project, platform)
        ruff_toml_file_name = cls._ruff_toml_template_file().file_name
        ruff_check_command = [
            "uv",
            "run",
            "--no-project",
            "--module",
            "ruff",
            "check",
            "--show-fixes",
            f"--config={ruff_toml_file_name}",
            ".",
        ]
        ruff_format_command = [
            "uv",
            "run",
            "--no-project",
            "--module",
            "ruff",
            "format",
            f"--config={ruff_toml_file_name}",
            ".",
        ]
        if fix:
            ruff_check_command = [*ruff_check_command, "--fix"]
        else:
            ruff_format_command = [*ruff_format_command, "--diff"]
        return await (
            container.with_exec(ruff_check_command)
            .with_exec(ruff_format_command)
            .sync()
        )

    @final
    @dagger.function
    async def lint(
        self, project: ProjectType, platform: PlatformType = PLATFORM_DEFAULT
    ) -> str:
        """Run linter analysis in the project of the provided source Directory."""
        await self.__pipeline(project, platform, False)
        return "Lint successfull"

    @final
    @dagger.function
    async def fix(
        self, project: ProjectType, platform: PlatformType
    ) -> dagger.Directory:
        """Run linter fixes in the project of the provided source Directory."""
        container = await self.__pipeline(project, platform, True)
        return await container.directory(str(self._container_project_path()))


sdk_module: Final = SDKModuleModule(init=LinterInit, module=Linter)
