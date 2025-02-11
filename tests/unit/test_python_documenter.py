"""test_python_documenter module."""

import dagger
import pytest

from shiryu.main import Shiryu
from shiryu.sdk.common.module import SCM, ProjectNameType, SCMListType

from .utils.common import Paths, get_all_paths
from .utils.python_init import TestCaseInit, build_test_cases_init


def python_documenter_init_paths(
    project_name: ProjectNameType, scm: SCMListType
) -> Paths:
    """
    Get python documenter initializer paths.

    Args:
        project_name: Project name.
        scm: Project Source Code Management (SCM) list to be targeted or configured.

    Returns:
        The python documenter initializer paths.
    """
    return (
        *(
            (
                ".gitlab/jobs/.documenter_document.yml",
                ".gitlab/stages/deploy.yml",
                ".gitlab/stages/quality.yml",
            )
            if SCM.GITLAB in scm
            else ()
        ),
        *(
            (
                ".github/actions/documenter_document/action.yml",
                ".github/workflows/deploy.yml",
                ".github/workflows/quality.yml",
            )
            if SCM.GITHUB in scm
            else ()
        ),
        *(
            "docs/Makefile",
            "docs/shiryu-templates/conf.py.jinja",
            "docs/source/_static/",
            "docs/source/_templates/",
            "docs/source/conf.py",
            "docs/source/explanation/",
            "docs/source/how_to/",
            "docs/source/index.rst",
            "docs/source/reference/",
            "docs/source/tutorials/",
        ),
    )


TEST_CASES = build_test_cases_init((python_documenter_init_paths,))


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda test_case: test_case.name)
async def test_python_documenter_init(
    dagger_client: dagger.Client, test_case: TestCaseInit
) -> None:
    """
    Test python documenter init function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    directory = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .documenter()()
        .init(
            project_name=inputs.project_name,
            project_directory=inputs.project_directory,
            is_update=inputs.is_update,
            scm=inputs.scm,
            platform=inputs.platform,
        )
    )

    assert await get_all_paths(directory) == test_case.output.paths
