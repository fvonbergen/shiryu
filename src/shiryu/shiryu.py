"""shiryu module."""

import logging
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)

SHIRYU_PACKAGE_PATH: Final = Path(__file__).parent
SHIRYU_PACKAGE_NAME: Final = SHIRYU_PACKAGE_PATH.stem
