"""Async event bus for solver state changes — decouples TUI/CLI from solver logic."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)

MAX_EVENT_QUEUE = 1000


@dataclass
class SolverEvent:
    type: Literal[
        "solver_started",
        "tool_call",
        "tool_result",
        "insight_shared",
        "insight_received",
        "coordinator_guidance",
        "flag_found",
        "flag_candidate",
        "solver_error",
        "solver_done",
        "cost_update",
        "user_hint",
        "state_change",
    ]
    solver_id: str
    data: dict[str, Any]


@dataclass
class EventBus:
    """Async pub/sub — both TUI and CLI subscribe to the same stream."""

    _subscribers: list[asyncio.Queue[SolverEvent]] = field(default_factory=list)

    def subscribe(self) -> asyncio.Queue[SolverEvent]:
        q: asyncio.Queue[SolverEvent] = asyncio.Queue(maxsize=MAX_EVENT_QUEUE)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[SolverEvent]) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def publish(self, event: SolverEvent) -> None:
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Event queue full, dropping event: %s", event.type)

    async def publish_and_wait(self, event: SolverEvent) -> None:
        self.publish(event)
        await asyncio.sleep(0)
