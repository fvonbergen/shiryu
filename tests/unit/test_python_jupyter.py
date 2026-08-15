"""test_python_jupyter module."""

import dagger
import pytest

from shiryu.main import Shiryu
from shiryu.sdk.common.module import ProjectNameType, SCMType

from .utils.common import Paths, get_all_paths
from .utils.python_init import TestCaseInit, build_test_cases_init


def python_jupyter_init_paths(project_name: ProjectNameType, scm: SCMType) -> Paths:
    """
    Get python jupyter initializer paths.

    Args:
        project_name: Project name.
        scm: Project Source Code Management (SCM) list to be targeted or configured.

    Returns:
        The python jupyter initializer paths.
    """
    return ("notebooks/playground.ipynb",)


TEST_CASES = build_test_cases_init((python_jupyter_init_paths,))


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda test_case: test_case.name)
async def test_python_builder_init(dagger_client: dagger.Client, test_case: TestCaseInit) -> None:
    """
    Test python jupyter init function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    directory = (
        await Shiryu.python()  # ty: ignore[unresolved-attribute]
        .jupyter()()
        .init(
            project_name=inputs.project_name,
            project_directory=inputs.project_directory,
            is_update=inputs.is_update,
            scm=inputs.scm,
            platform=inputs.platform,
        )
    )

    assert await get_all_paths(directory) == test_case.output.paths
