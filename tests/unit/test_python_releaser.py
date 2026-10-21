"""test_python_releaser module."""

import json
from unittest.mock import AsyncMock, MagicMock, call

import dagger
import pytest
from dagger_clients.core import Container, ReturnType

from shiryu.main import Shiryu
from shiryu.sdk.common.module import SCM, ProjectNameType, SCMType
from shiryu.sdk.python.module import ExecutionMode
from shiryu.sdk.python.modules.releaser import (
    VCS_USER_EMAIL_DAGGER_DEFAULT,
    VCS_USER_NAME_DAGGER_DEFAULT,
    Releaser,
    build_release_request,
)

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
    ("vcs_user_name", "vcs_user_email"),
    [
        (VCS_USER_NAME_DAGGER_DEFAULT, VCS_USER_EMAIL_DAGGER_DEFAULT),
        ("Release Bot", "release@example.com"),
    ],
    ids=["default_identity", "custom_identity"],
)
async def test_python_releaser_bump_git_identity(vcs_user_name: str, vcs_user_email: str) -> None:
    """Ensure bump sets both Git identities before running Commitizen.

    Args:
        vcs_user_name: Release commit author and committer name.
        vcs_user_email: Release commit author and committer email.
    """
    container = MagicMock(spec=Container)
    container.with_env_variable.return_value = container
    executed_container = container.with_exec.return_value
    executed_container.exit_code = AsyncMock(return_value=0)
    executed_container.with_exec.return_value.stdout = AsyncMock(return_value="0.1.0\n")

    bump_container, version = await Releaser._Releaser__bump(
        container, vcs_user_name, vcs_user_email
    )

    assert container.mock_calls[:5] == [
        call.with_env_variable("GIT_AUTHOR_NAME", vcs_user_name),
        call.with_env_variable("GIT_AUTHOR_EMAIL", vcs_user_email),
        call.with_env_variable("GIT_COMMITTER_NAME", vcs_user_name),
        call.with_env_variable("GIT_COMMITTER_EMAIL", vcs_user_email),
        call.with_exec(
            Releaser._build_uv_run_command(
                ["cz", "bump", "--yes"], execution_mode=ExecutionMode.SCRIPT
            ),
            expect=ReturnType.ANY,
        ),
    ]
    assert bump_container is executed_container
    assert version == "0.1.0"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case", TEST_CASES_RELEASER_INIT, ids=lambda test_case: test_case.name
)
async def test_python_releaser_init(
    dagger_session: dagger.Session, test_case: TestCaseInit
) -> None:
    """Test python releaser init function module.

    Args:
        dagger_session: The active Dagger engine session fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    init_changeset = (
        await (await Shiryu.create(ws=inputs.workspace))
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
