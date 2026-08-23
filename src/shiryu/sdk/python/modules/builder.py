"""builder module."""

from pathlib import PurePosixPath
from typing import Annotated, Final, final

import dagger

from ....utils.dagger.client import container_uv
from ...common.context import DaggerModuleMetadata
from ...common.module import (
    PLATFORM_DAGGER_DEFAULT,
    PlatformDaggerType,
    PlatformType,
    ProjectDirectoryDaggerType,
    ProjectMetadata,
)
from ...common.scm import (
    GitHubWorkflowId,
    GitLabStageId,
    build_github_action,
    build_github_workflow_checkout_job,
    build_github_workflow_job,
    build_gitlab_job,
    build_gitlab_stage_job,
)
from ..context import PythonModuleInitContextDirectory
from ..module import PythonModule, PythonModuleInitializer

RepositoryUrlDaggerType = Annotated[str, dagger.Doc("Repository to push distributable")]
RepositoryUserDaggerType = Annotated[str, dagger.Doc("Repository user")]
RepositoryPasswordDaggerType = Annotated[dagger.Secret, dagger.Doc("Repository password")]

PROJECT_DISTRIBUTABLE_FOLDER: Final = "dist"


class BuilderInitializer(PythonModuleInitializer):
    """Builderinitializer class."""

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
        dagger_version = shiryu_metadata.dagger_version
        shiryu_version = shiryu_metadata.git_tag_or_branch
        sdk_module_cls = Builder
        sdk_language = sdk_module_cls._sdk_name()
        sdk_module_name = sdk_module_cls.name()
        sdk_module_function_publish = sdk_module_cls.publish
        sdk_module_function_test = sdk_module_cls.test
        github_action_builder_publish = build_github_action(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function_publish,
            dagger_version=dagger_version,
            shiryu_version=shiryu_version,
            export_path=None,
        )
        github_action_builder_test = build_github_action(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function_test,
            dagger_version=dagger_version,
            shiryu_version=shiryu_version,
            export_path=None,
        )
        gitlab_job_builder_publish = build_gitlab_job(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function_publish,
            shiryu_version=shiryu_version,
            variables=(),
            pre_script=(),
            export_path=None,
            post_script=(),
            artifacts=None,
        )
        gitlab_job_builder_test = build_gitlab_job(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function_test,
            shiryu_version=shiryu_version,
            variables=(),
            pre_script=(),
            export_path=None,
            post_script=(),
            artifacts=None,
        )
        pre_steps = (build_github_workflow_checkout_job(),)

        return init_context_directory.evolve(
            vcs=init_context_directory.vcs.evolve(
                exclude_files_folders=init_context_directory.vcs.exclude_files_folders
                | {f"/{PROJECT_DISTRIBUTABLE_FOLDER}/"}
            ),
            scm=init_context_directory.scm.evolve(
                github_actions_workflows=init_context_directory.scm.github_actions_workflows.evolve(
                    actions=init_context_directory.scm.github_actions_workflows.actions
                    | {github_action_builder_publish, github_action_builder_test},
                    workflows=init_context_directory.scm.github_actions_workflows.workflows.add(
                        GitHubWorkflowId.RELEASE,
                        build_github_workflow_job(
                            sdk_language=sdk_language,
                            github_action=github_action_builder_publish,
                            shiryu_version=shiryu_version,
                            job_environment=None,
                            pre_steps=pre_steps,
                            post_steps=(),
                        ),
                    ).add(
                        GitHubWorkflowId.QUALITY,
                        build_github_workflow_job(
                            sdk_language=sdk_language,
                            github_action=github_action_builder_test,
                            shiryu_version=shiryu_version,
                            job_environment=None,
                            pre_steps=pre_steps,
                            post_steps=(),
                        ),
                    ),
                ),
                gitlab_jobs_stages=init_context_directory.scm.gitlab_jobs_stages.evolve(
                    jobs=init_context_directory.scm.gitlab_jobs_stages.jobs
                    | {gitlab_job_builder_publish, gitlab_job_builder_test},
                    stages=init_context_directory.scm.gitlab_jobs_stages.stages.add(
                        GitLabStageId.RELEASE,
                        build_gitlab_stage_job(
                            gitlab_stage_id=GitLabStageId.RELEASE,
                            gitlab_job=gitlab_job_builder_publish,
                        ),
                    ).add(
                        GitLabStageId.QUALITY,
                        build_gitlab_stage_job(
                            gitlab_stage_id=GitLabStageId.QUALITY,
                            gitlab_job=gitlab_job_builder_test,
                        ),
                    ),
                ),
            ),
            dependency_groups=init_context_directory.dependency_groups.add(
                sdk_module_name,
                {
                    # All versions supported
                    "hatch"
                },
            ),
        )


