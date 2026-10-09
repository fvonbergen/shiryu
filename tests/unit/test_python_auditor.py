"""test_python_auditor module."""

import dagger
import pytest

from shiryu.main import Shiryu
from shiryu.sdk.common.module import SCM, ProjectNameType, SCMType

from .utils.common import Paths
from .utils.python_init import TestCaseInit, build_test_cases_init


def python_auditor_init_paths(project_name: ProjectNameType, scm: SCMType) -> Paths:
    """Get python auditor initializer paths.

    Args:
        project_name: Project name.
        scm: Project Source Code Management (SCM) list to be targeted or configured.

    Returns:
        The python auditor initializer paths.
    """
    return (
        *(
            (
                ".gitlab/jobs/.auditor_audit.yml",
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
                ".github/actions/auditor_audit/",
                ".github/actions/auditor_audit/action.yml",
                ".github/workflows/",
                ".github/workflows/quality.yml",
            )
            if SCM.GITHUB in scm
            else ()
        ),
    )


TEST_CASES_AUDITOR_INIT = build_test_cases_init((python_auditor_init_paths,))


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES_AUDITOR_INIT, ids=lambda test_case: test_case.name)
async def test_python_auditor_init(dagger_session: dagger.Session, test_case: TestCaseInit) -> None:
    """Test python auditor init function module.

    Args:
        dagger_session: The active Dagger engine session fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    init_changeset = (
        await (await Shiryu.create(ws=inputs.workspace))
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .auditor()
        .init(
            project_name=inputs.project_name,
            is_update=inputs.is_update,
            scm=inputs.scm,
            platform=inputs.platform,
        )
    )

    assert tuple(await init_changeset.added_paths()) == test_case.output.paths
