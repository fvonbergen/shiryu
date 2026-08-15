"""Context module for core SDK module initialization configurations.

This module establishes immutable data structures representing the common
initialization context for SDK modules, handling directories, containers,
source control management (SCM), and version control systems (VCS).
"""

from dataclasses import dataclass, field, replace
from typing import Self, final

from .scm import GitHubActionsWorkflows, GitHubWorkflows, GitLabJobsStages, GitLabStages


@final
@dataclass(frozen=True, slots=True)
class DaggerModuleMetadata:
    """Metadata tracking configuration parameters for a Dagger module.

    Attributes:
        dagger_version: The required or targeted version string of the Dagger engine.
        git_tag_or_branch: The specific Git reference (tag or branch) for the module.
    """

    dagger_version: str
    git_tag_or_branch: str


VCSExcludeFilesAndFolders = frozenset[str]


@final
@dataclass(frozen=True, slots=True)
class SDKModuleInitContextDirectoryVcs:
    """Version Control System (VCS) initialization configuration context.

    Manages files and folder paths that should be structurally skipped or excluded
    during the initial directory parsing stage.

    Attributes:
        exclude_files_folders: A frozen set of file patterns or paths to ignore.
    """

    exclude_files_folders: VCSExcludeFilesAndFolders = field(default_factory=frozenset)

    def evolve(self, *, exclude_files_folders: VCSExcludeFilesAndFolders | None = None) -> Self:
        """Type-safe leaf evolution. Falls back to current value if None.

        Args:
            exclude_files_folders: Optional new set of paths to exclude.

        Returns:
            A new instance with updated or current exclusion patterns.
        """
        return replace(
            self,
            exclude_files_folders=exclude_files_folders
            if exclude_files_folders is not None
            else self.exclude_files_folders,
        )


@final
@dataclass(frozen=True, slots=True)
class SDKModuleInitContextDirectoryScm:
    """Source Control Management (SCM) initialization configuration context.

    Aggregates targeted platform workflow settings across both GitHub and GitLab
    environments.

    Attributes:
        github_actions_workflows: Context data tracking GitHub actions and workflows.
        gitlab_jobs_stages: Context data tracking GitLab jobs and pipeline stages.
    """

    github_actions_workflows: GitHubActionsWorkflows
    gitlab_jobs_stages: GitLabJobsStages

    def evolve(
        self,
        *,
        github_actions_workflows: GitHubActionsWorkflows | None = None,
        gitlab_jobs_stages: GitLabJobsStages | None = None,
    ) -> Self:
        """Type-safe leaf evolution. Falls back to current values if None.

        Args:
            github_actions_workflows: Optional new GitHub workflows configuration context.
            gitlab_jobs_stages: Optional new GitLab jobs configuration context.

        Returns:
            A new instance containing the modified platform configurations.
        """
        return replace(
            self,
            github_actions_workflows=github_actions_workflows or self.github_actions_workflows,
            gitlab_jobs_stages=gitlab_jobs_stages or self.gitlab_jobs_stages,
        )


@dataclass(frozen=True, slots=True)
class SDKModuleInitContextDirectory:
    """Composite context detailing layout options for the target directory structure.

    Combines both VCS configuration metrics and platform SCM pipeline settings.

    Attributes:
        vcs: Version control system details (e.g. file patterns to ignore).
        scm: Source control management configuration parameters.
    """

    vcs: SDKModuleInitContextDirectoryVcs
    scm: SDKModuleInitContextDirectoryScm

    def evolve(
        self,
        *,
        vcs: SDKModuleInitContextDirectoryVcs | None = None,
        scm: SDKModuleInitContextDirectoryScm | None = None,
    ) -> Self:
        """
        Pure assignment evolution. No 'if' clauses to forget.

        If an argument is passed, it uses it; otherwise, it keeps the current one.

        Args:
            vcs: Optional new VCS configuration block.
            scm: Optional new SCM configuration block.

        Returns:
            A copy of the directory context reflecting the passed adjustments.
        """
        return replace(self, vcs=vcs or self.vcs, scm=scm or self.scm)

    @classmethod
    def _create_default(cls) -> Self:
        """
        Creates a default initialized instance safely without ignores.

        Returns:
            A default container context directory instance.
        """
        return cls(
            vcs=SDKModuleInitContextDirectoryVcs(exclude_files_folders=frozenset()),
            scm=SDKModuleInitContextDirectoryScm(
                github_actions_workflows=GitHubActionsWorkflows(
                    actions=frozenset(), workflows=GitHubWorkflows()
                ),
                gitlab_jobs_stages=GitLabJobsStages(jobs=frozenset(), stages=GitLabStages()),
            ),
        )


@dataclass(frozen=True, slots=True)
class SDKModuleInitContextContainer:
    """Configuration context applied when bootstrapping systemic execution containers.

    Attributes:
        apt_packages: A frozen set of Linux apt utility package dependencies to inject.
    """

    apt_packages: frozenset[str]

    def evolve(self, *, apt_packages: frozenset[str] | None = None) -> Self:
        """
        Type-safe leaf evolution. Falls back to current value if None.

        Args:
            apt_packages: Optional new frozen set of system package targets.

        Returns:
            An updated container initialization context instance.
        """
        return replace(
            self,
            apt_packages=apt_packages if apt_packages is not None else self.apt_packages,
        )

    @classmethod
    def create_default(cls) -> Self:
        """
        Creates a default initialized instance safely without ignores.

        Returns:
            A default container context instance.
        """
        return cls(apt_packages=frozenset())
