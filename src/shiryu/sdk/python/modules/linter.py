"""linter module."""

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
from ..context import PythonModuleInitContextDirectory
from ..module import PythonModule, PythonModuleInitializer
from ..templates import PYTHON_JINJA_ENVIRONMENT


class LinterInitializer(PythonModuleInitializer):
    """LinterInitializer class."""

    @final
    @staticmethod
    def _ruff_cache_folder() -> str:
        """
        Get the linter cache folder.

        Returns:
            The linter cache folder.
        """
        return ".ruff_cache"

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
        sdk_module_cls = Linter
        sdk_language = sdk_module_cls._sdk_name()
        sdk_module_name = sdk_module_cls.name()
        sdk_module_function = sdk_module_cls.lint
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
            sdk_module_function=sdk_module_function,
            shiryu_version=shiryu_version,
            pre_script=(),
            export_path=None,
            post_script=(),
            artifacts=None,
        )
        return init_context_directory.evolve(
            vcs=init_context_directory.vcs.evolve(
                exclude_files_folders=init_context_directory.vcs.exclude_files_folders
                | {f"/{cls._ruff_cache_folder()}/"}
            ),
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
                sdk_module_name, {"ruff"}
            ),
        )

    @final
    @classmethod
    def _ruff_toml_template_file(cls) -> TemplateFile:
        """
        ruff.toml template file.

        Returns:
            The ruff.toml template file.
        """
        return TemplateFile(Path("ruff.toml"))

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
        # ruff.toml
        ruff_toml_template_mapping: Mapping = {"cache_folder": cls._ruff_cache_folder()}
        ruff_toml_template = Template(
            PYTHON_JINJA_ENVIRONMENT, cls._ruff_toml_template_file(), ruff_toml_template_mapping
        )
        return directory_with_new_file(init_directory, ruff_toml_template)


@dagger.object_type
class Linter(PythonModule):
    """Python SDK linter."""

    @staticmethod
    def _initializer_cls() -> type[LinterInitializer]:
        """
        Initializer class.

        Returns:
            The initializer class.
        """
        return LinterInitializer

    @final
    @classmethod
    async def __lint_fix(cls, container: dagger.Container, fix: bool) -> dagger.Directory:
        """
        Lint pipeline.

        Args:
            container: Project container.
            fix: Whether to fix the project files or not.

        Returns:
            Modified files between the project directory before and after running commands.
        """
        initializer = cls._initializer_cls()
        ruff_cache_folder = initializer._ruff_cache_folder()
        container = container.with_mounted_cache(
            ruff_cache_folder, dagger.dag.cache_volume("shiryu-ruff-debian-trixie-slim")
        )
        ruff_toml_file_name = initializer._ruff_toml_template_file().file_name
        ruff_check_command = cls._build_uv_run_command(
            ["ruff", "check", "--show-fixes", f"--config={ruff_toml_file_name}", "."]
        )
        ruff_format_command = cls._build_uv_run_command(
            ["ruff", "format", f"--config={ruff_toml_file_name}", "."]
        )
        expect_check = dagger.ReturnType.SUCCESS
        if fix:
            expect_check = dagger.ReturnType.ANY
            ruff_check_command = [*ruff_check_command, "--fix"]
        else:
            ruff_format_command = [*ruff_format_command, "--diff"]
        # Diff directories before and after command.
        initial_dir = container.directory(".")
        executed_container = container.with_exec(ruff_check_command, expect=expect_check).with_exec(
            ruff_format_command
        )
        modified_dir = executed_container.directory(".").filter(exclude=[f"{ruff_cache_folder}/"])
        return await initial_dir.diff(modified_dir).sync()

    @final
    @dagger.function
    async def lint(
        self,
        project_directory: ProjectDirectoryDaggerType,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> str:
        """Run linter analysis in the project of the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        await self.__lint_fix(container, False)
        return "Lint successfull"

    @final
    @dagger.function
    async def fix(
        self,
        project_directory: ProjectDirectoryDaggerType,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> dagger.Directory:
        """Run linter fixes in the project of the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        return await self.__lint_fix(container, True)


sdk_module: Final = Linter
