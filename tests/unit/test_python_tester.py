"""test_python_tester module."""

import re

import dagger
import pytest

from shiryu.main import Shiryu
from shiryu.sdk.common.module import PROJECT_NAME_DEFAULT, SCM, ProjectNameType, SCMType
from shiryu.utils.dagger.client import WORKDIR_PATH

from .utils.common import Paths, get_all_paths
from .utils.python_init import TestCaseInit, build_test_cases_init


def python_tester_init_paths(project_name: ProjectNameType, scm: SCMType) -> Paths:
    """
    Get python tester initializer paths.

    Args:
        project_name: Project name.
        scm: Project Source Code Management (SCM) list to be targeted or configured.

    Returns:
        The python tester initializer paths.
    """
    return (
        *(".coveragerc",),
        *(
            (".gitlab/jobs/.tester_unit.yml", ".gitlab/stages/quality.yml")
            if SCM.GITLAB in scm
            else ()
        ),
        *(
            (".github/actions/tester_unit/action.yml", ".github/workflows/quality.yml")
            if SCM.GITHUB in scm
            else ()
        ),
        *("pytest.unit.ini", "tests/unit/"),
    )


TEST_CASES = build_test_cases_init((python_tester_init_paths,))


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda test_case: test_case.name)
async def test_python_tester_init(dagger_client: dagger.Client, test_case: TestCaseInit) -> None:
    """
    Test python tester init function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
        test_case: A test case.
    """
    inputs = test_case.inputs

    directory = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .tester()()
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
async def test_python_tester_unit(dagger_client: dagger.Client) -> None:
    """
    Test python tester unit function module.

    Args:
        dagger_client: The active Dagger engine client injected by the `dagger_client` fixture.
    """
    project_name = PROJECT_NAME_DEFAULT
    project_directory = dagger.dag.directory()
    platform = dagger.Platform("linux/amd64")

    project_directory = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .tester()()
        .init(project_name=project_name, project_directory=project_directory, platform=platform)
    )
    stdout = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .tester()()
        .unit(project_directory=project_directory, platform=platform)
    )
    stdout_regex = re.compile(
        r"^============================= test session starts ==============================\n"
        r"platform linux -- Python (?P<python_major_version>\d+)\.\d+\.\d+, pytest-\d+\.\d+\.\d+, pluggy-\d+\.\d+\.\d+ -- /opt/.venv/bin/python(?P=python_major_version)\n"  # noqa: E501
        r"cachedir: \.pytest_cache\n"
        rf"rootdir: {WORKDIR_PATH}\n"
        r"configfile: pytest\.unit\.ini\n"
        r"testpaths: tests/unit\n"
        # r"plugins: asyncio-\d+\.\d+\.\d+, cov-\d+\.\d+\.\d+, xdist-\d+\.\d+\.\d+\n"
        r"plugins: .*\n"  # plugins order might vary between python versions.
        r"asyncio: mode=Mode\.STRICT, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function\n"  # noqa: E501
        r"created: (?P<worker>(?P<is_singular>1)|[2-9]|\d{2,})/(?P=worker) worker(?(is_singular)|s)\n"  # noqa: E501
        r"(?P=worker) worker(?(is_singular)|s) \[0 items\]\n"
        r"\n"
        r"scheduling tests via LoadScheduling\n"
        r"\n"
        r"================================ tests coverage ================================\n"
        r"_______________ coverage: platform linux, python (?P=python_major_version)\.\d+\.\d+-final-\d+ ________________\n"  # noqa: E501
        r"\n"
        r"Name                              Stmts   Miss  Cover   Missing\n"
        r"---------------------------------------------------------------\n"
        r"src/no_project_name/__init__\.py       0      0   100%\n"
        r"---------------------------------------------------------------\n"
        r"TOTAL                                 0      0   100%\n"
        r"Coverage XML written to file coverage\.xml\n"
        r"Required test coverage of 100\.0% reached\. Total coverage: 100\.00%\n"
        r"============================ no tests ran in \d+\.\d{2}s =============================\n$",  # noqa: E501
        re.DOTALL,
    )

    assert stdout_regex.match(stdout)
