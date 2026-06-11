"""CoordinatorAgent — reads solver traces, injects strategic guidance."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ctf_solver.collaboration.message_bus import ChallengeMessageBus
from ctf_solver.events import EventBus
from ctf_solver.providers import get_provider
from ctf_solver.providers.base import SolverSession
from ctf_solver.tracking.cost_tracker import CostTracker

if TYPE_CHECKING:
    from ctf_solver.config import Settings
    from ctf_solver.solver.swarm import ChallengeSwarm

logger = logging.getLogger(__name__)


@dataclass
class CoordinatorAgent:
    provider_name: str
    settings: Settings
    event_bus: EventBus
    cost_tracker: CostTracker
    message_bus: ChallengeMessageBus
    swarm: ChallengeSwarm | None = None
    session: SolverSession | None = None
    _task: asyncio.Task | None = None

    async def start(self) -> None:
        provider = get_provider(self.provider_name)
        config = {
            "anthropic_api_key": self.settings.anthropic_api_key,
            "openai_api_key": self.settings.openai_api_key,
            "zai_api_key": self.settings.zai_api_key,
            "zai_endpoint": self.settings.zai_endpoint,
        }
        if not provider.validate_config(config):
            logger.warning("Coordinator provider %s not configured — coordinator disabled", self.provider_name)
            return
        self.session = await provider.create_session(
            solver_id="coordinator",
            system_prompt="You are a CTF coordinator. Read solver traces and provide strategic guidance.",
            tools=[],
            config=config,
        )
        self._task = asyncio.create_task(self._coordination_loop())
        logger.info("Coordinator started with %s", self.provider_name)

    async def _coordination_loop(self) -> None:
        """Periodically read solver traces and inject guidance."""
        while True:
            await asyncio.sleep(30)
            if not self.swarm:
                continue
            status = self.swarm.get_status()
            for solver_id, info in status.get("solvers", {}).items():
                solver = self.swarm.solvers.get(solver_id)
                if not solver or not solver.tracer:
                    continue
                try:
                    trace_path = Path(solver.tracer.path)
                    if not trace_path.exists():
                        continue
                    lines = trace_path.read_text().strip().split("\n")
                    recent = lines[-10:]
                    summary = self._summarize_trace(recent)
                    await self.message_bus.broadcast("coordinator", f"Guidance for {solver_id}: {summary[:500]}")
                except Exception as e:
                    logger.warning("Coordinator trace read error: %s", e)

    def _summarize_trace(self, lines: list[str]) -> str:
        parts = []
        for line in lines:
            try:
                d = json.loads(line)
                t = d.get("type", "?")
                if t == "tool_call":
                    parts.append(f"Step {d.get('step', '?')}: called {d.get('tool', '?')}")
                elif t == "tool_result":
                    parts.append(f"Step {d.get('step', '?')}: got result from {d.get('tool', '?')}")
                elif t in ("finish", "error", "bump"):
                    parts.append(f"{t}: {str(d)[:100]}")
            except (json.JSONDecodeError, Exception):
                parts.append(line[:80])
        return "\n".join(parts) if parts else "No recent activity."

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        if self.session:
            await self.session.close()
        logger.info("Coordinator stopped")
