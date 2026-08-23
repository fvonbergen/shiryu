"""test_python_documenter module."""

import re

import dagger
import pytest

from shiryu.main import Shiryu
from shiryu.sdk.common.module import PROJECT_NAME_DEFAULT, SCM, ProjectNameType, SCMType

from .utils.common import Paths, get_all_paths
from .utils.python_init import TestCaseInit, build_test_cases_init


def python_documenter_init_paths(project_name: ProjectNameType, scm: SCMType) -> Paths:
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
                ".gitlab/stages/quality.yml",
                ".gitlab/stages/release.yml",
            )
            if SCM.GITLAB in scm
            else ()
        ),
        *(
            (
                ".github/actions/documenter_document/action.yml",
                ".github/workflows/quality.yml",
                ".github/workflows/release.yml",
            )
            if SCM.GITHUB in scm
            else ()
        ),
        *(
            "docs/explanation/index.md",
            "docs/how-to-guides/index.md",
            "docs/reference/index.md",
            "docs/tutorials/index.md",
            "docs/index.md",
            "scripts/gen_ref_pages.py",
            "zensical.toml",
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
        await Shiryu.python()  # ty: ignore[unresolved-attribute]
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


@pytest.mark.asyncio
async def test_python_documenter_document(dagger_client: dagger.Client) -> None:
    """
    Test python documenter document function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
    """
    project_name = PROJECT_NAME_DEFAULT
    project_directory = dagger.dag.directory()
    platform = dagger.Platform("linux/amd64")

    project_directory = (
        await Shiryu.python()  # ty: ignore[unresolved-attribute]
        .documenter()()
        .init(project_name=project_name, project_directory=project_directory, platform=platform)
    )
    directory = (
        await Shiryu.python()  # ty: ignore[unresolved-attribute]
        .documenter()()
        .document(project_directory=project_directory, platform=platform)
    )

    paths = await get_all_paths(directory)
    expected = (
        r"404\.html",
        r"assets/images/favicon\.png",
        r"assets/javascripts/LICENSE",
        r"assets/javascripts/bundle\.[a-f0-9]{8}\.min\.js",
        r"assets/javascripts/workers/search\.[a-f0-9]{8}\.min\.js",
        r"assets/stylesheets/classic/main\.[a-f0-9]{8}\.min\.css",
        r"assets/stylesheets/classic/palette\.[a-f0-9]{8}\.min\.css",
        r"assets/stylesheets/modern/main\.[a-f0-9]{8}\.min\.css",
        r"assets/stylesheets/modern/palette\.[a-f0-9]{8}\.min\.css",
        r"explanation/index\.html",
        r"how-to-guides/index\.html",
        r"index\.html",
        r"objects\.inv",
        r"reference/api-reference/index\.html",
        r"reference/index\.html",
        r"search\.json",
        r"sitemap\.xml",
        r"tutorials/index\.html",
    )

    for actual_path, pattern in zip(paths, expected, strict=True):
        assert re.fullmatch(pattern, actual_path), (
            f"Failed matching '{actual_path}' against '{pattern}'"
        )
