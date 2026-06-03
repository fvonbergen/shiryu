"""python_init module."""

from collections.abc import Callable
from itertools import chain, product
from typing import NamedTuple, final

import dagger

from shiryu.sdk.common.module import (
    PROJECT_NAME_DEFAULT,
    SCM,
    IsUpdateType,
    PlatformType,
    ProjectDirectoryType,
    ProjectNameType,
    SCMType,
)
from shiryu.sdk.python.utils import get_package_name_canonical

from .common import DirectoryOutput, Paths, ignore_pytest


@final
class TestCaseInitInputs(NamedTuple):
    """TestCaseInitInputs class."""

    project_name: ProjectNameType
    project_directory: ProjectDirectoryType
    is_update: IsUpdateType
    scm: SCMType
    platform: PlatformType


@final
@ignore_pytest
class TestCaseInit(NamedTuple):
    """TestCaseInit class."""

    name: str
    inputs: TestCaseInitInputs
    output: DirectoryOutput


def __python_init_paths(project_name: ProjectNameType, scm: SCMType) -> Paths:
    """
    Get python initializer paths.

    Args:
        project_name: Project name.
        scm: Project Source Code Management (SCM) list to be targeted or configured.

    Returns:
        The python initializer paths.
    """
    package_name_canonical = get_package_name_canonical(project_name)
    return (
        ".git/HEAD",
        ".git/branches/",
        ".git/config",
        ".git/description",
        ".git/hooks/applypatch-msg.sample",
        ".git/hooks/commit-msg.sample",
        ".git/hooks/fsmonitor-watchman.sample",
        ".git/hooks/post-update.sample",
        ".git/hooks/pre-applypatch.sample",
        ".git/hooks/pre-commit.sample",
        ".git/hooks/pre-merge-commit.sample",
        ".git/hooks/pre-push.sample",
        ".git/hooks/pre-rebase.sample",
        ".git/hooks/pre-receive.sample",
        ".git/hooks/prepare-commit-msg.sample",
        ".git/hooks/push-to-checkout.sample",
        ".git/hooks/sendemail-validate.sample",
        ".git/hooks/update.sample",
        ".git/info/exclude",
        ".git/objects/info/",
        ".git/objects/pack/",
        ".git/refs/heads/",
        ".git/refs/tags/",
        ".gitignore",
        *(
            (
                ".gitlab-ci.yml",
                ".gitlab/jobs/.dagger.yml",
            )
            if SCM.GITLAB in scm
            else ()
        ),
        "CHANGELOG.md",
        "README.md",
        "pyproject.toml",
        f"src/{package_name_canonical}/__init__.py",
        f"src/{package_name_canonical}/py.typed",
        "uv.lock",
    )


ModulesInitPathsCallable = Callable[[ProjectNameType, SCMType], Paths]


def __expected_paths(
    project_name: ProjectNameType,
    scm: SCMType,
    modules_init_paths_functions: tuple[ModulesInitPathsCallable, ...],
) -> Paths:
    """
    Get the module init expected paths.

    Args:
        project_name: Project name.
        scm: Project Source Code Management (SCM) list to be targeted or configured.
        modules_init_paths_functions: Callable functions to generate module initialization paths.

    Returns:
        The module init expected paths.
    """
    return tuple(
        sorted(
            (
                *__python_init_paths(project_name, scm),
                *set(
                    chain.from_iterable(
                        module_init_paths_function(project_name, scm)
                        for module_init_paths_function in modules_init_paths_functions
                    )
                ),
            )
        )
    )


def build_test_cases_init(
    modules_init_paths_functions: tuple[ModulesInitPathsCallable, ...],
) -> tuple[TestCaseInit, ...]:
    """
    Builds the test cases used for testing init calls.

    Args:
        modules_init_paths_functions: Callable functions to generate module initialization paths.

    Returns:
        The test cases.
    """
    # TODO: tests against more project names (e.g. test, test-test, etc.)
    project_name = PROJECT_NAME_DEFAULT
    project_directory = dagger.dag.directory()
    platform = dagger.Platform("linux/amd64")
    is_update_options = (False, True)
    scm_options = (SCM.GITLAB, SCM.GITHUB)
    test_cases_inputs = tuple(
        TestCaseInitInputs(
            project_name=project_name,
            project_directory=project_directory,
            is_update=is_update,
            scm=[scm],
            platform=platform,
        )
        for is_update, scm in product(is_update_options, scm_options)
    )
    return tuple(
        TestCaseInit(
            name=f"is_update={test_case_init_inputs.is_update},scm={list(test_case_init_inputs.scm)}",
            inputs=test_case_init_inputs,
            output=DirectoryOutput(
                paths=__expected_paths(
                    test_case_init_inputs.project_name,
                    test_case_init_inputs.scm,
                    modules_init_paths_functions,
                )
            ),
        )
        for test_case_init_inputs in test_cases_inputs
    )
