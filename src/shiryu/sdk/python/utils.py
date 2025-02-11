"""utils module."""

import re

from packaging.utils import canonicalize_name

from ...sdk.common.module import ProjectNameType

_PACKAGE_SANITIZER_PATTERN = re.compile(r"[-_.]+")


def get_package_name_canonical(project_name: ProjectNameType) -> str:
    """
    Converts a PyPI project distribution name into its canonical local package folder and import name.

    This function bridges the gap between two different Python packaging standards:
    1. PEP 503/508 distribution naming (which normalizes names using dashes).
    2. PEP 8/Python syntax rules (which require underscores for local imports/folders).

    Args:
        project_name: The raw project name as defined in a configuration file like `pyproject.toml` (e.g., "No-Project-Name" or "My.Awesome.App").

    Returns:
        A sanitized, lowercase string safe to use as a Python package directory or import statement (e.g., "no_project_name" or "my_awesome_app").
    """
    # Canonicalize per PEP 503 (lowercases and forces standard dash formatting)
    dist_name_canonical = canonicalize_name(project_name)
    # Convert dashes and periods to underscores to satisfy Python import syntax
    return _PACKAGE_SANITIZER_PATTERN.sub("_", dist_name_canonical)
