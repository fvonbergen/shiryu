"""python_linter module."""

from pathlib import PurePosixPath
from typing import NamedTuple, final

from shiryu.sdk.common.module import PROJECT_NAME_DEFAULT, ProjectNameType
from shiryu.sdk.python.utils import get_package_name_canonical

from .common import DirectoryOutput, ignore_pytest


@final
class TestCaseLintFixCodeInputFile(NamedTuple):
    """TestCaseLintFixCodeInputFile class."""

    path: PurePosixPath
    contents: str


def __get_source_file_path(project_name: ProjectNameType, file_name: str) -> PurePosixPath:
    """Construct relative path to a source file within a shiryu project.

    Args:
        project_name: Project name.
        file_name: File name.

    Returns:
        The constructed project source file path.
    """
    package_name_canonical = get_package_name_canonical(project_name)
    return PurePosixPath("src") / str(package_name_canonical) / file_name


def __build_test_case_lint_fix_code_input_file(
    project_name: ProjectNameType, file_name: str, contents: str
) -> TestCaseLintFixCodeInputFile:
    """Helper to build input file for lint or fix code calls test cases.

    Args:
        project_name: Project name.
        file_name: File name.
        contents: File contents.

    Returns:
        The input file for lint or fix code calls test cases.
    """
    return TestCaseLintFixCodeInputFile(
        path=__get_source_file_path(project_name, file_name), contents=contents
    )


@final
class TestCaseLintFixCodeInputs(NamedTuple):
    """TestCaseLintFixCodeInputs class."""

    file: TestCaseLintFixCodeInputFile | None


@final
class StringOutput(NamedTuple):
    """StringOutput class."""

    expected_stdout: str


@final
@ignore_pytest
class TestCaseLintCode(NamedTuple):
    """TestCaseLintCode class."""

    name: str
    inputs: TestCaseLintFixCodeInputs
    output: StringOutput


LINTER_LINT_CODE_SUCCESS_FILE_CONTENTS = '''"""linter_lint_code_success_file module."""


def main() -> None:
    """Print a simple greeting."""
    print("Hello")
'''


def build_test_cases_linter_lint_code_success() -> tuple[TestCaseLintCode, ...]:
    """Builds the test cases used for testing linter lint_code successfull calls.

    Returns:
        The test cases.
    """
    project_name = PROJECT_NAME_DEFAULT
    stdout_successfull = "Lint code successfull"

    return (
        TestCaseLintCode(
            name="empty_directory",
            inputs=TestCaseLintFixCodeInputs(None),
            output=StringOutput(stdout_successfull),
        ),
        TestCaseLintCode(
            name="valid_file",
            inputs=TestCaseLintFixCodeInputs(
                __build_test_case_lint_fix_code_input_file(
                    project_name, "lint_success.py", LINTER_LINT_CODE_SUCCESS_FILE_CONTENTS
                )
            ),
            output=StringOutput(stdout_successfull),
        ),
    )


def build_test_cases_linter_lint_code_failure() -> tuple[TestCaseLintCode, ...]:
    """Builds the test cases used for testing linter lint_code failure calls.

    Returns:
        The test cases.
    """
    project_name = PROJECT_NAME_DEFAULT
    source_file_path = __get_source_file_path(project_name, "lint_code_failure.py")
    return (
        TestCaseLintCode(
            name="invalid_file",
            inputs=TestCaseLintFixCodeInputs(
                __build_test_case_lint_fix_code_input_file(project_name, "lint_code_failure.py", "")
            ),
            output=StringOutput(
                f"D100 Missing docstring in public module\n--> {source_file_path}:1:1\n\nFound 1 "
                "error."
            ),
        ),
    )


@final
@ignore_pytest
class TestCaseFixCodeSuccess(NamedTuple):
    """TestCaseFixCodeSuccess class."""

    name: str
    inputs: TestCaseLintFixCodeInputs
    output: DirectoryOutput


def build_test_cases_linter_fix_code_success() -> tuple[TestCaseFixCodeSuccess, ...]:
    """Builds the test cases used for testing linter fix code successfull calls.

    Returns:
        The test cases.
    """
    project_name = PROJECT_NAME_DEFAULT

    return (
        TestCaseFixCodeSuccess(
            name="empty_directory",
            inputs=TestCaseLintFixCodeInputs(file=None),
            output=DirectoryOutput(paths=()),
        ),
        TestCaseFixCodeSuccess(
            name="valid_file",
            inputs=TestCaseLintFixCodeInputs(
                file=__build_test_case_lint_fix_code_input_file(
                    project_name, "fix_success.py", LINTER_LINT_CODE_SUCCESS_FILE_CONTENTS
                )
            ),
            output=DirectoryOutput(paths=()),
        ),
        TestCaseFixCodeSuccess(
            name="invalid_file",
            inputs=TestCaseLintFixCodeInputs(
                file=__build_test_case_lint_fix_code_input_file(
                    project_name, "fix_code_failure.py", ""
                )
            ),
            output=DirectoryOutput(paths=()),
        ),
    )
