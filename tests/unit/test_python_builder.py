"""test_python_builder module."""

import re

import dagger
import pytest

from shiryu.main import Shiryu
from shiryu.sdk.common.module import PROJECT_NAME_DEFAULT, SCM, ProjectNameType, SCMType
from shiryu.sdk.python.utils import get_package_name_canonical

from .utils.common import Paths, get_all_paths
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
                ".gitlab/stages/quality.yml",
                ".gitlab/stages/release.yml",
            )
            if SCM.GITLAB in scm
            else ()
        ),
        *(
            (
                ".github/actions/builder_publish/action.yml",
                ".github/actions/builder_test/action.yml",
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
async def test_python_builder_init(dagger_client: dagger.Client, test_case: TestCaseInit) -> None:
    """Test python builder init function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    directory = (
        await Shiryu.python()  # ty: ignore[unresolved-attribute]
        .builder()()
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
async def test_python_builder_build(dagger_client: dagger.Client) -> None:
    """Test python builder build function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
    """
    project_name = PROJECT_NAME_DEFAULT
    package_name_canonical = get_package_name_canonical(project_name)
    project_directory = dagger.dag.directory()
    platform = dagger.Platform("linux/amd64")

    project_directory = (
        await Shiryu.python()  # ty: ignore[unresolved-attribute]
        .builder()()
        .init(project_name=project_name, project_directory=project_directory, platform=platform)
    )
    directory = (
        await Shiryu.python()  # ty: ignore[unresolved-attribute]
        .builder()()
        .build(project_directory=project_directory, platform=platform)
    )
    paths = await get_all_paths(directory)
    date_pattern = r"\d{4}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])"
    expected_paths_compiled_patterns = (
        re.compile(
            rf"^dist/linux/amd64/{package_name_canonical}-0\.0\.1\.dev0\+unknown\.d{date_pattern}-py3-none-any\.whl$"
        ),
        re.compile(
            rf"^dist/linux/amd64/{package_name_canonical}-0\.0\.1\.dev0\+unknown\.d{date_pattern}\.tar\.gz$"
        ),
    )

    for path, pattern in zip(paths, expected_paths_compiled_patterns, strict=True):
        assert pattern.match(path)


@pytest.mark.asyncio
async def test_python_builder_test(dagger_client: dagger.Client) -> None:
    """Test python builder test function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
    """
    project_name = PROJECT_NAME_DEFAULT
    project_directory = dagger.dag.directory()
    platform = dagger.Platform("linux/amd64")

    project_directory = (
        await Shiryu.python()  # ty: ignore[unresolved-attribute]
        .builder()()
        .init(project_name=project_name, project_directory=project_directory, platform=platform)
    )
    stdout = (
        await Shiryu.python()  # ty: ignore[unresolved-attribute]
        .builder()()
        .test(project_directory=project_directory, platform=platform)
    )

    assert stdout == "Test build successfull"
