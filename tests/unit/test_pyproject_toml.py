"""test_pyproject_toml module."""

from shiryu.sdk.common.module import ProjectAuthor
from shiryu.sdk.python.context import DependencyGroups
from shiryu.sdk.python.templates import PYTHON_JINJA_ENVIRONMENT


def test_pyproject_toml(render_template) -> None:
    """Test pyproject.toml."""
    # Test pyproject.toml with multiple authors
    project_name = "no-project-name"
    project_version = "0.1.0"
    readme_file_name = "README.md"

    # Unsorted input to explicitly verify your Jinja |sort filter works
    authors = frozenset(
        {
            ProjectAuthor("name_2", "name_2@mail.com"),
            ProjectAuthor("name_1", "name_1@mail.com"),
        }
    )
    dependency_groups = DependencyGroups()

    context = {
        "project_name": project_name,
        "project_version": project_version,
        "readme_file_name": readme_file_name,
        "project_authors": authors,
        "dependency_groups": dependency_groups,
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
authors = [
{authors_block}
]
# linked to [tool.uv] environments
# python3.6
# - uv minium python support - https://docs.astral.sh/uv/reference/policies/python/#python-versions
# python3.7
# - pytest >= 7.1.0 (tester) - https://docs.pytest.org/en/stable/changelog.html#pytest-7-1-0-2022-03-13
# python3.8
# - uv >= 0.7 (auditor) - https://github.com/astral-sh/uv/blob/main/changelogs/0.7.x.md
# - ty minimum python support - (checker) - https://github.com/astral-sh/ty/blob/0.0.2/pyproject.toml#L4
# python3.9
# - commit-check >= 2.0.0 (linter) - https://github.com/commit-check/commit-check/blob/v2.0.0/pyproject.toml#L14
# python3.10
# - zensical minimum python support - (documenter) - https://github.com/zensical/zensical/blob/v0.0.3/pyproject.toml#L36
requires-python = ">=3.10"
dependencies = []

# Dependencies that will be installed for the specific module call.
[dependency-groups]

[project.urls]
# "Homepage" = ""
# "Documentation" = ""
# "Repository" = ""
# "Issues" = ""
# "Changelog" = ""
# "Release Notes" = ""
# "Community" = ""
# "Twitter" = ""

[build-system]
requires = ["hatchling==1.31.0"]
build-backend = "hatchling.build"

[tool.uv]
# linked to [project] requires-python
environments = [
  "python_version == '3.10'",
  "python_version == '3.11'",
  "python_version == '3.12'",
  "python_version == '3.13'",
  "python_version == '3.14'",
  "python_version == '3.15'",
]"""

    assert rendered.strip() == expected_output.strip()
