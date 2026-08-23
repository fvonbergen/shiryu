"""test_python_releaser module."""

import dagger
import pytest

from shiryu.main import Shiryu
from shiryu.sdk.common.module import SCM, ProjectNameType, SCMType

from .utils.common import Paths, get_all_paths
from .utils.python_init import TestCaseInit, build_test_cases_init


def python_releaser_init_paths(project_name: ProjectNameType, scm: SCMType) -> Paths:
    """Get python releaser initializer paths.

    Args:
        project_name: Project name.
        scm: Project Source Code Management (SCM) list to be targeted or configured.

    Returns:
        The python releaser initializer paths.
    """
    return (
        *(
            (
                ".gitlab/jobs/.releaser_release.yml",
                ".gitlab/stages/release.yml",
            )
            if SCM.GITLAB in scm
            else ()
        ),
        *(
            (
                ".github/actions/releaser_release/action.yml",
                ".github/workflows/release.yml",
            )
            if SCM.GITHUB in scm
            else ()
        ),
        *(".cz.toml",),
    )


TEST_CASES_RELEASER_INIT = build_test_cases_init((python_releaser_init_paths,))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case", TEST_CASES_RELEASER_INIT, ids=lambda test_case: test_case.name
)
async def test_python_releaser_init(dagger_client: dagger.Client, test_case: TestCaseInit) -> None:
    """Test python releaser init function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    directory = (
        await Shiryu.python()  # ty: ignore[unresolved-attribute]
        .releaser()()
        .init(
            project_name=inputs.project_name,
            project_directory=inputs.project_directory,
            is_update=inputs.is_update,
            scm=inputs.scm,
            platform=inputs.platform,
        )
    )

    assert await get_all_paths(directory) == test_case.output.paths
