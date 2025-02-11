"""templates subpackage."""

from pathlib import Path
from typing import Final

from ....utils.template import get_jinja_environment

PYTHON_JINJA_ENVIRONMENT: Final = get_jinja_environment(Path(__file__))
