"""builder module."""

from pathlib import Path
from typing import Annotated, Final, final

import dagger

from ...common.module import (
    PLATFORM_DEFAULT,
    GitHubActionsWorkflows,
    GitHubWorkflowId,
    GitLabJobsStages,
    GitLabStageId,
    PlatformType,
    ProjectDirectoryType,
    ProjectNameType,
    SCMListType,
    SDKEnv,
    SDKModuleModule,
)
from ..module import PythonModule, PythonModuleInit

RepositoryUrlType = Annotated[str, dagger.Doc("Repository to push distributable")]
RepositoryUserType = Annotated[str, dagger.Doc("Repository user")]
RepositoryPasswordType = Annotated[dagger.Secret, dagger.Doc("Repository password")]


class BuilderInit(PythonModuleInit):
    """Python SDK builder initializer."""

    @final
    @staticmethod
    def _project_distributable_folder() -> str:
        """
        Get the project distributable folder.

        Returns:
            Project distributable folder.
        """
        return "dist"

    @classmethod
    def _exclude_folders(cls) -> set[str]:
        """
        Folders to exclude from project.

        Returns:
            Folders to exclude from project.
        """
        return {cls._project_distributable_folder()}

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
        vcs_exclude_files_folders.update(
            {f"/{folder}/" for folder in cls._exclude_folders()}
        )
        return vcs_exclude_files_folders

    @final
    @classmethod
    def _container_project_distributable_path(cls) -> Path:
        """
        Get the container project distributable path.

        Returns:
            Container project distibutable path.
        """
        return cls._container_project_path() / cls._project_distributable_folder()

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
        python_packages = {"hatch"}
        container = container.with_exec(
            ["uv", "add", "--group", Builder.name(), *python_packages, "--no-sync"]
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
        github_actions_workflows = super()._github_actions_workflows(
            dagger_version, shiryu_version
        )
        github_actions = github_actions_workflows["actions"]
        github_workflows = github_actions_workflows["workflows"]
        github_action_builder_deploy = cls._build_github_action(
            Builder,
            Builder.deploy,  # pyright: ignore [reportArgumentType]
            dagger_version,
            shiryu_version,
            None,
        )
        github_action_builder_test = cls._build_github_action(
            Builder,
            Builder.test,  # pyright: ignore [reportArgumentType]
            dagger_version,
            shiryu_version,
            None,
        )
        github_actions.update(
            {github_action_builder_deploy, github_action_builder_test}
        )
        github_workflows.add(
            GitHubWorkflowId.DEPLOY,
            cls._build_github_workflow_job(
                github_action_builder_deploy, shiryu_version, None, tuple()
            ),
        )
        github_workflows.add(
            GitHubWorkflowId.QUALITY,
            cls._build_github_workflow_job(
                github_action_builder_test, shiryu_version, None, tuple()
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
        gitlab_jobs_stages = super()._gitlab_jobs_stages(dagger_version, shiryu_version)
        gitlab_jobs = gitlab_jobs_stages["jobs"]
        gitlab_stages = gitlab_jobs_stages["stages"]
        gitlab_job_builder_deploy = cls._build_gitlab_job(
            Builder,
            Builder.deploy,  # pyright: ignore [reportArgumentType]
            shiryu_version,
            (),
            None,
            (),
            None,
        )
        gitlab_job_builder_test = cls._build_gitlab_job(
            Builder,
            Builder.test,  # pyright: ignore [reportArgumentType]
            shiryu_version,
            (),
            None,
            (),
            None,
        )
        gitlab_jobs.update({gitlab_job_builder_deploy, gitlab_job_builder_test})
        gitlab_stages.add(
            GitLabStageId.DEPLOY,
            cls._build_gitlab_stage_job(
                GitLabStageId.DEPLOY, gitlab_job_builder_deploy
            ),
        )
        gitlab_stages.add(
            GitLabStageId.QUALITY,
            cls._build_gitlab_stage_job(GitLabStageId.QUALITY, gitlab_job_builder_test),
        )
        return {"jobs": gitlab_jobs, "stages": gitlab_stages}


@final
@dagger.object_type
class Builder(PythonModule, BuilderInit):
    """Python SDK builder."""

    @final
    @classmethod
    async def __pipeline(
        cls,
        project_directory: ProjectDirectoryType,
        platform: PlatformType,
        clean: bool,
    ) -> SDKEnv:
        """
        Build pipeline.

        Args:
            project_directory: Project directory.
            platform: The container platform.
            clean: Whether to clean project distributables before build or not.

        Returns:
            A container with the project build command executed.
        """
        container, project_properties = await cls.sdk_module_env(
            project_directory, platform
        )
        build_command = [
            "uv",
            "run",
            "--group",
            Builder.name(),
            "--module",
            "hatch",
            "build",
            str(cls._container_project_distributable_path() / platform),
        ]
        if clean:
            build_command.append("--clean")
        return SDKEnv(container.with_exec(build_command), project_properties)

    @final
    @classmethod
    async def __deploy(
        cls,
        container: dagger.Container,
        repository_url: RepositoryUrlType,
        repository_user: RepositoryUserType,
        repository_password: RepositoryPasswordType,
        platform: PlatformType,
    ) -> dagger.Container:
        """
        Deploy distributable.

        Args:
            container: SDK container with project distributable.
            repository_url: Repository to push distributable.
            repository_user: Repository user.
            repository_password: Repository password.
            platform: The container platform.

        Returns:
            A container with the project build command executed.
        """
        deploy_command = [
            "uv",
            "run",
            "--group",
            Builder.name(),
            "--module",
            "hatch",
            "publish",
            f"--user={repository_user}",
            f"--auth={repository_password}",
            f"--repo={repository_url}",
            str(cls._container_project_distributable_path() / platform),
        ]
        return container.with_exec(deploy_command)

    @dagger.function
    async def build(
        self,
        project_directory: ProjectDirectoryType,
        platform: PlatformType = PLATFORM_DEFAULT,
    ) -> dagger.Directory:
        """Build project distributable of the provided source Directory."""
        container, _ = await self.__pipeline(project_directory, platform, False)
        return self._container_project_directory(
            container, include=[f"{self._project_distributable_folder()}/"]
        )

    @dagger.function
    async def deploy(
        self,
        project_directory: ProjectDirectoryType,
        repository_url: RepositoryUrlType,
        repository_user: RepositoryUserType,
        repository_password: RepositoryPasswordType,
        platform: PlatformType = PLATFORM_DEFAULT,
    ) -> str:
        """Build and deploy project distributable of the provided source Directory."""
        container, _ = await self.__pipeline(project_directory, platform, True)
        await (
            await self.__deploy(
                container,
                repository_url,
                repository_user,
                repository_password,
                platform,
            )
        ).sync()
        return "Deploy successfull"

    @dagger.function
    async def test(
        self,
        project_directory: ProjectDirectoryType,
        platform: PlatformType = PLATFORM_DEFAULT,
    ) -> str:
        """Test the project installation process for the provided source Directory."""
        container, project_properties = await self.__pipeline(
            project_directory, platform, False
        )
        package_name = project_properties.name
        package_name_version = f"{package_name}=={project_properties.version}"
        await (
            container.with_exec(
                [
                    "uv",
                    "package",
                    "install",
                    "--no-build-isolation",
                    "--no-index",
                    f"--find-links={self._container_project_distributable_path() / platform}",
                    package_name_version,
                ]
            )
            .with_exec(["uv", "package", "uninstall", package_name])
            .sync()
        )
        return "Test build successfull"


sdk_module: Final = SDKModuleModule(init=BuilderInit, module=Builder)
