"""Tests for message bus."""

import pytest

from ctf_solver.collaboration.message_bus import ChallengeMessageBus, InsightMessage


@pytest.mark.asyncio
async def test_post_and_check():
    bus = ChallengeMessageBus()
    await bus.post(InsightMessage(solver_id="claude-0", step=5, category="finding", content="found buffer overflow", confidence=0.8))
    findings = await bus.check("codex-0")
    assert len(findings) == 1
    assert findings[0].content == "found buffer overflow"


@pytest.mark.asyncio
async def test_no_self_insights():
    bus = ChallengeMessageBus()
    await bus.post(InsightMessage(solver_id="claude-0", step=5, category="finding", content="test", confidence=0.5))
    findings = await bus.check("claude-0")
    assert len(findings) == 0


@pytest.mark.asyncio
async def test_cursor_advances():
    bus = ChallengeMessageBus()
    await bus.post(InsightMessage(solver_id="a", step=1, category="finding", content="first", confidence=0.5))
    await bus.check("b")
    await bus.post(InsightMessage(solver_id="a", step=2, category="finding", content="second", confidence=0.5))
    findings = await bus.check("b")
    assert len(findings) == 1
    assert findings[0].content == "second"


@pytest.mark.asyncio
async def test_broadcast():
    bus = ChallengeMessageBus()
    await bus.broadcast("coordinator", "check HTTP headers")
    findings_a = await bus.check("a")
    findings_b = await bus.check("b")
    assert len(findings_a) == 1
    assert len(findings_b) == 1
