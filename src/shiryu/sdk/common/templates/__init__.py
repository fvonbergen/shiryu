"""templates subpackage."""

from pathlib import Path

from ....utils.template import get_jinja_environment

COMMON_JINJA_ENVIRONMENT = get_jinja_environment(Path(__file__))
