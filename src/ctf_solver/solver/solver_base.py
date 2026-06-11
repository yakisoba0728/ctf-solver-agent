"""Solver protocol, result types, and state machine — shared across all backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol

from ctf_solver.providers.base import TokenUsage
from ctf_solver.sandbox.docker import SandboxProtocol


class ResultStatus(Enum):
    SOLVED = "solved"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    LOOP_DETECTED = "loop_detected"
    ERROR = "error"
    QUOTA_ERROR = "quota_error"


class SolverState(Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    SHARING = "sharing"
    COORDINATING = "coordinating"
    DONE = "done"


@dataclass
class SolverResult:
    solver_id: str
    status: ResultStatus
    flag: str | None
    steps: int
    duration: float
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    cost_usd: float = 0.0
    trace_path: Path = field(default_factory=Path)
    findings_summary: str = ""
    error: str | None = None


class SolverProtocol(Protocol):
    """Protocol for solver backends — uses structural subtyping for easy mocking."""

    model_spec: str
    sandbox: SandboxProtocol
    state: SolverState

    async def start(self) -> None:
        """Initialize sandbox and provider session. Must be called first."""
        ...

    async def run_until_done(self) -> SolverResult:
        """Run the tool-call loop until flag found, limit reached, or cancelled."""
        ...

    def inject_insights(self, insights: str) -> None:
        """Enqueue insights for injection into the next LLM turn. Callable anytime."""
        ...

    async def stop(self) -> None:
        """Cancel loop, close session, stop sandbox."""
        ...
