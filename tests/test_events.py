"""Tests for event system."""

import asyncio

import pytest


@pytest.mark.asyncio
async def test_publish_and_subscribe():
    from ctf_solver.events import EventBus, SolverEvent

    bus = EventBus()
    queue = bus.subscribe()
    event = SolverEvent(type="solver_started", solver_id="claude-0", data={"model": "opus"})
    bus.publish(event)
    received = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert received.type == "solver_started"
    assert received.solver_id == "claude-0"


@pytest.mark.asyncio
async def test_multiple_subscribers():
    from ctf_solver.events import EventBus, SolverEvent

    bus = EventBus()
    q1 = bus.subscribe()
    q2 = bus.subscribe()
    event = SolverEvent(type="tool_call", solver_id="codex-0", data={"tool": "bash"})
    bus.publish(event)
    r1 = await asyncio.wait_for(q1.get(), timeout=1.0)
    r2 = await asyncio.wait_for(q2.get(), timeout=1.0)
    assert r1.type == r2.type == "tool_call"


@pytest.mark.asyncio
async def test_publish_and_wait_yields():
    from ctf_solver.events import EventBus, SolverEvent

    bus = EventBus()
    queue = bus.subscribe()
    event = SolverEvent(type="solver_done", solver_id="zai-0", data={})
    await bus.publish_and_wait(event)
    received = queue.get_nowait()
    assert received.type == "solver_done"
