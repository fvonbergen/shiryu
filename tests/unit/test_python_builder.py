"""test_python_builder module."""

import re

import dagger
import pytest
from dagger_clients.core import Platform, core

from shiryu.main import Shiryu
from shiryu.sdk.common.module import SCM, ProjectNameType, SCMType
from shiryu.sdk.python.utils import get_package_name_canonical

from .utils.common import PROJECT_NAME_DEFAULT, Paths
from .utils.python_init import TestCaseInit, build_test_cases_init


def python_builder_init_paths(project_name: ProjectNameType, scm: SCMType) -> Paths:
    """Get python builder initializer paths.

    Args:
        project_name: Project name.
        scm: Project Source Code Management (SCM) list to be targeted or configured.

    Returns:
        The python builder initializer paths.
    """
    return (
        *(
            (
                ".gitlab/jobs/.builder_publish.yml",
                ".gitlab/jobs/.builder_test.yml",
                ".gitlab/stages/",
                ".gitlab/stages/quality.yml",
                ".gitlab/stages/release.yml",
            )
            if SCM.GITLAB in scm
            else ()
        ),
        *(
            (
                ".github/",
                ".github/actions/",
                ".github/actions/builder_publish/",
                ".github/actions/builder_publish/action.yml",
                ".github/actions/builder_test/",
                ".github/actions/builder_test/action.yml",
                ".github/workflows/",
                ".github/workflows/quality.yml",
                ".github/workflows/release.yml",
            )
            if SCM.GITHUB in scm
            else ()
        ),
    )


TEST_CASES = build_test_cases_init((python_builder_init_paths,))


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda test_case: test_case.name)
async def test_python_builder_init(dagger_session: dagger.Session, test_case: TestCaseInit) -> None:
    """Test python builder init function module.

    Args:
        dagger_session: The active Dagger engine session fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    init_changeset = (
        await (await Shiryu.create(ws=inputs.workspace))
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .builder()
        .init(
            project_name=inputs.project_name,
            is_update=inputs.is_update,
            scm=inputs.scm,
            platform=inputs.platform,
        )
    )

    assert tuple(await init_changeset.added_paths()) == test_case.output.paths


@pytest.mark.asyncio
async def test_python_builder_build(dagger_session: dagger.Session) -> None:
    """Test python builder build function module.

    Args:
        dagger_session: The active Dagger engine session fixture.
    """
    source = core().directory()
    project_name = PROJECT_NAME_DEFAULT
    package_name_canonical = get_package_name_canonical(project_name)
    platform = Platform("linux/amd64")

    init_changeset = (
        await (await Shiryu.create(ws=source.as_workspace()))
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .builder()
        .init(project_name=project_name, platform=platform)
    )
    init_source = source.with_changes(init_changeset)
    build_changeset = (
        await (await Shiryu.create(ws=init_source.as_workspace()))
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .builder()
        .build(platform=platform)
    )
    date_pattern = r"\d{4}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])"
    expected_changeset_patterns = (
        "^dist/$",
        "^dist/linux/$",
        "^dist/linux/amd64/$",
        rf"^dist/linux/amd64/{package_name_canonical}-0\.0\.1\.dev0\+unknown\.d{date_pattern}-py3-none-any\.whl$",
        rf"^dist/linux/amd64/{package_name_canonical}-0\.0\.1\.dev0\+unknown\.d{date_pattern}\.tar\.gz$",
    )

    for changeset, pattern in zip(
        await build_changeset.added_paths(), expected_changeset_patterns, strict=True
    ):
        assert re.compile(pattern).fullmatch(changeset)


@pytest.mark.asyncio
async def test_python_builder_test(dagger_session: dagger.Session) -> None:
    """Test python builder test function module.

    Args:
        dagger_session: The active Dagger engine session fixture.
    """
    source = core().directory()
    project_name = PROJECT_NAME_DEFAULT
    platform = Platform("linux/amd64")

    init_changeset = (
        await (await Shiryu.create(ws=source.as_workspace()))
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .builder()
        .init(project_name=project_name, platform=platform)
    )
    init_source = source.with_changes(init_changeset)
    await (
        (await Shiryu.create(ws=init_source.as_workspace()))
        .python()  # ty: ignore[unresolved-attribute] # pyright: ignore[reportAttributeAccessIssue]
        .builder()
        .test(platform=platform)
    )
