"""releaser module."""

import asyncio
from pathlib import Path
from typing import Annotated, Final, final
from urllib.parse import urlsplit, urlunsplit

import dagger

from ....utils.dagger.client import container_git
from ....utils.dagger.directory import directory_with_new_file
from ....utils.dagger.function import SourceType
from ....utils.template import Mapping, Template, TemplateFile
from ...common.context import DaggerModuleMetadata
from ...common.module import (
    PLATFORM_DAGGER_DEFAULT,
    PlatformDaggerType,
    PlatformType,
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
from ..templavtes import PYTHON_JINJA_ENVIRONMENT

AuthTokenDaggerType = Annotated[dagger.Secret, dagger.Doc("Authorization token")]
AuthUserNameDaggerType = Annotated[
    str,
    dagger.Doc(
        "User name sent with the authorization token (any non-empty value works with GitHub and "
        "GitLab access tokens)."
    ),
]
AUTH_USER_NAME_DAGGER_DEFAULT: Final = "x-access-token"
GitUserNameDaggerType = Annotated[str, dagger.Doc("Git user name used for the release commit.")]
GitUserEmailDaggerType = Annotated[str, dagger.Doc("Git user email used for the release commit.")]
VCSUserNameDaggerType = Annotated[str, dagger.Doc("VCS user name")]

VCS_USER_NAME_DAGGER_DEFAULT: Final = "CI Release Bot"
VCSUserEMailDaggerType = Annotated[str, dagger.Doc("VCS user email")]
VCS_USER_EMAIL_DAGGER_DEFAULT: Final = "ci@shiryu.dev"

type PushUrls = list[str]

CZ_NOTHING_TO_RELEASE_EXIT_CODES: Final = frozenset({3, 21})
NOTHING_TO_RELEASE: Final = "Nothing to release"


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
    async def __next_version(cls, container: dagger.Container) -> str | None:
        """Compute the next version from the commits since the last release tag.

        Args:
            container: Project container.

        Returns:
            The next version, or `None` if no commit is eligible for a release.

        Raises:
            RuntimeError: If commitizen fails for any other reason.
        """
        executed_container = container.with_exec(
            cls._build_uv_run_command(
                ["cz", "bump", "--get-next", "--yes"], execution_mode=ExecutionMode.SCRIPT
            ),
            expect=dagger.ReturnType.ANY,
        )
        exit_code = await executed_container.exit_code()
        if exit_code in CZ_NOTHING_TO_RELEASE_EXIT_CODES:
            return None
        if exit_code != 0:
            exception_message = (
                f"{await executed_container.stdout()}{await executed_container.stderr()}"
            )
            raise RuntimeError(exception_message)
        return (await executed_container.stdout()).strip()

    @final
    @classmethod
    def __bump(
        cls, container: dagger.Container, version: str, git_user_name: str, git_user_email: str
    ) -> dagger.Container:
        """Bump the project version, update the changelog, commit and tag.

        Args:
            container: Project container.
            version: The new version.
            git_user_name: Release commit author name.
            git_user_email: Release commit author email.

        Returns:
            A container with the release commit and tag.
        """
        tag = f"v{version}"
        git_identity = ["-c", f"user.name={git_user_name}", "-c", f"user.email={git_user_email}"]
        return (
            # Updates pyproject.toml and uv.lock together.
            container.with_exec(["uv", "version", version, "--no-sync"])
            .with_exec(
                cls._build_uv_run_command(
                    ["cz", "changelog", "--incremental", f"--unreleased-version={tag}"],
                    execution_mode=ExecutionMode.SCRIPT,
                )
            )
            .with_exec(["git", "add", "pyproject.toml", "uv.lock", "CHANGELOG.md"])
            .with_exec(["git", *git_identity, "commit", "-m", f"chore: release {tag}"])
            .with_exec(["git", *git_identity, "tag", "--annotate", tag, f"-m={tag}"])
        )

    @final
    @classmethod
    async def __ensure_primary_branch_head(cls, container: dagger.Container) -> None:
        """Ensure the checked out commit is the tip of the remote primary branch.

        CI checkouts are usually in detached HEAD state (always in GitLab), so the current branch
        name can't be used. Comparing against the remote-tracking ref prevents releasing (and
        pushing to the primary branch) from any other branch.

        Args:
            container: Project container.

        Raises:
            RuntimeError: If HEAD is not the tip of the remote primary branch.
        """
        remote_ref = f"refs/remotes/origin/{VCS_PRIMARY_BRANCH}"
        executed_container = container.with_exec(
            ["git", "rev-parse", "HEAD", remote_ref], expect=dagger.ReturnType.ANY
        )
        head_sha, _, remote_sha = (await executed_container.stdout()).strip().partition("\n")
        if await executed_container.exit_code() != 0 or head_sha != remote_sha:
            exception_message = (
                f"Releases can only be made from the tip of {VCS_PRIMARY_BRANCH} "
                f"(HEAD={head_sha or 'unknown'}, {remote_ref}={remote_sha or 'missing'})"
            )
            raise RuntimeError(exception_message)

    @final
    @classmethod
    def __push(
        cls,
        container: dagger.Container,
        push_urls: PushUrls,
        tag: str,
        auth_user_name: str,
        auth_token: dagger.Secret,
    ) -> dagger.Container:
        """Push the release commit and tag atomically.

        Args:
            container: Container with the release commit and tag.
            push_urls: Credential-free HTTPS push URLs.
            tag: The release tag.
            auth_user_name: User name sent along with the token.
            auth_token: Token with write access to the repository.

        Returns:
            The container after pushing.
        """
        credential_helper = (
            '!f() { test "$1" = get && '
            'printf "username=%s\\npassword=%s\\n" "$GIT_AUTH_USER_NAME" "$GIT_AUTH_TOKEN"; }; f'
        )
        container = container.with_env_variable(
            "GIT_AUTH_USER_NAME", auth_user_name
        ).with_secret_variable("GIT_AUTH_TOKEN", auth_token)
        for push_url in push_urls:
            container = container.with_exec(
                [
                    "git",
                    "-c",
                    "credential.helper=",
                    "-c",
                    f"credential.helper={credential_helper}",
                    "push",
                    "--atomic",
                    push_url,
                    f"HEAD:refs/heads/{VCS_PRIMARY_BRANCH}",
                    f"refs/tags/{tag}",
                ]
            )
        return container

    @final
    @dagger.function
    async def release(  # noqa: PLR0913, PLR0917
        self,
        project_directory: ProjectDirectoryDaggerType,
        auth_token: AuthTokenDaggerType,
        auth_user_name: AuthUserNameDaggerType = AUTH_USER_NAME_DAGGER_DEFAULT,
        git_user_name: GitUserNameDaggerType = VCS_USER_NAME_DAGGER_DEFAULT,
        git_user_email: GitUserEmailDaggerType = VCS_USER_EMAIL_DAGGER_DEFAULT,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> str:
        """Bump version, update changelog, commit, tag and push the project.

        Returns the release tag, or an empty string if there is nothing to release, so CI can
        decide whether to run the publishing jobs and which ref to check out.
        """
        container, push_urls = await asyncio.gather(
            self._exec_container(project_directory, platform),
            self.__get_clean_push_urls(project_directory, platform),
        )
        await self.__ensure_primary_branch_head(container)
        version = await self.__next_version(container)
        if version is None:
            return ""
        tag = f"v{version}"
        bump_container = self.__bump(container, version, git_user_name, git_user_email)
        await self.__push(bump_container, push_urls, tag, auth_user_name, auth_token).sync()
        return tag

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
    async def __get_clean_push_urls(cls, source: SourceType, platform: PlatformType) -> PushUrls:
        """Retrieve cleaned HTTPS Git push URLs for a project directory.

        Extracts 'origin' push URLs via Dagger and normalizes them to credential-free HTTPS
        endpoints.

        Args:
            source: Project source directory.
            platform: The container platform.

        Returns:
            A list of validated, credential-free HTTPS Git remote URLs.
        """
        raw_origin = await (
            container_git(dagger.dag, platform)
            .with_directory(".", source)
            .with_exec(["git", "remote", "get-url", "--all", "--push", "origin"])
            .stdout()
        )

        push_urls = [line.strip() for line in raw_origin.strip().splitlines() if line.strip()]
        return [cls.__normalize_to_https(url) for url in push_urls]


sdk_module: Final = Releaser
