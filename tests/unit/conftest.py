"""conftest module."""

from collections.abc import AsyncGenerator, Callable
from typing import Any

import dagger
import jinja2
import pytest
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


@pytest.fixture
def render_template() -> Callable[[jinja2.Environment, str, dict[str, Any]], str]:
    """Provide a factory function to render Jinja templates.

    Returns:
        A callable function that renders a template.
    """

    def _render(
        environment: jinja2.Environment, template_name: str, context: dict[str, Any]
    ) -> str:
        """Render a template using the provided Jinja environment.

        Args:
            environment: The Jinja environment instance.
            template_name: The name of the template to render.
            context: Key-value variable mappings to inject into the template.

        Returns:
            The final rendered template string.
        """
        template: jinja2.Template = environment.get_template(template_name)
        return template.render(context)

    return _render
