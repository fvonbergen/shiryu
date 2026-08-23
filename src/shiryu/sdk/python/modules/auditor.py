"""auditor module."""

from typing import Final, final

import dagger

from ...common.context import DaggerModuleMetadata
from ...common.module import (
    PLATFORM_DAGGER_DEFAULT,
    PlatformDaggerType,
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


class AuditorInitializer(PythonModuleInitializer):
    """AuditorInitializer class."""

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
        sdk_module_cls = Auditor
        sdk_language = sdk_module_cls._sdk_name()
        sdk_module_name = sdk_module_cls.name()
        sdk_module_function = sdk_module_cls.audit
        github_action = build_github_action(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function,
            dagger_version=shiryu_metadata.dagger_version,
            shiryu_version=shiryu_metadata.git_tag_or_branch,
            export_path=None,
        )
        gitlab_job = build_gitlab_job(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function,
            shiryu_version=shiryu_metadata.git_tag_or_branch,
            variables=(),
            pre_script=(),
            export_path=None,
            post_script=(),
            artifacts=None,
        )
        pre_steps = (build_github_workflow_checkout_job(),)

        return init_context_directory.evolve(
            scm=init_context_directory.scm.evolve(
                github_actions_workflows=init_context_directory.scm.github_actions_workflows.evolve(
                    actions=init_context_directory.scm.github_actions_workflows.actions
                    | {github_action},
                    workflows=init_context_directory.scm.github_actions_workflows.workflows.add(
                        GitHubWorkflowId.QUALITY,
                        build_github_workflow_job(
                            sdk_language=sdk_language,
                            github_action=github_action,
                            shiryu_version=shiryu_metadata.git_tag_or_branch,
                            job_environment=None,
                            pre_steps=pre_steps,
                            post_steps=(),
                        ),
                    ),
                ),
                gitlab_jobs_stages=init_context_directory.scm.gitlab_jobs_stages.evolve(
                    jobs=init_context_directory.scm.gitlab_jobs_stages.jobs | {gitlab_job},
                    stages=init_context_directory.scm.gitlab_jobs_stages.stages.add(
                        GitLabStageId.QUALITY,
                        build_gitlab_stage_job(
                            gitlab_stage_id=GitLabStageId.QUALITY, gitlab_job=gitlab_job
                        ),
                    ),
                ),
            ),
            dependency_groups=init_context_directory.dependency_groups.add(
                sdk_module_name,
                {
                    # https://github.com/astral-sh/uv/releases/tag/0.11.0
                    # >= 0.11.0: New uv audit command
                    "uv >= 0.11.0"
                },
            ),
        )


@dagger.object_type
class Auditor(PythonModule):
    """Python SDK Security Auditor."""

    @staticmethod
    def _initializer_cls() -> type[AuditorInitializer]:
        """
        Initializer class.

        Returns:
            The initializer class.
        """
        return AuditorInitializer

    @final
    @dagger.function
    async def audit(
        self,
        project_directory: ProjectDirectoryDaggerType,
        *,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> str:
        """Run security audit analysis in the project."""
        container = await self._exec_container(project_directory, platform)
        uv_audit_command = self._build_uv_run_command(["uv", "audit"])
        await container.with_exec(uv_audit_command).sync()
        return "Security audit successful"


sdk_module: Final = Auditor
