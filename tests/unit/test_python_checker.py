"""test_python_checker module."""

import dagger
import pytest

from shiryu.main import Shiryu
from shiryu.sdk.common.module import SCM, ProjectNameType, SCMListType

from .utils.common import Paths, get_all_paths
from .utils.python_init import TestCaseInit, build_test_cases_init


def python_checker_init_paths(project_name: ProjectNameType, scm: SCMListType) -> Paths:
    """
    Get python checker initializer paths.

    Args:
        project_name: Project name.
        scm: Project Source Code Management (SCM) list to be targeted or configured.

    Returns:
        The python checker initializer paths.
    """
    return (
        *(
            (
                ".gitlab/jobs/.checker_check.yml",
                ".gitlab/stages/quality.yml",
            )
            if SCM.GITLAB in scm
            else ()
        ),
        *(
            (
                ".github/actions/checker_check/action.yml",
                ".github/workflows/quality.yml",
            )
            if SCM.GITHUB in scm
            else ()
        ),
        *("mypy.ini",),
    )


TEST_CASES = build_test_cases_init((python_checker_init_paths,))


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda test_case: test_case.name)
async def test_python_checker_init(
    dagger_client: dagger.Client, test_case: TestCaseInit
) -> None:
    """
    Test python checker init function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    directory = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .checker()()
        .init(
            project_name=inputs.project_name,
            project_directory=inputs.project_directory,
            is_update=inputs.is_update,
            scm=inputs.scm,
            platform=inputs.platform,
        )
    )

    assert await get_all_paths(directory) == test_case.output.paths


@pytest.mark.asyncio
async def test_python_checker_check(dagger_client: dagger.Client) -> None:
    """
    Test python checker check function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
    """
    project_directory = dagger.dag.directory()
    platform = dagger.Platform("linux/amd64")

    stdout = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .checker()()
        .check(project_directory=project_directory, platform=platform)
    )

    assert stdout == "Check successfull"
