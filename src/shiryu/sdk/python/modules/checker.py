"""checker module."""

from pathlib import Path
from typing import Final, final

import dagger

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
from ...common.scm import (
    GitHubWorkflowId,
    GitLabStageId,
    build_github_action,
    build_github_workflow_job,
    build_gitlab_job,
    build_gitlab_stage_job,
)
from ...common.utils import PROJECT_SOURCE_CODE_FOLDER
from ..context import PythonModuleInitContextDirectory
from ..module import PythonModule, PythonModuleInitializer
from ..templates import PYTHON_JINJA_ENVIRONMENT


class CheckerInitializer(PythonModuleInitializer):
    """CheckerInitializer class."""

    @final
    @classmethod
    def _ty_toml_template_file(cls) -> TemplateFile:
        """
        Get the ty.toml template file.

        Returns:
            The ty.toml template file.
        """
        return TemplateFile(Path("ty.toml"))

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
        dagger_version = shiryu_metadata.dagger_version
        shiryu_version = shiryu_metadata.git_tag_or_branch
        sdk_module_cls = Checker
        sdk_language = sdk_module_cls._sdk_name()
        sdk_module_name = sdk_module_cls.name()
        sdk_module_function = sdk_module_cls.check
        github_action = build_github_action(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function,
            dagger_version=dagger_version,
            shiryu_version=shiryu_version,
            export_path=None,
        )
        gitlab_job = build_gitlab_job(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function,  # pyright: ignore [reportArgumentType]
            shiryu_version=shiryu_version,
            pre_script=(),
            export_path=None,
            post_script=(),
            artifacts=None,
        )
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
                            shiryu_version=shiryu_version,
                            job_environment=None,
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
                    # https://github.com/astral-sh/ty/releases/tag/0.0.1-alpha.8
                    # >= 0.0.1-alpha.8: Add --config-file CLI arg.
                    "ty >= 0.0.1-alpha.8"
                },
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
        # ty.toml
        ty_toml_template_mapping: Mapping = {
            "project_source_path": PROJECT_SOURCE_CODE_FOLDER,
            "source_code_files_folders": init_context_directory.source_code_files_folders,
        }
        ty_toml_template = Template(
            PYTHON_JINJA_ENVIRONMENT, cls._ty_toml_template_file(), ty_toml_template_mapping
        )
        return directory_with_new_file(init_directory, ty_toml_template)


@dagger.object_type
class Checker(PythonModule):
    """Python SDK checker."""

    @staticmethod
    def _initializer_cls() -> type[CheckerInitializer]:
        """
        Initializer class.

        Returns:
            The initializer class.
        """
        return CheckerInitializer

    @final
    @classmethod
    async def __check(cls, container: dagger.Container) -> None:
        """
        Check pipeline.

        Args:
            container: Project container.
        """
        initializer = cls._initializer_cls()
        ty_command = cls._build_uv_run_command(
            ["ty", "check", f"--config-file={initializer._ty_toml_template_file().file_name}"]
        )
        await container.with_exec(ty_command).sync()

    @final
    @dagger.function
    async def check(
        self,
        project_directory: ProjectDirectoryDaggerType,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> str:
        """Run type checks in the project of the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        await self.__check(container)
        return "Check successfull"


sdk_module: Final = Checker
