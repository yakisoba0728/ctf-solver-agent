"""Tests for vision tool."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ctf_solver.tools.vision import do_view_image


@pytest.mark.asyncio
async def test_unsupported_ext():
    result = await do_view_image(MagicMock(), "file.xyz")
    assert "Not a supported" in result


@pytest.mark.asyncio
async def test_no_vision():
    result = await do_view_image(MagicMock(), "test.png", use_vision=False)
    assert "Vision not available" in result


@pytest.mark.asyncio
async def test_file_not_found():
    sandbox = MagicMock()
    sandbox.read_file_bytes = AsyncMock(side_effect=FileNotFoundError)
    result = await do_view_image(sandbox, "missing.png")
    assert "not found" in result.lower() or "File not found" in result
