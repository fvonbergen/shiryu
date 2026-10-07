"""test_python_checker module."""

import dagger
import pytest

from shiryu.main import Shiryu
from shiryu.sdk.common.module import PROJECT_NAME_DEFAULT, SCM, ProjectNameType, SCMType

from .utils.common import Paths
from .utils.python_init import TestCaseInit, build_test_cases_init


def python_checker_init_paths(project_name: ProjectNameType, scm: SCMType) -> Paths:
    """Get python checker initializer paths.

    Args:
        project_name: Project name.
        scm: Project Source Code Management (SCM) list to be targeted or configured.

    Returns:
        The python checker initializer paths.
    """
    return (
        *(
            (".gitlab/jobs/.checker_check.yml", ".gitlab/stages/", ".gitlab/stages/quality.yml")
            if SCM.GITLAB in scm
            else ()
        ),
        *(
            (
                ".github/",
                ".github/actions/",
                ".github/actions/checker_check/",
                ".github/actions/checker_check/action.yml",
                ".github/workflows/",
                ".github/workflows/quality.yml",
            )
            if SCM.GITHUB in scm
            else ()
        ),
        *("ty.toml",),
    )


TEST_CASES = build_test_cases_init((python_checker_init_paths,))


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda test_case: test_case.name)
async def test_python_checker_init(dagger_client: dagger.Client, test_case: TestCaseInit) -> None:
    """Test python checker init function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    init_changeset = (
        await Shiryu(source=inputs.source)  # pyright: ignore[reportCallIssue]
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .checker()
        .init(
            project_name=inputs.project_name,
            is_update=inputs.is_update,
            scm=inputs.scm,
            platform=inputs.platform,
        )
    )

    assert tuple(await init_changeset.added_paths()) == test_case.output.paths


@pytest.mark.asyncio
async def test_python_checker_check(dagger_client: dagger.Client) -> None:
    """Test python checker check function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
    """
    source = dagger.dag.directory()
    project_name = PROJECT_NAME_DEFAULT
    platform = dagger.Platform("linux/amd64")

    init_changeset = (
        await Shiryu(source=source)  # pyright: ignore[reportCallIssue]
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .checker()
        .init(project_name=project_name, platform=platform)
    )
    init_source = source.with_changes(init_changeset)
    await Shiryu(source=init_source).python().checker().check(platform=platform)  # ty: ignore[unresolved-attribute] # pyright: ignore[reportCallIssue, reportAttributeAccessIssue]
