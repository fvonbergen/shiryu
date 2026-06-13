"""
Context module for Python-specific SDK initialization operations.

This module provides data models and context containers tailored for initializing Python modules. It
manages structural immutability for dependency groups and specializes core SDK directory and module
initialization contexts.
"""

from collections.abc import ItemsView, Mapping, Set
from dataclasses import InitVar, dataclass, field, replace
from types import MappingProxyType
from typing import Self, final

from ..common.context import (
    GitHubActionsWorkflows,
    GitHubWorkflows,
    GitLabJobsStages,
    GitLabStages,
    SDKModuleInitContextDirectory,
    SDKModuleInitContextDirectoryScm,
    SDKModuleInitContextDirectoryVcs,
)

DistributionPackages = frozenset[str]


@final
@dataclass(frozen=True, slots=True)
class DependencyGroups:
    """
    DependencyGroups class with enforced read-only structural immutability.

    Wraps a mapping proxy containing mappings of group names to sets of package requirements.

    Args:
        dependency_groups_input: Initial mapping of group names to their package requirements.

    Attributes:
        _dependency_groups: Internal read-only group-to-packages mapping proxy.
    """

    _dependency_groups: MappingProxyType[str, DistributionPackages] = field(
        init=False, default_factory=lambda: MappingProxyType({})
    )
    dependency_groups_input: InitVar[Mapping[str, Set[str] | DistributionPackages] | None] = None

    def __post_init__(self, dependency_groups_input: Mapping[str, Set[str]] | None) -> None:
        """Process the input dictionary into immutable structures post-initialization.

        Args:
            dependency_groups_input: Raw dictionary input passed via construction.
        """
        if dependency_groups_input is not None:
            immutable_data = {
                group_name: frozenset(packages)
                for group_name, packages in dependency_groups_input.items()
            }
            object.__setattr__(self, "_dependency_groups", MappingProxyType(immutable_data))

    def add(self, group_name: str, packages: Set[str]) -> "DependencyGroups":
        """
        Add a collection of dependency packages to a dependency group name.

        Args:
            group_name: The target dependency group name.
            packages: Distribution package names to add to the group.

        Returns:
            A new DependencyGroups instance containing the updated state.
        """
        current_packages: DistributionPackages = self._dependency_groups.get(
            group_name, frozenset()
        )

        # Unpack the proxy into a temporary flat dict to safely add the data
        updated_dict: dict[str, DistributionPackages] = dict(self._dependency_groups)
        updated_dict[group_name] = current_packages | frozenset(packages)

        return DependencyGroups(MappingProxyType(updated_dict))

    def merge(self, other: "DependencyGroups") -> "DependencyGroups":
        """
        Merge another DependencyGroups instance into a brand new state.

        Args:
            other: A DependencyGroups instance to merge into this one.

        Returns:
            A new DependencyGroups instance representing the union of both states.
        """
        merged_dict: dict[str, DistributionPackages] = dict(self._dependency_groups)
        for group_name, packages in other.items():
            merged_dict[group_name] = merged_dict.get(group_name, frozenset()) | packages

        return DependencyGroups(MappingProxyType(merged_dict))

    def items(self) -> ItemsView[str, DistributionPackages]:
        """
        Return the dependency groups names and packages as key-value pairs.

        Returns:
            The group names and their package sets.
        """
        return self._dependency_groups.items()

    def evolve(
        self,
        dependency_groups: MappingProxyType[str, DistributionPackages] | None = None,
    ) -> "DependencyGroups":
        """
        Type-safe evolution for the underlying dependency groups.

        Args:
            dependency_groups: Python package dependency groups.

        Returns:
            A new DependencyGroups instance with the modified or current state.
        """
        return replace(
            self,
            _dependency_groups=dependency_groups
            if dependency_groups is not None
            else self._dependency_groups,
        )


SourceCodeFilesFolders = frozenset[str]


@final
@dataclass(frozen=True, slots=True)
class PythonModuleInitContextDirectory(SDKModuleInitContextDirectory):
    """
    Python-specific implementation of SDKModuleInitContextDirectory.

    Attributes:
        dependency_groups: Python package dependency groups.
    """

    dependency_groups: DependencyGroups = field(default_factory=DependencyGroups)
    source_code_files_folders: SourceCodeFilesFolders = field(default_factory=frozenset)

    def evolve(
        self,
        vcs: SDKModuleInitContextDirectoryVcs | None = None,
        scm: SDKModuleInitContextDirectoryScm | None = None,
        dependency_groups: DependencyGroups | None = None,
        source_code_files_folders: SourceCodeFilesFolders | None = None,
    ) -> Self:
        """
        Type-safe pure assignment evolution extending base directory capabilities.

        Args:
            vcs: Version control system context configuration.
            scm: Source control management context configuration.
            dependency_groups: Python package dependency groups.
            source_code_files_folders: Source code files and folders configuration.

        Returns:
            A mutated copy of the directory initialization context containing the updates.
        """
        return replace(
            self,
            vcs=vcs or self.vcs,
            scm=scm or self.scm,
            dependency_groups=dependency_groups
            if dependency_groups is not None
            else self.dependency_groups,
            source_code_files_folders=source_code_files_folders or self.source_code_files_folders,
        )

    @classmethod
    def create_default(cls) -> Self:
        """
        Build the default directory.

        Returns:
            A default directory.
        """
        return cls(
            vcs=SDKModuleInitContextDirectoryVcs(exclude_files_folders=frozenset()),
            scm=SDKModuleInitContextDirectoryScm(
                github_actions_workflows=GitHubActionsWorkflows(
                    actions=frozenset(), workflows=GitHubWorkflows()
                ),
                gitlab_jobs_stages=GitLabJobsStages(jobs=frozenset(), stages=GitLabStages()),
            ),
            dependency_groups=DependencyGroups(),
            source_code_files_folders=frozenset(),
        )
