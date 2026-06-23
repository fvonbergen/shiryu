"""test_python_init module."""

import dagger
import pytest

from shiryu.main import Shiryu

from .test_python_auditor import python_auditor_init_paths
from .test_python_builder import python_builder_init_paths
from .test_python_checker import python_checker_init_paths
from .test_python_documenter import python_documenter_init_paths
from .test_python_jupyter import python_jupyter_init_paths
from .test_python_linter import python_linter_init_paths
from .test_python_tester import python_tester_init_paths
from .utils.common import get_all_paths
from .utils.python_init import TestCaseInit, build_test_cases_init

TEST_CASES = build_test_cases_init(
    (
        python_auditor_init_paths,
        python_builder_init_paths,
        python_checker_init_paths,
        python_documenter_init_paths,
        python_jupyter_init_paths,
        python_linter_init_paths,
        python_tester_init_paths,
    )
)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda test_case: test_case.name)
async def test_python_init(dagger_client: dagger.Client, test_case: TestCaseInit) -> None:
    """
    Test python init function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    directory = await Shiryu.python()().init(  # type: ignore[attr-defined]
        project_name=inputs.project_name,
        project_directory=inputs.project_directory,
        is_update=inputs.is_update,
        scm=inputs.scm,
        platform=inputs.platform,
    )

    assert await get_all_paths(directory) == test_case.output.paths
