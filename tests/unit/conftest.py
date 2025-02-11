"""conftest module."""

import sys

import dagger
import pytest_asyncio


@pytest_asyncio.fixture(scope="function")
async def dagger_client():
    """
    Provides an initialized Dagger client connection for the duration of a test.

    This fixture establishes a connection to the background Dagger Engine, initializes the global `dagger.dag` API client, and automatically handles resource cleanup after the test completes.

    Yields:
        dagger.Client: A live, connected Dagger client instance.
    """
    config = dagger.Config(log_output=sys.stderr)
    async with dagger.connection(config) as client:
        yield client
