"""conftest module."""

from collections.abc import AsyncGenerator

import dagger
import pytest_asyncio


@pytest_asyncio.fixture(scope="function")
async def dagger_session() -> AsyncGenerator[dagger.Session, None]:
    """Provides an active Dagger session connection for the duration of a test.

    Establishes a connection context with the background Dagger Engine and yields the connected
    session object, automatically closing the session after the test completes.

    Yields:
        dagger.Session: The active, connected Dagger session instance.
    """
    config = dagger.Config()
    async with dagger.connection(config) as session:
        yield session
