"""test_module_version module."""

import pytest

from shiryu.main import Shiryu


@pytest.mark.asyncio
async def test_module_version():
    """Test module_version."""
    entries = await Shiryu().get_module_version()
    assert entries == "debug-dagger-module-testing-inside-pytest"
