"""linter module."""

import asyncio
from pathlib import Path
from typing import Annotated, Final, final

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
    GitHubWorkflowStepInputParameter,
    GitLabStageId,
    GitLabVariable,
    build_github_action,
    build_github_workflow_checkout_job,
    build_github_workflow_job,
    build_gitlab_job,
    build_gitlab_stage_job,
)
from ...common.utils import TESTS_UNIT_PATH
from ...common.vcs import VCS_PRIMARY_BRANCH
from ..context import PythonModuleInitContextDirectory
from ..module import ExecutionMode, PythonModule, PythonModuleInitializer
from ..templates import PYTHON_JINJA_ENVIRONMENT

BranchHistoryDaggerType = Annotated[
    bool, dagger.Doc("Whether to lint over branch VCS history or not")
]
BRANCH_HISTORY_DAGGER_DEFAULT: Final = True


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
        sdk_module_function_lint_code = sdk_module_cls.lint_code
        sdk_module_function_lint_vcs = sdk_module_cls.lint_vcs
        github_action_linter_lint_code = build_github_action(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function_lint_code,
            dagger_version=dagger_version,
            shiryu_version=shiryu_version,
            export_path=None,
        )
        github_action_linter_lint_vcs = build_github_action(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function_lint_vcs,
            dagger_version=dagger_version,
            shiryu_version=shiryu_version,
            export_path=None,
        )
        gitlab_job_linter_lint_code = build_gitlab_job(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function_lint_code,
            shiryu_version=shiryu_version,
            variables=(),
            pre_script=(),
            export_path=None,
            post_script=(),
            artifacts=None,
        )
        gitlab_job_linter_lint_vcs = build_gitlab_job(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function_lint_vcs,
            shiryu_version=shiryu_version,
            variables=(GitLabVariable("GIT_STRATEGY", "fetch"), GitLabVariable("GIT_DEPTH", "0")),
            pre_script=(f"git fetch origin main:refs/remotes/origin/{VCS_PRIMARY_BRANCH} || true",),
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
                    | {github_action_linter_lint_code, github_action_linter_lint_vcs},
                    workflows=init_context_directory.scm.github_actions_workflows.workflows.add(
                        GitHubWorkflowId.QUALITY,
                        build_github_workflow_job(
                            sdk_language=sdk_language,
                            github_action=github_action_linter_lint_code,
                            shiryu_version=shiryu_version,
                            job_environment=None,
                            pre_steps=(build_github_workflow_checkout_job(),),
                            post_steps=(),
                        ),
                    ).add(
                        GitHubWorkflowId.QUALITY,
                        build_github_workflow_job(
                            sdk_language=sdk_language,
                            github_action=github_action_linter_lint_vcs,
                            shiryu_version=shiryu_version,
                            job_environment=None,
                            pre_steps=(
                                build_github_workflow_checkout_job(
                                    (GitHubWorkflowStepInputParameter("fetch-depth", "0"),)
                                ),
                            ),
                            post_steps=(),
                        ),
                    ),
                ),
                gitlab_jobs_stages=init_context_directory.scm.gitlab_jobs_stages.evolve(
                    jobs=init_context_directory.scm.gitlab_jobs_stages.jobs
                    | {gitlab_job_linter_lint_code, gitlab_job_linter_lint_vcs},
                    stages=init_context_directory.scm.gitlab_jobs_stages.stages.add(
                        GitLabStageId.QUALITY,
                        build_gitlab_stage_job(
                            gitlab_stage_id=GitLabStageId.QUALITY,
                            gitlab_job=gitlab_job_linter_lint_code,
                        ),
                    ).add(
                        GitLabStageId.QUALITY,
                        build_gitlab_stage_job(
                            gitlab_stage_id=GitLabStageId.QUALITY,
                            gitlab_job=gitlab_job_linter_lint_vcs,
                        ),
                    ),
                ),
            ),
            dependency_groups=init_context_directory.dependency_groups.add(
                sdk_module_name,
                {
                    # https://github.com/commit-check/commit-check/releases/tag/v2.0.0
                    # >= 2.0.0: Configuration Migration and Removed Features
                    "commit-check >= 2.0.0",
                    # https://github.com/astral-sh/ruff/blob/main/changelogs/0.1.x.md#012
                    # >= 0.1.2: New ruff format command
                    "ruff >= 0.1.2",
                },
            ),
        )

    @final
    @classmethod
    def _cchk_toml_template_file(cls) -> TemplateFile:
        """
        cchk.toml template file.

        Returns:
            The cchk.toml template file.
        """
        return TemplateFile(Path("cchk.toml"))

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
        # cchk.toml
        cchk_toml_template_mapping: Mapping = {}
        cchk_toml_template = Template(
            PYTHON_JINJA_ENVIRONMENT, cls._cchk_toml_template_file(), cchk_toml_template_mapping
        )
        init_directory = directory_with_new_file(init_directory, cchk_toml_template)
        # ruff.toml
        ruff_toml_template_mapping: Mapping = {
            "cache_folder": cls._ruff_cache_folder(),
            "tests_unit_path": str(TESTS_UNIT_PATH),
        }
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
    async def __lint_fix_code(cls, container: dagger.Container, fix: bool) -> dagger.Directory:
        """
        Lint or fix code pipeline.

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
    @classmethod
    async def __lint_vcs(cls, container: dagger.Container, branch_history: bool) -> None:
        """
        Lint VCS pipeline.

        Args:
            container: Project container.
            branch_history: Whether to lint over branch VCS history or not.
        """
        initializer = cls._initializer_cls()
        cchk_toml_file_name = initializer._cchk_toml_template_file().file_name
        commit_check_config = ["commit-check", "--no-banner", f"--config={cchk_toml_file_name}"]
        commit_check_message_command = cls._build_uv_run_command(
            [*commit_check_config, "--message", "--author-name", "--author-email", "--compact"],
            execution_mode=ExecutionMode.SCRIPT,
        )
        await asyncio.gather(
            container.with_exec(
                cls._build_uv_run_command(
                    [*commit_check_config, "--branch"], execution_mode=ExecutionMode.SCRIPT
                )
            ).sync(),
            container.with_exec(
                [
                    "bash",
                    "-c",
                    f"""
                # Stop Git from complaining about folder ownership in Docker
                #git config --global --add safe.directory /src

                # Gather all commits across history, ignoring merge commits
                #shas=$(git rev-list --no-merges HEAD) || exit 1
                # Gather only commits unique to the current branch vs origin/main
                shas=$(git rev-list --no-merges origin/{VCS_PRIMARY_BRANCH}..HEAD) || exit 1

                status=0
                for sha in $shas; do
                  # Check message, author name, and email all at once in compact view
                  if ! {" ".join(commit_check_message_command)} --rev "$sha"; then
                    status=1
                  fi
                done

                exit $status
                """,
                ]
                if branch_history
                else commit_check_message_command
            ).sync(),
        )

    @final
    @dagger.function
    async def lint_code(
        self,
        project_directory: ProjectDirectoryDaggerType,
        *,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> str:
        """Run linter analysis in the project code of the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        await self.__lint_fix_code(container, False)
        return "Lint code successfull"

    @final
    @dagger.function
    async def fix_code(
        self,
        project_directory: ProjectDirectoryDaggerType,
        *,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> dagger.Directory:
        """Run linter fixes in the project code of the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        return await self.__lint_fix_code(container, True)

    @final
    @dagger.function
    async def lint_vcs(
        self,
        project_directory: ProjectDirectoryDaggerType,
        *,
        branch_history: BranchHistoryDaggerType = BRANCH_HISTORY_DAGGER_DEFAULT,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> str:
        """Run linter analysis in the project VCS of the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        await self.__lint_vcs(container, branch_history)
        return "Lint VCS successfull"


sdk_module: Final = Linter
