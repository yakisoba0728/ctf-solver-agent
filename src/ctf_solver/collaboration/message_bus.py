"""Per-challenge message bus for inter-solver insight sharing."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class InsightMessage:
    solver_id: str
    step: int
    category: Literal["technique", "finding", "dead_end", "flag_candidate"]
    content: str
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)


MAX_FINDINGS = 200


@dataclass
class ChallengeMessageBus:
    """Append-only shared findings with per-model cursors."""

    findings: list[InsightMessage] = field(default_factory=list)
    cursors: dict[str, int] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def post(self, message: InsightMessage) -> None:
        async with self._lock:
            self.findings.append(message)
            if len(self.findings) > MAX_FINDINGS:
                trim = len(self.findings) - MAX_FINDINGS
                self.findings = self.findings[trim:]
                self.cursors = {k: max(0, v - trim) for k, v in self.cursors.items()}

    async def check(self, model: str) -> list[InsightMessage]:
        async with self._lock:
            cursor = self.cursors.get(model, 0)
            unread = [f for f in self.findings[cursor:] if f.solver_id != model]
            self.cursors[model] = len(self.findings)
            return unread

    async def broadcast(self, source: str, content: str) -> None:
        await self.post(InsightMessage(solver_id=source, step=0, category="finding", content=content, confidence=1.0))

    def format_unread(self, findings: list[InsightMessage]) -> str:
        if not findings:
            return ""
        parts = [f"[{f.solver_id}] ({f.category}) {f.content}" for f in findings]
        return "**Findings from other agents:**\n\n" + "\n\n".join(parts)
