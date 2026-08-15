"""test_python_documenter module."""

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
    assert await get_all_paths(directory) == (
        "404.html",
        "assets/images/favicon.png",
        "assets/javascripts/LICENSE",
        "assets/javascripts/bundle.e886cdf1.min.js",
        "assets/javascripts/workers/search.7d14d953.min.js",
        "assets/stylesheets/classic/main.39e53929.min.css",
        "assets/stylesheets/classic/palette.7dc9a0ad.min.css",
        "assets/stylesheets/modern/main.20815dad.min.css",
        "assets/stylesheets/modern/palette.dfe2e883.min.css",
        "explanation/index.html",
        "how-to-guides/index.html",
        "index.html",
        "objects.inv",
        "reference/api-reference/index.html",
        "reference/index.html",
        "search.json",
        "sitemap.xml",
        "tutorials/index.html",
    )
