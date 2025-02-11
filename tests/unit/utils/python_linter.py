"""python_linter module."""

from pathlib import Path
from typing import NamedTuple, final

from shiryu.sdk.common.module import PROJECT_NAME_DEFAULT, ProjectNameType
from shiryu.sdk.python.utils import get_package_name_canonical

from .common import DirectoryOutput, ignore_pytest


@final
class TestCaseLintFixInputFile(NamedTuple):
    """TestCaseLintFixInputFile class."""

    path: Path
    contents: str


def __get_source_file_path(project_name: ProjectNameType, file_name: str) -> Path:
    """
    Construct relative path to a source file within a shiryu project.

    Args:
        project_name: Project name.
        file_name: File name.

    Returns:
        The constructed project source file path.
    """
    package_name_canonical = get_package_name_canonical(project_name)
    return Path("src") / str(package_name_canonical) / file_name


def __build_test_case_lint_fix_input_file(
    project_name: ProjectNameType, file_name: str, contents: str
) -> TestCaseLintFixInputFile:
    """
    Helper to build input file for lint or fix calls test cases.

    Args:
        project_name: Project name.
        file_name: File name.
        contents: File contents.

    Returns:
        The input file for lint or fix calls test cases.
    """
    return TestCaseLintFixInputFile(
        path=__get_source_file_path(project_name, file_name), contents=contents
    )


@final
class TestCaseLintFixInputs(NamedTuple):
    """TestCaseLintFixInputs class."""

    file: TestCaseLintFixInputFile | None


@final
class StringOutput(NamedTuple):
    """StringOutput class."""

    expected_stdout: str


@final
@ignore_pytest
class TestCaseLint(NamedTuple):
    """TestCaseLint class."""

    name: str
    inputs: TestCaseLintFixInputs
    output: StringOutput


LINTER_SUCCESS_FILE_CONTENTS = '''"""linter_success_file module."""


def main() -> None:
    """Print a simple greeting."""
    print("Hello")
'''


def build_test_cases_linter_lint_success() -> tuple[TestCaseLint, ...]:
    """
    Builds the test cases used for testing linter lint successfull calls.

    Returns:
        The test cases.
    """
    project_name = PROJECT_NAME_DEFAULT
    stdout_successfull = "Lint successfull"

    return (
        TestCaseLint(
            name="empty_directory",
            inputs=TestCaseLintFixInputs(None),
            output=StringOutput(stdout_successfull),
        ),
        TestCaseLint(
            name="valid_file",
            inputs=TestCaseLintFixInputs(
                __build_test_case_lint_fix_input_file(
                    project_name, "lint_success.py", LINTER_SUCCESS_FILE_CONTENTS
                )
            ),
            output=StringOutput(stdout_successfull),
        ),
    )


def build_test_cases_linter_lint_failure() -> tuple[TestCaseLint, ...]:
    """
    Builds the test cases used for testing linter lint failure calls.

    Returns:
        The test cases.
    """
    project_name = PROJECT_NAME_DEFAULT

    return (
        TestCaseLint(
            name="invalid_file",
            inputs=TestCaseLintFixInputs(
                __build_test_case_lint_fix_input_file(
                    project_name, "lint_failure.py", ""
                )
            ),
            output=StringOutput(
                f"D100 Missing docstring in public module\n--> {__get_source_file_path(project_name, 'lint_failure.py')}:1:1\n\nFound 1 error."
            ),
        ),
    )


@final
@ignore_pytest
class TestCaseFixSuccess(NamedTuple):
    """TestCaseFixSuccess class."""

    name: str
    inputs: TestCaseLintFixInputs
    output: DirectoryOutput


def build_test_cases_linter_fix_success() -> tuple[TestCaseFixSuccess, ...]:
    """
    Builds the test cases used for testing linter fix successfull calls.

    Returns:
        The test cases.
    """
    project_name = PROJECT_NAME_DEFAULT

    return (
        TestCaseFixSuccess(
            name="empty_directory",
            inputs=TestCaseLintFixInputs(file=None),
            output=DirectoryOutput(paths=()),
        ),
        TestCaseFixSuccess(
            name="valid_file",
            inputs=TestCaseLintFixInputs(
                file=__build_test_case_lint_fix_input_file(
                    project_name, "fix_success.py", LINTER_SUCCESS_FILE_CONTENTS
                )
            ),
            output=DirectoryOutput(paths=()),
        ),
    )


@final
@ignore_pytest
class TestCaseFixFailure(NamedTuple):
    """TestCaseFixFailure class."""

    name: str
    inputs: TestCaseLintFixInputs
    output: StringOutput


def build_test_cases_linter_fix_failure() -> tuple[TestCaseFixFailure, ...]:
    """
    Builds the test cases used for testing linter fix failure calls.

    Returns:
        The test cases.
    """
    project_name = PROJECT_NAME_DEFAULT

    return (
        TestCaseFixFailure(
            name="invalid_file",
            inputs=TestCaseLintFixInputs(
                __build_test_case_lint_fix_input_file(
                    project_name, "fix_failure.py", ""
                )
            ),
            output=StringOutput(
                f"D100 Missing docstring in public module\n--> {__get_source_file_path(project_name, 'fix_failure.py')}:1:1\n\nFound 1 error."
            ),
        ),
    )
