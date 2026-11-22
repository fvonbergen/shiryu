"""test_pyproject_toml module."""

from packaging.version import Version

from shiryu.sdk.common.module import ProjectAuthor
from shiryu.sdk.python.context import DependencyGroups
from shiryu.sdk.python.templates import PYTHON_JINJA_ENVIRONMENT


def test_pyproject_toml(render_template) -> None:
    """Test pyproject.toml."""
    # Test pyproject.toml with multiple authors
    project_name = "no-project-name"
    project_version = "0.1.0"
    readme_file_name = "README.md"
    license_ = "Apache-2.0"
    license_file_name = "LICENSE"
    lower_bound_requires_python = Version("3.10")
    hatchling_version = Version("1.33.0")

    # Unsorted input to explicitly verify your Jinja |sort filter works
    authors = frozenset(
        {
            ProjectAuthor(name="name_2", email="name_2@mail.com"),
            ProjectAuthor(name="name_1", email="name_1@mail.com"),
        }
    )
    dependency_groups = DependencyGroups()

    context = {
        "project_name": project_name,
        "project_authors": authors,
        "project_version": project_version,
        "readme_file_name": readme_file_name,
        "license": license_,
        "license_file_name": license_file_name,
        "requires_python": lower_bound_requires_python,
        "python_versions": frozenset(
            {
                lower_bound_requires_python,
                Version("3.11"),
                Version("3.12"),
                Version("3.13"),
                Version("3.14"),
                Version("3.15"),
            }
        ),
        "dependency_groups_specifiers": dependency_groups.specifiers,
        "hatchling_version": str(hatchling_version),
    }

    # Render directly by name from your pre-configured environment
    rendered = render_template(
        environment=PYTHON_JINJA_ENVIRONMENT, template_name="pyproject.toml.jinja2", context=context
    )

    # Generate the string representation for the authors block dynamically
    authors_block = "\n".join(
        f'  {{ name = "{a.name}", email = "{a.email}" }},'
        for a in sorted(authors, key=lambda author: author.name)
    )

    expected_output = f"""[project]
name = "{project_name}"
version = "{project_version}"
description = ""
readme = "{readme_file_name}"
license = "{license_}"
license-files = ["{license_file_name}"]
authors = [
{authors_block}
]
maintainers = [
{authors_block}
]
keywords = []
requires-python = ">=3.10"
# NOTE: Keep these aligned with [project].requires-python; update if minimum Python changes.
classifiers = [
  "Operating System :: OS Independent",
  "Programming Language :: Python",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Programming Language :: Python :: 3.14",
  "Programming Language :: Python :: 3.15",
  "Typing :: Typed",
]
dependencies = []

[project.urls]
# Homepage = ""
# Documentation = ""
# Repository = ""
# Issues = ""
# Changelog = ""
# Release Notes = ""
# Community = ""

# Dependencies that will be installed for the specific module call.
[dependency-groups]

[build-system]
requires = ["hatchling=={hatchling_version}"]
build-backend = "hatchling.build\""""

    assert rendered.strip() == expected_output.strip()
