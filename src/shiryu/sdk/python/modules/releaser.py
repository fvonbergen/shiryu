"""releaser module."""

import asyncio
from pathlib import Path
from typing import Annotated, Final, final

import dagger

from ....utils.dagger.client import container_git
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
    SCM,
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
from ...common.vcs import VCS_PRIMARY_BRANCH
from ..context import PythonModuleInitContextDirectory
from ..module import ExecutionMode, PythonModule, PythonModuleInitializer
from ..templates import PYTHON_JINJA_ENVIRONMENT

AuthTokenDaggerType = Annotated[dagger.Secret, dagger.Doc("Authorization token")]
VCSUserNameDaggerType = Annotated[str, dagger.Doc("VCS user name")]
VCS_USER_NAME_DAGGER_DEFAULT: Final = "CI Release Bot"
VCSUserEMailDaggerType = Annotated[str, dagger.Doc("VCS user email")]
VCS_USER_EMAIL_DAGGER_DEFAULT: Final = "ci@shiryu.dev"


class ReleaserInitializer(PythonModuleInitializer):
    """ReleaserInitializer class."""

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
        sdk_module_cls = Releaser
        sdk_language = sdk_module_cls._sdk_name()
        sdk_module_name = sdk_module_cls.name()
        sdk_module_function = sdk_module_cls.release
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
            variables=(GitLabVariable("GIT_STRATEGY", "fetch"), GitLabVariable("GIT_DEPTH", "0")),
            pre_script=(),
            export_path=None,
            post_script=(),
            artifacts=None,
        )
        pre_steps = (
            build_github_workflow_checkout_job(
                (GitHubWorkflowStepInputParameter("fetch-depth", "0"),)
            ),
        )

        return init_context_directory.evolve(
            scm=init_context_directory.scm.evolve(
                github_actions_workflows=init_context_directory.scm.github_actions_workflows.evolve(
                    actions=init_context_directory.scm.github_actions_workflows.actions
                    | {github_action},
                    workflows=init_context_directory.scm.github_actions_workflows.workflows.add(
                        GitHubWorkflowId.RELEASE,
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
                        GitLabStageId.RELEASE,
                        build_gitlab_stage_job(
                            gitlab_stage_id=GitLabStageId.RELEASE, gitlab_job=gitlab_job
                        ),
                    ),
                ),
            ),
            dependency_groups=init_context_directory.dependency_groups.add(
                sdk_module_name, {"commitizen"}
            ),
        )

    @final
    @classmethod
    def _cz_toml_template_file(cls) -> TemplateFile:
        """
        .cz.toml template file.

        Returns:
            The .cz.toml template file.
        """
        return TemplateFile(Path(".cz.toml"))

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
        # .cz.toml
        _cz_toml_template_mapping: Mapping = {}
        _cz_toml_template = Template(
            PYTHON_JINJA_ENVIRONMENT, cls._cz_toml_template_file(), _cz_toml_template_mapping
        )
        return directory_with_new_file(init_directory, _cz_toml_template)


