"""Tests for provider stubs."""

import pytest

from ctf_solver.providers import get_provider
from ctf_solver.providers.claude import ClaudeProvider
from ctf_solver.providers.codex import CodexProvider
from ctf_solver.providers.zai import ZAIProvider


def test_get_provider_claude():
    p = get_provider("claude")
    assert isinstance(p, ClaudeProvider)
    assert p.name == "claude"


def test_get_provider_codex():
    p = get_provider("codex")
    assert isinstance(p, CodexProvider)


def test_get_provider_zai():
    p = get_provider("zai")
    assert isinstance(p, ZAIProvider)


def test_get_provider_unknown():
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nonexistent")


def test_claude_validate_no_key():
    p = ClaudeProvider()
    assert p.validate_config({"anthropic_api_key": ""}) is False


def test_codex_validate_no_key():
    p = CodexProvider()
    assert p.validate_config({"openai_api_key": ""}) is False


def test_zai_validate_no_key():
    p = ZAIProvider()
    assert p.validate_config({"zai_api_key": ""}) is False


def test_codex_validate_with_key():
    p = CodexProvider()
    assert p.validate_config({"openai_api_key": "sk-test"}) is True


@pytest.mark.asyncio
async def test_claude_create_session_raises():
    p = ClaudeProvider()
    with pytest.raises(NotImplementedError):
        await p.create_session("test", "", [], {})


@pytest.mark.asyncio
async def test_codex_create_session_raises():
    p = CodexProvider()
    with pytest.raises(NotImplementedError):
        await p.create_session("test", "", [], {})


@pytest.mark.asyncio
async def test_zai_create_session_raises():
    p = ZAIProvider()
    with pytest.raises(NotImplementedError):
        await p.create_session("test", "", [], {})
