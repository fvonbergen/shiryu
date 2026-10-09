"""test_python_linter module."""

import dagger
import pytest
from dagger_clients.core import Platform, core

from shiryu.main import Shiryu
from shiryu.sdk.common.module import SCM, ProjectNameType, SCMType

from .utils.common import PROJECT_NAME_DEFAULT, Paths
from .utils.python_init import TestCaseInit, build_test_cases_init
from .utils.python_linter import (
    TestCaseFixCodeSuccess,
    TestCaseLintCodeFailure,
    TestCaseLintCodeSuccess,
    build_test_cases_linter_fix_code_success,
    build_test_cases_linter_lint_code_failure,
    build_test_cases_linter_lint_code_success,
)


def python_linter_init_paths(project_name: ProjectNameType, scm: SCMType) -> Paths:
    """Get python linter initializer paths.

    Args:
        project_name: Project name.
        scm: Project Source Code Management (SCM) list to be targeted or configured.

    Returns:
        The python linter initializer paths.
    """
    return (
        *(
            (
                ".gitlab/jobs/.linter_lint_code.yml",
                ".gitlab/jobs/.linter_lint_vcs.yml",
                ".gitlab/stages/",
                ".gitlab/stages/quality.yml",
            )
            if SCM.GITLAB in scm
            else ()
        ),
        *(
            (
                ".github/",
                ".github/actions/",
                ".github/actions/linter_lint_code/",
                ".github/actions/linter_lint_code/action.yml",
                ".github/actions/linter_lint_vcs/",
                ".github/actions/linter_lint_vcs/action.yml",
                ".github/workflows/",
                ".github/workflows/quality.yml",
            )
            if SCM.GITHUB in scm
            else ()
        ),
        *(
            "cchk.toml",
            "ruff.toml",
        ),
    )


TEST_CASES_LINTER_INIT = build_test_cases_init((python_linter_init_paths,))


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES_LINTER_INIT, ids=lambda test_case: test_case.name)
async def test_python_linter_init(dagger_session: dagger.Session, test_case: TestCaseInit) -> None:
    """Test python linter init function module.

    Args:
        dagger_session: The active Dagger engine session fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    init_changeset = (
        await (await Shiryu.create(ws=inputs.workspace))
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .linter()
        .init(
            project_name=inputs.project_name,
            is_update=inputs.is_update,
            scm=inputs.scm,
            platform=inputs.platform,
        )
    )

    assert tuple(await init_changeset.added_paths()) == test_case.output.paths


TEST_CASES_LINTER_LINT_CODE_SUCCESS = build_test_cases_linter_lint_code_success()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case", TEST_CASES_LINTER_LINT_CODE_SUCCESS, ids=lambda test_case: test_case.name
)
async def test_python_linter_lint_code_success(
    dagger_session: dagger.Session, test_case: TestCaseLintCodeSuccess
) -> None:
    """Test python linter lint code function module success calls.

    Args:
        dagger_session: The active Dagger engine session fixture.
        test_case: A test case.
    """
    file = test_case.inputs.file
    source = core().directory()
    project_name = PROJECT_NAME_DEFAULT
    platform = Platform("linux/amd64")

    init_changeset = (
        await (await Shiryu.create(ws=source.as_workspace()))
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .linter()
        .init(project_name=project_name, platform=platform)
    )
    init_source = source.with_changes(init_changeset)
    if file is not None:
        init_source = init_source.with_new_file(path=str(file.path), contents=file.contents)
    await (
        (await Shiryu.create(ws=init_source.as_workspace()))
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .linter()
        .lint_code(platform=platform)
    )


TEST_CASES_LINTER_LINT_CODE_FAILURE = build_test_cases_linter_lint_code_failure()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case", TEST_CASES_LINTER_LINT_CODE_FAILURE, ids=lambda test_case: test_case.name
)
async def test_python_linter_lint_code_failure(
    dagger_session: dagger.Session, test_case: TestCaseLintCodeFailure
) -> None:
    """Test python linter lint code function module failure calls.

    Args:
        dagger_session: The active Dagger engine session fixture.
        test_case: A test case.
    """
    file = test_case.inputs.file
    source = core().directory()
    project_name = PROJECT_NAME_DEFAULT
    platform = Platform("linux/amd64")

    init_changeset = (
        await (await Shiryu.create(ws=source.as_workspace()))
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .linter()
        .init(project_name=project_name, platform=platform)
    )
    init_source = source.with_changes(init_changeset)
    if file is not None:
        init_source = init_source.with_new_file(path=str(file.path), contents=file.contents)
    with pytest.raises(dagger.ExecError) as exc_info:
        await (
            (await Shiryu.create(ws=init_source.as_workspace()))
            .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
            .linter()
            .lint_code(platform=platform)
        )

    assert str(exc_info.value.stdout) == test_case.output.expected_stdout


TEST_CASES_LINTER_FIX_CODE_SUCCESS = build_test_cases_linter_fix_code_success()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case", TEST_CASES_LINTER_FIX_CODE_SUCCESS, ids=lambda test_case: test_case.name
)
async def test_python_linter_fix_success(
    dagger_session: dagger.Session, test_case: TestCaseFixCodeSuccess
) -> None:
    """Test python linter fix code function module success calls.

    Args:
        dagger_session: The active Dagger engine session fixture.
        test_case: A test case.
    """
    file = test_case.inputs.file
    source = core().directory()
    project_name = PROJECT_NAME_DEFAULT
    platform = Platform("linux/amd64")

    init_changeset = (
        await (await Shiryu.create(ws=source.as_workspace()))
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .linter()
        .init(project_name=project_name, platform=platform)
    )
    init_source = source.with_changes(init_changeset)
    if file is not None:
        init_source = init_source.with_new_file(path=str(file.path), contents=file.contents)
    changeset = (
        await (await Shiryu.create(ws=init_source.as_workspace()))
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .linter()
        .fix_code(platform=platform)
    )

    assert tuple(await changeset.added_paths()) == test_case.output.paths
