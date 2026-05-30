"""test_python_tester module."""

import re

import dagger
import pytest

from shiryu.main import Shiryu
from shiryu.sdk.common.module import SCM, ProjectNameType, SCMListType

from .utils.common import Paths, get_all_paths
from .utils.python_init import TestCaseInit, build_test_cases_init


def python_tester_init_paths(project_name: ProjectNameType, scm: SCMListType) -> Paths:
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
            (
                ".gitlab/jobs/.tester_unit.yml",
                ".gitlab/stages/quality.yml",
            )
            if SCM.GITLAB in scm
            else ()
        ),
        *(
            (
                ".github/actions/tester_unit/action.yml",
                ".github/workflows/quality.yml",
            )
            if SCM.GITHUB in scm
            else ()
        ),
        *(
            "pytest.unit.ini",
            "tests/unit/",
        ),
    )


TEST_CASES = build_test_cases_init((python_tester_init_paths,))


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda test_case: test_case.name)
async def test_python_tester_init(
    dagger_client: dagger.Client, test_case: TestCaseInit
) -> None:
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
    project_directory = dagger.dag.directory()
    platform = dagger.Platform("linux/amd64")

    stdout = (
        await Shiryu.python()  # type: ignore[attr-defined]
        .tester()()
        .unit(project_directory=project_directory, platform=platform)
    )
    # raise Exception(stdout)
    stdout_regex = re.compile(
        r"^============================= test session starts ==============================\n"
        r"platform linux -- Python (?P<python_major_version>\d+)\.\d+\.\d+, pytest-\d+\.\d+\.\d+, pluggy-\d+\.\d+\.\d+ -- /opt/.venv/bin/python(?P=python_major_version)\n"
        r"cachedir: \.pytest_cache\n"
        r"rootdir: /project\n"
        r"configfile: pytest\.unit\.ini\n"
        r"testpaths: tests/unit\n"
        r"plugins: xdist-\d+\.\d+\.\d+, asyncio-\d+\.\d+\.\d+, cov-\d+\.\d+\.\d+\n"
        r"asyncio: mode=Mode\.STRICT, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function\n"
        r"created: 2/2 workers\n"
        r"2 workers \[0 items\]\n"
        r"\n"
        r"scheduling tests via LoadScheduling\n"
        r"\n"
        r"================================ tests coverage ================================\n"
        r"_______________ coverage: platform linux, python (?P=python_major_version)\.\d+\.\d+-final-\d+ ________________\n"
        r"\n"
        r"Name                              Stmts   Miss  Cover   Missing\n"
        r"---------------------------------------------------------------\n"
        r"src/no_project_name/__init__\.py       0      0   100%\n"
        r"---------------------------------------------------------------\n"
        r"TOTAL                                 0      0   100%\n"
        r"Coverage XML written to file coverage\.xml\n"
        r"Required test coverage of 100\.0% reached\. Total coverage: 100\.00%\n"
        r"============================ no tests ran in \d+\.\d{2}s =============================\n$",
        re.DOTALL,
    )

    def find_stdout_mismatch(actual_stdout: str) -> str:
        # Your raw regex lines broken into a list
        regex_lines = [
            r"^============================= test session starts ==============================\n",
            r"platform linux -- Python (?P<python_major_version>\d+)\.\d+\.\d+, pytest-\d+\.\d+\.\d+, pluggy-\d+\.\d+\.\d+ -- /opt/.venv/bin/python(?P=python_major_version)\n",
            r"cachedir: \.pytest_cache\n",
            r"rootdir: /project\n",
            r"configfile: pytest\.unit\.ini\n",
            r"testpaths: tests/unit\n",
            r"plugins: xdist-\d+\.\d+\.\d+, asyncio-\d+\.\d+\.\d+, cov-\d+\.\d+\.\d+\n",
            r"asyncio: mode=Mode\.STRICT, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function\n",
            r"created: 2/2 workers\n",
            r"2 workers \[0 items\]\n",
            r"\n",
            r"scheduling tests via LoadScheduling\n",
            r"\n",
            r"================================ tests coverage ================================\n",
            # Swapped backreference (?P=python_major_version) to \d+ for the standalone line check
            r"_______________ coverage: platform linux, python \d+\.\d+\.\d+-final-\d+ ________________\n",
            r"\n",
            r"Name                              Stmts   Miss  Cover   Missing\n",
            r"---------------------------------------------------------------\n",
            r"src/no_project_name/__init__\.py      0      0   100%\n",
            r"---------------------------------------------------------------\n",
            r"TOTAL                                  0      0   100%\n",
            r"Coverage XML written to file coverage\.xml\n",
            r"Required test coverage of 100\.0% reached\. Total coverage: 100\.00%\n",
            r"============================ no tests ran in \d+\.\d{2}s =============================\n$",
        ]

        # Split the actual stdout into lines, preserving the \n characters at the end of each line
        actual_lines = actual_stdout.splitlines(keepends=True)

        for i, pattern_line in enumerate(regex_lines):
            # Case 1: Actual output ended earlier than expected
            if i >= len(actual_lines):
                return (
                    f"❌ MISMATCH: Regex expected more lines, but stdout ended early.\n"
                    f"Expected pattern line {i + 1}: {repr(pattern_line)}"
                )

            actual_line = actual_lines[i]
            compiled_line = re.compile(pattern_line, re.DOTALL)

            # Case 2: The current line doesn't match the regex pattern
            if not compiled_line.match(actual_line):
                return (
                    f"❌ MISMATCH FOUND AT LINE {i + 1}!\n"
                    f"--- Expected Pattern (Line {i + 1}) ---\n"
                    f"{repr(pattern_line)}\n"
                    f"--- Actual Value (Line {i + 1}) ---\n"
                    f"{repr(actual_line)}\n"
                    f"💡 Hint: Look for differences in spaces, version structures, or trailing newlines."
                )

        # Case 3: The regex finished matching all lines, but actual stdout has trailing text
        if len(actual_lines) > len(regex_lines):
            return (
                f"❌ MISMATCH: Your text has extra lines at the end that the regex doesn't account for.\n"
                f"First extra line: {repr(actual_lines[len(regex_lines)])}"
            )

        return "✅ Success! The stdout matches the regex perfectly."

    result = find_stdout_mismatch(stdout)
    raise Exception(result)
    assert stdout_regex.match(stdout)
