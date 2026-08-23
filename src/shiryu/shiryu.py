"""shiryu module."""

import logging

# from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Final

# from setuptools_scm import get_version

logger = logging.getLogger(__name__)

SHIRYU_PACKAGE_PATH: Final = Path(__file__).parent
SHIRYU_PACKAGE_NAME: Final = SHIRYU_PACKAGE_PATH.stem


# TODO: remove?
# def __package_get_version() -> str:
#     """Get package version from importlib metadata or a fixed string if package is not installed.
#
#     Returns:
#         Package version.
#     """
#     # """Get package version from importlib metadata, then a fallback method, finally a fixed string.
#
#     # Returns:
#     #    Package version.
#     # """
#
#     def __package_get_version_fallback() -> str:
#         """Get package version with fallback method.
#
#         Returns:
#             Package version.
#         """
#         # try:
#         #     _version = get_version(SHIRYU_PACKAGE_PATH)
#         #     logger.info(f"Falling back to setuptools-scm.")
#         # except LookupError:
#         #     # package without git
#         #     logger.info(
#         #         f"Package {SHIRYU_PACKAGE_NAME} not installed. Falling back to unknown version."
#         #     )
#         #     _version = "0.0.0+unknown"
#         # return _version
#         return "0.0.0+unknown"
#
#     try:
#         _version = version(SHIRYU_PACKAGE_NAME)
#     except PackageNotFoundError:
#         # package is not installed
#         logger.info(f"Package {SHIRYU_PACKAGE_NAME} not installed.")
#         _version = __package_get_version_fallback()
#     return _version
#
#
# SHIRYU_VERSION: Final = __package_get_version()
