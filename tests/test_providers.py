"""Tests for providers."""

import pytest

from ctf_solver.providers import get_provider
from ctf_solver.providers.base import SolverSession
from ctf_solver.providers.claude import ClaudeProvider, ClaudeSession
from ctf_solver.providers.codex import CodexProvider, CodexSession
from ctf_solver.providers.zai import ZAIProvider, ZAISession


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
async def test_claude_create_session():
    p = ClaudeProvider()
    session = await p.create_session("test", "system", [], {"anthropic_api_key": "sk-test"})
    assert isinstance(session, ClaudeSession)
    assert isinstance(session, SolverSession)
    await session.close()


@pytest.mark.asyncio
async def test_codex_create_session():
    p = CodexProvider()
    session = await p.create_session("test", "system", [], {"openai_api_key": "sk-test"})
    assert isinstance(session, CodexSession)
    assert isinstance(session, SolverSession)
    await session.close()


@pytest.mark.asyncio
async def test_zai_create_session():
    p = ZAIProvider()
    session = await p.create_session("test", "system", [], {"zai_api_key": "sk-test"})
    assert isinstance(session, ZAISession)
    assert isinstance(session, SolverSession)
    await session.close()


@pytest.mark.asyncio
async def test_claude_validate_with_key():
    p = ClaudeProvider()
    assert p.validate_config({"anthropic_api_key": "sk-test"}) is True


@pytest.mark.asyncio
async def test_zai_validate_with_key():
    p = ZAIProvider()
    assert p.validate_config({"zai_api_key": "sk-test"}) is True
