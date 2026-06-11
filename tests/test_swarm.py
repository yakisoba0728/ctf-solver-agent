"""Integration test for ChallengeSwarm with stub providers."""

import pytest

from ctf_solver.config import Settings
from ctf_solver.events import EventBus
from ctf_solver.solver.swarm import ChallengeSwarm


@pytest.mark.asyncio
async def test_swarm_status_without_docker(tmp_path):
    event_bus = EventBus()
    settings = Settings(
        claude_count=1,
        codex_count=1,
        zai_count=0,
        no_docker=True,
        no_tui=True,
        sandbox_image="alpine:latest",
    )
    swarm = ChallengeSwarm(
        challenge_dir=str(tmp_path),
        challenge_name="test-chall",
        description="test",
        category="misc",
        settings=settings,
        event_bus=event_bus,
    )
    status = swarm.get_status()
    assert status["challenge"] == "test-chall"
    assert status["cancelled"] is False


def test_swarm_kill():
    event_bus = EventBus()
    settings = Settings(claude_count=1)
    swarm = ChallengeSwarm(
        challenge_dir="/tmp",
        challenge_name="test",
        description="test",
        category="misc",
        settings=settings,
        event_bus=event_bus,
    )
    swarm.kill()
    assert swarm.cancel_event.is_set()
