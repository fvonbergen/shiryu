"""releaser module."""

import asyncio
from pathlib import Path
from typing import Annotated, Final, final
from urllib.parse import urlsplit, urlunsplit

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
    ProjectDirectoryType,
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
from ...common.vcs import VCS_PRIMARY_BRANCH
from ..context import PythonModuleInitContextDirectory
from ..module import ExecutionMode, PythonModule, PythonModuleInitializer
from ..templates import PYTHON_JINJA_ENVIRONMENT

AuthTokenDaggerType = Annotated[dagger.Secret, dagger.Doc("Authorization token")]
VCSUserNameDaggerType = Annotated[str, dagger.Doc("VCS user name")]
VCS_USER_NAME_DAGGER_DEFAULT: Final = "CI Release Bot"
VCSUserEMailDaggerType = Annotated[str, dagger.Doc("VCS user email")]
VCS_USER_EMAIL_DAGGER_DEFAULT: Final = "ci@shiryu.dev"

type PushUrls = list[str]


class ReleaserInitializer(PythonModuleInitializer):
    """ReleaserInitializer class."""

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
        """.cz.toml template file.

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
        """Build the initialization directory.

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
        """Initializer class.

        Returns:
            The initializer class.
        """
        return ReleaserInitializer

    @final
    @classmethod
    def __normalize_to_https(cls, raw_url: str) -> str:
        """Normalize Git remote URLs to clean HTTPS format without credentials.

        Converts legacy SCP-style SSH paths (e.g., git@domain.com:org/repo.git) to standard HTTPS
        syntax and strips any embedded username or password credentials from the netloc to prevent
        leaking secrets to disk.

        Args:
            raw_url: Raw Git remote URL extracted from repository configuration.

        Returns:
            A clean HTTPS URL string containing only scheme, host, port, and path.
        """
        clean_url = raw_url.strip()

        # Convert SCP-style SSH syntax (git@host.com:org/repo.git -> https://host.com/org/repo.git)
        if clean_url.startswith("git@") and ":" in clean_url and not clean_url.startswith("git://"):
            host_part, path_part = clean_url[4:].split(":", 1)
            clean_url = f"https://{host_part}/{path_part}"

        parsed = urlsplit(clean_url)

        # SECURITY: Explicitly strip both username and password from netloc/authority component
        # to ensure raw remotes written to .git/config contain zero embedded credentials.
        hostname = parsed.hostname or ""
        port_suffix = f":{parsed.port}" if parsed.port else ""
        clean_netloc = f"{hostname}{port_suffix}"

        return urlunsplit(("https", clean_netloc, parsed.path, parsed.query, parsed.fragment))

    @final
    @classmethod
    async def __get_clean_push_urls(
        cls, project_directory: ProjectDirectoryDaggerType, platform: PlatformType
    ) -> PushUrls:
        """Retrieve cleaned HTTPS Git push URLs for a project directory.

        Extracts 'origin' push URLs via Dagger and normalizes them to credential-free HTTPS
        endpoints.

        Args:
            project_directory: Project directory.
            platform: The container platform.

        Returns:
            A list of validated, credential-free HTTPS Git remote URLs.
        """
        raw_origin = await (
            container_git(dagger.dag, platform)
            .with_directory(".", project_directory)
            .with_exec(["git", "remote", "get-url", "--all", "--push", "origin"])
            .stdout()
        )

        push_urls = [line.strip() for line in raw_origin.strip().splitlines() if line.strip()]
        return [cls.__normalize_to_https(url) for url in push_urls]

    @final
    @classmethod
    async def __release(  # noqa: PLR0913, PLR0917
        cls,
        container: dagger.Container,
        push_urls: PushUrls,
        auth_token: AuthTokenDaggerType,
        vcs_user_name: VCSUserNameDaggerType,
        vcs_user_email: VCSUserEMailDaggerType,
        dry_run: bool,
    ) -> str:
        """Run release steps inside the Dagger container with maximal security controls.

        Configures Git identity, updates remote URLs to clean target endpoints, executes Commitizen
        version bumping, and pushes upstream.

        Args:
            container: Execution container configured with runtime dependencies.
            push_urls: List of clean HTTPS remote URLs for push targets.
            auth_token: Authorization token.
            vcs_user_name: VCS user name.
            vcs_user_email: VCS user email.
            dry_run: Flag indicating whether to skip upstream pushes and commitizen mutations.

        Returns:
            Captured stdout logs from the release execution.
        """
        initializer = cls._initializer_cls()
        container = container.with_exec(
            ["git", "config", "--global", "user.name", vcs_user_name]
        ).with_exec(["git", "config", "--global", "user.email", vcs_user_email])

        # Write clean HTTPS push URLs to repository config
        if push_urls:
            container = container.with_exec(["git", "remote", "set-url", "origin", push_urls[0]])
            for next_url in push_urls[1:]:
                container = container.with_exec(
                    ["git", "remote", "set-url", "--add", "origin", next_url]
                )

        _cz_toml_file_name = initializer._cz_toml_template_file().file_name
        cz_command = cls._build_uv_run_command(
            ["cz", f"--config={_cz_toml_file_name}", "bump", "--changelog", "--yes"],
            execution_mode=ExecutionMode.SCRIPT,
        )
        if dry_run:
            cz_command = [*cz_command, "--dry-run"]

        container = container.with_exec(cz_command)

        if not dry_run:
            # SECURITY:
            # 1. Bind auth_token to secret environment variable `GIT_TOKEN`.
            # 2. Use `GIT_CONFIG_KEY_0` and `GIT_CONFIG_VALUE_0` to inject HTTP authorization
            #    header natively into Git.
            # 3. Direct execution via array args ensures no shell parsing takes place.
            container = (
                container.with_secret_variable("GIT_TOKEN", auth_token)
                .with_env_variable("GIT_CONFIG_KEY_0", "http.extraHeader")
                .with_env_variable("GIT_CONFIG_VALUE_0", "Authorization: Bearer $GIT_TOKEN")
                .with_exec(["git", "push", "origin", f"HEAD:{VCS_PRIMARY_BRANCH}", "--follow-tags"])
            )

        return await container.stdout()

    @final
    @classmethod
    async def __run_release_workflow(  # noqa: PLR0913, PLR0917
        cls,
        project_directory: ProjectDirectoryType,
        auth_token: AuthTokenDaggerType,
        vcs_user_name: VCSUserNameDaggerType,
        vcs_user_email: VCSUserEMailDaggerType,
        platform: PlatformType,
        dry_run: bool,
    ) -> str:
        """Internal orchestrator executing the container release pipeline securely.

        Coordinates parallel preparation tasks before invoking the execution stage.

        Args:
            project_directory: Project directory.
            auth_token: Authorization token.
            vcs_user_name: VCS user name.
            vcs_user_email: VCS user email.
            platform: The container platform.
            dry_run: If True, execution in dry-run simulation mode without pushing upstream.

        Returns:
            Success summary message on real releases, or full command output log during dry runs.
        """
        container, clean_push_urls = await asyncio.gather(
            cls._exec_container(project_directory, platform),
            cls.__get_clean_push_urls(project_directory, platform),
        )
        output = await cls.__release(
            container, clean_push_urls, auth_token, vcs_user_name, vcs_user_email, dry_run=dry_run
        )
        return output if dry_run else "Release successful"

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
        return await self.__run_release_workflow(
            project_directory, auth_token, vcs_user_name, vcs_user_email, platform, dry_run=False
        )

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
        return await self.__run_release_workflow(
            project_directory, auth_token, vcs_user_name, vcs_user_email, platform, dry_run=True
        )


sdk_module: Final = Releaser