@dagger.object_type
class Releaser(PythonModule):
    """Python SDK Releaser."""

    @staticmethod
    def _initializer_cls() -> type[ReleaserInitializer]:
        """
        Initializer class.

        Returns:
            The initializer class.
        """
        return ReleaserInitializer

    @final
    @classmethod
    async def __get_auth_urls(
        cls,
        project_directory: ProjectDirectoryDaggerType,
        auth_token: AuthTokenDaggerType,
        platform: PlatformType,
    ) -> list[str]:
        """
        Retrieve authenticated HTTPS Git push URLs for a project directory.

        Extracts 'origin' push URLs via Dagger, normalizes SSH/HTTPS formats, and injects the
        authentication token (using GitLab OAuth2 or GitHub x-access-token syntax).

        Args:
            project_directory: Project directory.
            auth_token: Authorization token.
            platform: The container platform.

        Returns:
            HTTPS URLs formatted with embedded credentials.
        """
        raw_origin = await (
            container_git(dagger.dag, platform)
            .with_directory(".", project_directory)
            .with_exec(["git", "remote", "get-url", "--all", "--push", "origin"])
            .stdout()
        )
        push_urls = [line.strip() for line in raw_origin.strip().splitlines() if line.strip()]
        auth_urls = []
        token_str = await auth_token.plaintext()
        for raw_url in push_urls:
            clean_url = raw_url
            # Normalize SSH (git@domain:org/repo.git) to HTTPS
            if clean_url.startswith("git@"):
                clean_url = clean_url.replace(":", "/").replace("git@", "https://")
            elif clean_url.startswith(("https://", "http://")):
                clean_url = "https://" + clean_url.split("://")[-1].split("@")[-1]

            # Inject token based on target domain
            if SCM.GITLAB.value in clean_url:
                auth_url = clean_url.replace("https://", f"https://oauth2:{token_str}@")
            else:
                auth_url = clean_url.replace("https://", f"https://x-access-token:{token_str}@")

            auth_urls.append(auth_url)
        return auth_urls

    @final
    @dagger.function
    async def release(
        self,
        project_directory: ProjectDirectoryDaggerType,
        auth_token: AuthTokenDaggerType,
        *,
        vcs_user_name: VCSUserNameDaggerType = VCS_USER_NAME_DAGGER_DEFAULT,
        vcs_user_email: VCSUserEMailDaggerType = VCS_USER_EMAIL_DAGGER_DEFAULT,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> str:
        """Run release in the project."""
        initializer = self._initializer_cls()
        auth_urls, container = await asyncio.gather(
            self.__get_auth_urls(project_directory, auth_token, platform),
            self._exec_container(project_directory, platform),
        )
        container = container.with_exec(
            ["git", "config", "--global", "user.name", vcs_user_name]
        ).with_exec(["git", "config", "--global", "user.email", vcs_user_email])

        # Re-assign origin push URLs to match all detected remotes
        # The first URL replaces current origin; subsequent URLs are added via --add
        if auth_urls:
            container = container.with_exec(["git", "remote", "set-url", "origin", auth_urls[0]])
            for next_url in auth_urls[1:]:
                container = container.with_exec(
                    ["git", "remote", "set-url", "--add", "origin", next_url]
                )
        _cz_toml_file_name = initializer._cz_toml_template_file().file_name
        cz_command = self._build_uv_run_command(
            ["cz", f"--config={_cz_toml_file_name}", "bump", "--changelog", "--yes"],
            execution_mode=ExecutionMode.SCRIPT,
        )
        await (
            container.with_exec(cz_command)
            .with_exec(
                ["git", "push", "origin", f"HEAD:{VCS_PRIMARY_BRANCH}", "--follow-tags"],
            )
            .sync()
        )
        return "Release successful"

    @final
    @dagger.function
    async def test(
        self,
        project_directory: ProjectDirectoryDaggerType,
        auth_token: AuthTokenDaggerType,
        *,
        vcs_user_name: VCSUserNameDaggerType = VCS_USER_NAME_DAGGER_DEFAULT,
        vcs_user_email: VCSUserEMailDaggerType = VCS_USER_EMAIL_DAGGER_DEFAULT,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> str:
        """Run release dry run in the project."""
        initializer = self._initializer_cls()
        auth_urls, container = await asyncio.gather(
            self.__get_auth_urls(project_directory, auth_token, platform),
            self._exec_container(project_directory, platform),
        )
        container = container.with_exec(
            ["git", "config", "--global", "user.name", vcs_user_name]
        ).with_exec(["git", "config", "--global", "user.email", vcs_user_email])

        # Re-assign origin push URLs to match all detected remotes
        # The first URL replaces current origin; subsequent URLs are added via --add
        if auth_urls:
            container = container.with_exec(["git", "remote", "set-url", "origin", auth_urls[0]])
            for next_url in auth_urls[1:]:
                container = container.with_exec(
                    ["git", "remote", "set-url", "--add", "origin", next_url]
                )
        _cz_toml_file_name = initializer._cz_toml_template_file().file_name
        cz_command = self._build_uv_run_command(
            ["cz", f"--config={_cz_toml_file_name}", "bump", "--changelog", "--yes", "--dry-run"],
            execution_mode=ExecutionMode.SCRIPT,
        )
        return await container.with_exec(cz_command).stdout()


sdk_module: Final = Releaser