@dagger.object_type
class Builder(PythonModule):
    """Python SDK builder."""

    @staticmethod
    def _initializer_cls() -> type[BuilderInitializer]:
        """Initializer class.

        Returns:
            The initializer class.
        """
        return BuilderInitializer

    @final
    @classmethod
    def __build_container(
        cls, container: dagger.Container, platform: dagger.Platform, clean: bool
    ) -> dagger.Container:
        """Build wheel in the distributable directory container.

        Args:
            container: Project container.
            platform: The container platform.
            clean: Whether to clean project distributables before build or not.

        Returns:
            A container with the distributable directory.
        """
        build_command = cls._build_uv_run_command(
            ["hatch", "build", str(PurePosixPath(PROJECT_DISTRIBUTABLE_FOLDER) / platform)]
        )
        if clean:
            build_command.append("--clean")
        return container.with_exec(build_command)

    @final
    @classmethod
    def __build(cls, container: dagger.Container, platform: dagger.Platform) -> dagger.Directory:
        """Build wheel in the distributable directory.

        Args:
            container: Project container.
            platform: The container platform.

        Returns:
            A directory with the distributable directory.
        """
        return (
            cls.__build_container(container, platform, False)
            .directory(".")
            .filter(include=[PROJECT_DISTRIBUTABLE_FOLDER])
        )

    @final
    @classmethod
    async def __publish(
        cls,
        container: dagger.Container,
        repository_url: RepositoryUrlDaggerType,
        repository_user: RepositoryUserDaggerType,
        repository_password: RepositoryPasswordDaggerType,
        platform: PlatformType,
    ) -> None:
        """Publish distributable.

        Args:
            container: SDK container with project distributable.
            repository_url: Repository to push distributable.
            repository_user: Repository user.
            repository_password: Repository password.
            platform: The container platform.

        Returns:
            A container with the project build command executed.
        """
        container = cls.__build_container(container, platform, True)
        deploy_command = cls._build_uv_run_command(
            [
                "hatch",
                "publish",
                f"--user={repository_user}",
                f"--repo={repository_url}",
                str(PurePosixPath(PROJECT_DISTRIBUTABLE_FOLDER) / platform),
            ]
        )
        await (
            container.with_secret_variable("HATCH_INDEX_AUTH", repository_password)
            .with_exec(deploy_command)
            .sync()
        )

    @dagger.function
    async def build(
        self,
        project_directory: ProjectDirectoryDaggerType,
        *,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> dagger.Directory:
        """Build project distributable of the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        return self.__build(container, platform)

    @dagger.function
    async def publish(
        self,
        project_directory: ProjectDirectoryDaggerType,
        repository_url: RepositoryUrlDaggerType,
        repository_user: RepositoryUserDaggerType,
        repository_password: RepositoryPasswordDaggerType,
        *,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> str:
        """Build and publish project distributable of the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        await self.__publish(
            container, repository_url, repository_user, repository_password, platform
        )
        return "Publish successfull"

    @dagger.function
    async def test(
        self,
        project_directory: ProjectDirectoryDaggerType,
        *,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> str:
        """Test the project installation process for the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        directory = self.__build(container, platform)
        project_metadata = await self._get_project_metadata(project_directory, platform)
        package_name = project_metadata.name
        package_name_version = f"{package_name}=={project_metadata.version}"
        await (
            container_uv(dagger.dag, platform)
            .with_directory(".", directory)
            .with_exec(["uv", "venv"])
            .with_exec(
                [
                    "uv",
                    "pip",
                    "install",
                    "--no-build-isolation",
                    f"--find-links={PurePosixPath(PROJECT_DISTRIBUTABLE_FOLDER) / platform}",
                    package_name_version,
                ]
            )
            .with_exec(["uv", "pip", "uninstall", package_name])
            .sync()
        )
        return "Test build successfull"


sdk_module: Final = Builder
