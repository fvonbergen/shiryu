"""test_python_linter module."""

import dagger
import pytest

from shiryu.main import Shiryu
from shiryu.sdk.common.module import PROJECT_NAME_DEFAULT, SCM, ProjectNameType, SCMType

from .utils.common import Paths, get_all_paths
from .utils.python_init import TestCaseInit, build_test_cases_init
from .utils.python_linter import (
    TestCaseFixSuccess,
    TestCaseLint,
    build_test_cases_linter_fix_success,
    build_test_cases_linter_lint_failure,
    build_test_cases_linter_lint_success,
)


def python_linter_init_paths(project_name: ProjectNameType, scm: SCMType) -> Paths:
    """
    Get python linter initializer paths.

    Args:
        project_name: Project name.
        scm: Project Source Code Management (SCM) list to be targeted or configured.

    Returns:
        The python linter initializer paths.
    """
    return (
        *(
            (".gitlab/jobs/.linter_lint.yml", ".gitlab/stages/quality.yml")
            if SCM.GITLAB in scm
            else ()
        ),
        *(
            (".github/actions/linter_lint/action.yml", ".github/workflows/quality.yml")
            if SCM.GITHUB in scm
            else ()
        ),
        *("ruff.toml",),
    )


TEST_CASES_LINTER_INIT = build_test_cases_init((python_linter_init_paths,))


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES_LINTER_INIT, ids=lambda test_case: test_case.name)
async def test_python_linter_init(dagger_client: dagger.Client, test_case: TestCaseInit) -> None:
    """
    Test python linter init function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    directory = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .linter()()
        .init(
            project_name=inputs.project_name,
            project_directory=inputs.project_directory,
            is_update=inputs.is_update,
            scm=inputs.scm,
            platform=inputs.platform,
        )
    )

    assert await get_all_paths(directory) == test_case.output.paths


TEST_CASES_LINTER_LINT_SUCCESS = build_test_cases_linter_lint_success()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case", TEST_CASES_LINTER_LINT_SUCCESS, ids=lambda test_case: test_case.name
)
async def test_python_linter_lint_success(
    dagger_client: dagger.Client, test_case: TestCaseLint
) -> None:
    """
    Test python linter lint function module success calls.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
        test_case: A test case.
    """
    file = test_case.inputs.file
    project_name = PROJECT_NAME_DEFAULT
    project_directory = dagger.dag.directory()
    platform = dagger.Platform("linux/amd64")

    project_directory = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .linter()()
        .init(project_name=project_name, project_directory=project_directory, platform=platform)
    )
    if file is not None:
        project_directory = project_directory.with_new_file(
            path=str(file.path), contents=file.contents
        )
    stdout = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .linter()()
        .lint(project_directory=project_directory, platform=platform)
    )

    assert stdout == test_case.output.expected_stdout


TEST_CASES_LINTER_LINT_FAILURE = build_test_cases_linter_lint_failure()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case", TEST_CASES_LINTER_LINT_FAILURE, ids=lambda test_case: test_case.name
)
async def test_python_linter_lint_failure(
    dagger_client: dagger.Client, test_case: TestCaseLint
) -> None:
    """
    Test python linter lint function module failure calls.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
        test_case: A test case.
    """
    file = test_case.inputs.file
    project_name = PROJECT_NAME_DEFAULT
    project_directory = dagger.dag.directory()
    platform = dagger.Platform("linux/amd64")

    project_directory = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .linter()()
        .init(project_name=project_name, project_directory=project_directory, platform=platform)
    )
    if file is not None:
        project_directory = project_directory.with_new_file(
            path=str(file.path), contents=file.contents
        )
    with pytest.raises(dagger.ExecError) as exc_info:
        await (
            Shiryu.python()  # type: ignore[attr-defined]
            .linter()()
            .lint(project_directory=project_directory, platform=platform)
        )

    assert str(exc_info.value.stdout) == test_case.output.expected_stdout


TEST_CASES_LINTER_FIX_SUCCESS = build_test_cases_linter_fix_success()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case", TEST_CASES_LINTER_FIX_SUCCESS, ids=lambda test_case: test_case.name
)
async def test_python_linter_fix_success(
    dagger_client: dagger.Client, test_case: TestCaseFixSuccess
) -> None:
    """
    Test python linter fix function module success calls.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
        test_case: A test case.
    """
    file = test_case.inputs.file
    project_name = PROJECT_NAME_DEFAULT
    project_directory = dagger.dag.directory()
    platform = dagger.Platform("linux/amd64")

    project_directory = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .linter()()
        .init(project_name=project_name, project_directory=project_directory, platform=platform)
    )
    if file is not None:
        project_directory = project_directory.with_new_file(
            path=str(file.path), contents=file.contents
        )
    directory = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .linter()()
        .fix(project_directory=project_directory, platform=platform)
    )

    assert await get_all_paths(directory) == test_case.output.paths
