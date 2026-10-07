"""test_python_releaser module."""

import json

import dagger
import pytest

from shiryu.main import Shiryu
from shiryu.sdk.common.module import SCM, ProjectNameType, SCMType
from shiryu.sdk.python.modules.releaser import build_release_request

from .utils.common import Paths
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
                ".gitlab/stages/",
                ".gitlab/stages/release.yml",
            )
            if SCM.GITLAB in scm
            else ()
        ),
        *(
            (
                ".github/",
                ".github/actions/",
                ".github/actions/releaser_release/",
                ".github/actions/releaser_release/action.yml",
                ".github/workflows/",
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

    init_changeset = (
        await Shiryu.create(ws=inputs.workspace)
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .releaser()
        .init(
            project_name=inputs.project_name,
            is_update=inputs.is_update,
            scm=inputs.scm,
            platform=inputs.platform,
        )
    )

    assert tuple(await init_changeset.added_paths()) == test_case.output.paths
    assert await get_all_paths(directory) == test_case.output.paths


@pytest.mark.parametrize(
    ("push_url", "endpoint", "authorization_header", "notes_key"),
    [
        (
            "https://github.com/owner/repo.git",
            "https://api.github.com/repos/owner/repo/releases",
            "Authorization: Bearer",
            "body",
        ),
        (
            "https://gitlab.com/group/repo.git",
            "https://gitlab.com/api/v4/projects/group%2Frepo/releases",
            "PRIVATE-TOKEN:",
            "description",
        ),
        (
            "https://git.example.org:8443/group/subgroup/repo",
            "https://git.example.org:8443/api/v4/projects/group%2Fsubgroup%2Frepo/releases",
            "PRIVATE-TOKEN:",
            "description",
        ),
    ],
    ids=["github", "gitlab", "gitlab_self_managed"],
)
def test_build_release_request(
    push_url: str, endpoint: str, authorization_header: str, notes_key: str
) -> None:
    """Test the release request built for each SCM.

    Args:
        push_url: Credential-free HTTPS push URL.
        endpoint: Expected API endpoint.
        authorization_header: Expected authorization header prefix.
        notes_key: Expected payload key holding the release notes.
    """
    notes = '### Added\n\n- add "quoted" thing'

    request = build_release_request(push_url, "v0.1.0", notes)

    assert request[:2] == (endpoint, authorization_header)
    assert json.loads(request[2]) == {"tag_name": "v0.1.0", "name": "v0.1.0", notes_key: notes}
