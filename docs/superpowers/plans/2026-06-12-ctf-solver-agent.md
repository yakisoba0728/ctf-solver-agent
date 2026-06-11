# CTF Solver Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-subagent-driven-development (recommended) or superpowers-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-model CTF solver agent with Docker sandboxing, inter-model collaboration, TUI dashboard, and pluggable AI providers.

**Architecture:** Provider-abstraction layer with Protocol/ABC interfaces. Each solver gets an isolated Docker container. ChallengeSwarm runs multiple solvers in parallel with message bus collaboration. CoordinatorAgent provides strategic guidance. Textual TUI as default interface, `--no-tui` for CI.

**Tech Stack:** Python 3.12+, asyncio, Click, Textual, Rich, Pydantic, aiodocker, httpx, PyYAML

**Spec:** `docs/superpowers/specs/2026-06-12-ctf-solver-agent-design.md`

---

## File Structure

```
src/ctf_solver/
├── __init__.py                    # package init, version
├── cli.py                         # Click CLI (ctf-solve, ctf-msg)
├── config.py                      # Pydantic Settings
├── events.py                      # SolverEvent + EventBus
├── prompts.py                     # system prompt builder
├── tracing.py                     # SolverTracer (JSONL)
├── writeup.py                     # solve-detail.md + solve-brief.md generation
│
├── providers/
│   ├── __init__.py                # provider registry
│   ├── base.py                    # ProviderProtocol, SolverSession, data models
│   ├── claude.py                  # ClaudeProvider stub
│   ├── codex.py                   # CodexProvider stub
│   └── zai.py                     # ZAIProvider stub
│
├── solver/
│   ├── __init__.py
│   ├── solver_base.py             # SolverProtocol, SolverResult, ResultStatus, SolverState
│   ├── swarm.py                   # ChallengeSwarm
│   └── coordinator.py             # CoordinatorAgent
│
├── sandbox/
│   ├── __init__.py
│   └── docker.py                  # SandboxProtocol + DockerSandbox
│
├── tools/
│   ├── __init__.py
│   ├── core.py                    # bash, read/write, web_fetch, webhook, list_files
│   ├── vision.py                  # view_image
│   └── flag.py                    # flag pattern matching
│
├── collaboration/
│   ├── __init__.py
│   ├── message_bus.py             # InsightMessage + ChallengeMessageBus
│   └── loop_detect.py             # LoopDetector
│
├── tracking/
│   ├── __init__.py
│   ├── cost_tracker.py            # CostTracker + AgentUsage
│   └── circuit_breaker.py         # CircuitBreaker
│
└── tui/
    ├── __init__.py
    ├── app.py                     # CTFApp (Textual App)
    ├── screens/
    │   ├── __init__.py
    │   ├── main.py                # MainDashboard
    │   └── logs.py                # LogsScreen
    └── widgets/
        ├── __init__.py
        ├── solver_panel.py        # SolverPanel
        ├── message_log.py         # MessageLog
        ├── cost_bar.py            # CostBar
        ├── coordinator_view.py    # CoordinatorView
        └── input_bar.py           # HintInputBar

tests/
├── test_events.py
├── test_config.py
├── test_loop_detect.py
├── test_message_bus.py
├── test_cost_tracker.py
├── test_circuit_breaker.py
├── test_flag_pattern.py
├── test_sandbox.py
├── test_writeup.py
├── test_swarm.py
├── test_cli.py
└── test_tracing.py

sandbox/
├── Dockerfile
└── sandbox-tools.txt

pyproject.toml
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/ctf_solver/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "ctf-solver-agent"
version = "0.1.0"
description = "Multi-model CTF solver agent with Docker sandboxing and TUI dashboard"
requires-python = ">=3.12"
dependencies = [
    "click>=8.0",
    "rich>=13.0",
    "textual>=3.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "aiodocker>=0.24",
    "httpx>=0.27",
    "pyyaml>=6.0",
    "genai-prices>=0.1",
]

[project.scripts]
ctf-solve = "ctf_solver.cli:main"
ctf-msg = "ctf_solver.cli:send_message"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
package = true

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.8",
]

[tool.hatch.build.targets.wheel]
packages = ["src/ctf_solver"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "N", "C4", "PTH"]
ignore = ["E501", "SIM105", "SIM115", "PTH123"]

[tool.ruff.lint.isort]
known-first-party = ["ctf_solver"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create package init**

```python
"""CTF Solver Agent — multi-model CTF solver with Docker sandboxing."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create directory structure**

```bash
mkdir -p src/ctf_solver/{providers,solver,sandbox,tools,collaboration,tracking,tui/screens,tui/widgets}
mkdir -p tests sandbox challenges/example/distfiles
touch src/ctf_solver/{providers,solver,sandbox,tools,collaboration,tracking,tui,tui/screens,tui/widgets}/__init__.py
```

- [ ] **Step 4: Install dependencies**

```bash
cd /home/yakihyuk0728/ctf-solver-agent && uv sync
```

- [ ] **Step 5: Verify installation**

```bash
cd /home/yakihyuk0728/ctf-solver-agent && uv run python -c "import ctf_solver; print(ctf_solver.__version__)"
```
Expected: `0.1.0`

- [ ] **Step 6: Commit**

```bash
git init && git add -A && git commit -m "chore: project scaffolding with pyproject.toml and directory structure"
```

---

## Task 2: Config Module

**Files:**
- Create: `src/ctf_solver/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for config module."""

import pytest


def test_default_settings():
    from ctf_solver.config import Settings

    s = Settings()
    assert s.sandbox_image == "ctf-sandbox"
    assert s.sandbox_memory == "4g"
    assert s.sandbox_cpus == 2
    assert s.timeout == 600
    assert s.max_steps == 100
    assert s.max_cost == 10.0
    assert s.flag_pattern == r"([Ff][Ll][Aa][Gg]|[Cc][Tt][Ff])\{[^}]+\}"


def test_settings_from_env(monkeypatch):
    from ctf_solver.config import Settings

    monkeypatch.setenv("SANDBOX_IMAGE", "my-sandbox")
    monkeypatch.setenv("TIMEOUT", "300")
    monkeypatch.setenv("MAX_COST", "5.0")
    s = Settings()
    assert s.sandbox_image == "my-sandbox"
    assert s.timeout == 300
    assert s.max_cost == 5.0


def test_provider_counts_default():
    from ctf_solver.config import Settings

    s = Settings()
    assert s.claude_count == 0
    assert s.codex_count == 0
    assert s.zai_count == 0


def test_no_providers_raises():
    from ctf_solver.config import Settings, validate_provider_config

    s = Settings()
    with pytest.raises(ValueError, match="at least one provider"):
        validate_provider_config(s)


def test_coordinator_default_is_first_provider():
    from ctf_solver.config import Settings, get_coordinator_provider

    s = Settings(claude_count=0, codex_count=2, zai_count=1)
    assert get_coordinator_provider(s) == "codex"


def test_coordinator_zero_count_excluded():
    from ctf_solver.config import Settings, get_coordinator_provider

    s = Settings(claude_count=0, codex_count=3)
    assert get_coordinator_provider(s) == "codex"


def test_coordinator_explicit_overrides():
    from ctf_solver.config import Settings, get_coordinator_provider

    s = Settings(claude_count=2, codex_count=2, coordinator="codex")
    assert get_coordinator_provider(s) == "codex"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_config.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

```python
"""Pydantic Settings — credentials and configuration from .env + env vars + CLI."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    zai_api_key: str = ""
    zai_endpoint: str = "https://api.z.ai/v1"

    # Provider counts (set via CLI, not env)
    claude_count: int = 0
    codex_count: int = 0
    zai_count: int = 0
    coordinator: str = ""
    no_coordinator: bool = False

    # Sandbox
    sandbox_image: str = "ctf-sandbox"
    sandbox_memory: str = "4g"
    sandbox_cpus: int = 2
    no_docker: bool = False

    # Limits
    timeout: int = 600
    max_steps: int = 100
    max_cost: float = 10.0
    flag_pattern: str = r"([Ff][Ll][Aa][Gg]|[Cc][Tt][Ff])\{[^}]+\}"

    # Hints
    hint: str = ""
    interactive: bool = False

    # Output
    output_dir: str = ""
    log_dir: str = ""
    port: int = 0

    # Modes
    no_tui: bool = False
    dry_run: bool = False
    verbose: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def validate_provider_config(settings: Settings) -> None:
    """Validate that at least one provider has a positive count."""
    if settings.claude_count + settings.codex_count + settings.zai_count <= 0:
        msg = "Specify at least one provider (--claude N, --codex N, or --zai N)"
        raise ValueError(msg)


def get_active_providers(settings: Settings) -> list[tuple[str, int]]:
    """Return list of (provider_name, count) for providers with positive count."""
    result = []
    if settings.claude_count > 0:
        result.append(("claude", settings.claude_count))
    if settings.codex_count > 0:
        result.append(("codex", settings.codex_count))
    if settings.zai_count > 0:
        result.append(("zai", settings.zai_count))
    return result


def get_coordinator_provider(settings: Settings) -> str | None:
    """Get the coordinator provider name, or None if --no-coordinator."""
    if settings.no_coordinator:
        return None
    if settings.coordinator:
        active = {name for name, _ in get_active_providers(settings)}
        if settings.coordinator not in active:
            msg = f"Coordinator '{settings.coordinator}' has no active solvers. Active: {active}"
            raise ValueError(msg)
        return settings.coordinator
    providers = get_active_providers(settings)
    return providers[0][0] if providers else None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_config.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add config module with Pydantic Settings"
```

---

## Task 3: Event System

**Files:**
- Create: `src/ctf_solver/events.py`
- Test: `tests/test_events.py`

- [ ] **Step 1: Write failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_events.py -v
```

- [ ] **Step 3: Write implementation**

```python
"""Async event bus for solver state changes — decouples TUI/CLI from solver logic."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Literal


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
        q: asyncio.Queue[SolverEvent] = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def publish(self, event: SolverEvent) -> None:
        for q in self._subscribers:
            q.put_nowait(event)

    async def publish_and_wait(self, event: SolverEvent) -> None:
        self.publish(event)
        await asyncio.sleep(0)
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/test_events.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add EventBus with async pub/sub"
```

---

## Task 4: Loop Detector

**Files:**
- Create: `src/ctf_solver/collaboration/loop_detect.py`
- Test: `tests/test_loop_detect.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for loop detector."""

from ctf_solver.collaboration.loop_detect import LoopDetector


def test_no_loop():
    ld = LoopDetector()
    assert ld.check("bash", "ls") is None
    assert ld.check("bash", "cat file.txt") is None


def test_warn_at_threshold():
    ld = LoopDetector(warn_threshold=3, break_threshold=5)
    assert ld.check("bash", "ls") is None
    assert ld.check("bash", "ls") is None
    assert ld.check("bash", "ls") == "warn"


def test_break_at_threshold():
    ld = LoopDetector(warn_threshold=3, break_threshold=5)
    for _ in range(5):
        result = ld.check("bash", "ls")
    assert result == "break"


def test_reset_clears_history():
    ld = LoopDetector(warn_threshold=3, break_threshold=5)
    for _ in range(4):
        ld.check("bash", "ls")
    ld.reset()
    assert ld.check("bash", "ls") is None


def test_different_args_no_loop():
    ld = LoopDetector()
    for i in range(10):
        assert ld.check("bash", f"cmd {i}") is None


def test_dict_args():
    ld = LoopDetector()
    assert ld.check("bash", {"command": "ls"}) is None
    assert ld.check("bash", {"command": "ls"}) is None
    assert ld.check("bash", {"command": "ls"}) == "warn"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_loop_detect.py -v
```

- [ ] **Step 3: Write implementation**

```python
"""Tool signature tracking for loop detection — warn then break on repetition."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field


@dataclass
class LoopDetector:
    window: int = 12
    warn_threshold: int = 3
    break_threshold: int = 5
    _recent: deque[str] = field(init=False, default_factory=lambda: deque(maxlen=12))

    def __post_init__(self) -> None:
        self._recent = deque(maxlen=self.window)

    def check(self, tool_name: str, args: dict | str | None = None) -> str | None:
        if args is not None:
            raw = json.dumps(args, sort_keys=True) if isinstance(args, dict) else str(args)
            sig = f"{tool_name}:{raw[:500]}"
        else:
            sig = tool_name
        self._recent.append(sig)
        count = sum(1 for s in self._recent if s == sig)
        if count >= self.break_threshold:
            return "break"
        if count >= self.warn_threshold:
            return "warn"
        return None

    def reset(self) -> None:
        self._recent.clear()

    @property
    def last_sig(self) -> str:
        return self._recent[-1] if self._recent else ""


LOOP_WARNING_MESSAGE = (
    "You are stuck in a loop — you have run the exact same command multiple times "
    "with identical results. STOP repeating this command. Step back, reconsider your approach, "
    "and try a completely different technique or tool."
)
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/test_loop_detect.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add LoopDetector with sliding window signature tracking"
```

---

## Task 5: Message Bus

**Files:**
- Create: `src/ctf_solver/collaboration/message_bus.py`
- Test: `tests/test_message_bus.py`

- [ ] **Step 1: Write failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_message_bus.py -v
```

- [ ] **Step 3: Write implementation**

```python
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
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/test_message_bus.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add ChallengeMessageBus with per-model cursors"
```

---

## Task 6: Circuit Breaker

**Files:**
- Create: `src/ctf_solver/tracking/circuit_breaker.py`
- Test: `tests/test_circuit_breaker.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for circuit breaker."""

import time

from ctf_solver.tracking.circuit_breaker import CircuitBreaker


def test_starts_available():
    cb = CircuitBreaker()
    assert cb.is_available()


def test_trips_after_threshold():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.is_available()
    cb.record_failure()
    assert not cb.is_available()


def test_success_resets():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    cb.record_failure()
    assert cb.is_available()


def test_recovery_after_timeout(monkeypatch):
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
    cb.record_failure()
    assert not cb.is_available()
    current_time = time.monotonic()
    monkeypatch.setattr("time.monotonic", lambda: current_time + 11.0)
    assert cb.is_available()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_circuit_breaker.py -v
```

- [ ] **Step 3: Write implementation**

```python
"""Per-provider circuit breaker — stops dispatching after N consecutive failures."""

from __future__ import annotations

import time


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._consecutive_failures = 0
        self._last_failure_time: float | None = None

    def record_success(self) -> None:
        self._consecutive_failures = 0

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        self._last_failure_time = time.monotonic()

    def is_available(self) -> bool:
        if self._consecutive_failures < self.failure_threshold:
            return True
        if self._last_failure_time is None:
            return True
        if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
            self._consecutive_failures = 0
            return True
        return False
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/test_circuit_breaker.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add CircuitBreaker with recovery timeout"
```

---

## Task 7: Cost Tracker

**Files:**
- Create: `src/ctf_solver/tracking/cost_tracker.py`
- Test: `tests/test_cost_tracker.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for cost tracker."""

from ctf_solver.tracking.cost_tracker import CostTracker


def test_record_and_total():
    ct = CostTracker()
    ct.record_tokens("solver-1", "claude-opus-4-6", input_tokens=1000, output_tokens=500, provider_spec="claude-sdk")
    assert ct.total_cost_usd >= 0
    assert ct.total_tokens == 1500


def test_multiple_agents():
    ct = CostTracker()
    ct.record_tokens("s1", "gpt-5.4", input_tokens=2000, output_tokens=1000, provider_spec="codex")
    ct.record_tokens("s2", "gpt-5.4-mini", input_tokens=500, output_tokens=200, provider_spec="codex")
    assert ct.total_tokens == 3700


def test_format_usage():
    ct = CostTracker()
    ct.record_tokens("s1", "claude-opus-4-6", input_tokens=50000, output_tokens=5000, provider_spec="claude-sdk")
    formatted = ct.format_usage("s1")
    assert "$" in formatted


def test_max_cost_exceeded():
    ct = CostTracker()
    ct.record_tokens("s1", "gpt-5.4", input_tokens=100000, output_tokens=50000, provider_spec="codex")
    assert ct.is_over_budget(0.01)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_cost_tracker.py -v
```

- [ ] **Step 3: Write implementation**

```python
"""Per-agent token/cost tracking with genai-prices and fallback pricing."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

FALLBACK_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-6": {"input": 5.00, "cached_input": 0.50, "output": 25.00},
    "gpt-5.4": {"input": 2.50, "cached_input": 0.25, "output": 15.00},
    "gpt-5.4-mini": {"input": 0.75, "cached_input": 0.075, "output": 4.50},
    "gpt-5.3-codex": {"input": 1.75, "cached_input": 0.175, "output": 14.00},
}


def _calc_cost(input_tokens: int, output_tokens: int, cache_read_tokens: int, model: str) -> float:
    pricing = FALLBACK_PRICING.get(model)
    if not pricing:
        return 0.0
    input_rate = pricing["input"]
    cached_rate = pricing.get("cached_input", input_rate)
    output_rate = pricing["output"]
    uncached = max(0, input_tokens - cache_read_tokens)
    return (uncached * input_rate + cache_read_tokens * cached_rate + output_tokens * output_rate) / 1_000_000


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


@dataclass
class AgentUsage:
    model_name: str = ""
    provider_spec: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class CostTracker:
    by_agent: dict[str, AgentUsage] = field(default_factory=dict)

    def record_tokens(
        self,
        agent_name: str,
        model_name: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        provider_spec: str = "",
    ) -> None:
        cost = _calc_cost(input_tokens, output_tokens, cache_read_tokens, model_name)
        if agent_name not in self.by_agent:
            self.by_agent[agent_name] = AgentUsage(model_name=model_name, provider_spec=provider_spec)
        agent = self.by_agent[agent_name]
        agent.input_tokens += input_tokens
        agent.output_tokens += output_tokens
        agent.cache_read_tokens += cache_read_tokens
        agent.cost_usd += cost

    @property
    def total_cost_usd(self) -> float:
        return sum(a.cost_usd for a in self.by_agent.values())

    @property
    def total_tokens(self) -> int:
        return sum(a.input_tokens + a.output_tokens for a in self.by_agent.values())

    def is_over_budget(self, max_cost: float) -> bool:
        return self.total_cost_usd >= max_cost

    def format_usage(self, agent_name: str) -> str:
        agent = self.by_agent.get(agent_name)
        if not agent:
            return ""
        return (
            f"{_fmt_tokens(agent.input_tokens)} in / "
            f"{_fmt_tokens(agent.output_tokens)} out | "
            f"${agent.cost_usd:.4f}"
        )
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/test_cost_tracker.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add CostTracker with fallback pricing"
```

---

## Task 8: Flag Pattern Matcher

**Files:**
- Create: `src/ctf_solver/tools/flag.py`
- Test: `tests/test_flag_pattern.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for flag pattern matching."""

from ctf_solver.tools.flag import extract_flags, DEFAULT_FLAG_PATTERN


def test_extract_standard_flag():
    flags = extract_flags("The flag is FLAG{hello_world}", DEFAULT_FLAG_PATTERN)
    assert flags == ["FLAG{hello_world}"]


def test_extract_ctf_flag():
    flags = extract_flags("Found: ctf{secret123}", DEFAULT_FLAG_PATTERN)
    assert flags == ["ctf{secret123}"]


def test_extract_multiple():
    text = "First: FLAG{a}, then flag{b}, also CTF{c}"
    flags = extract_flags(text, DEFAULT_FLAG_PATTERN)
    assert len(flags) == 3


def test_dedup():
    text = "FLAG{same} and FLAG{same} again"
    flags = extract_flags(text, DEFAULT_FLAG_PATTERN)
    assert flags == ["FLAG{same}"]


def test_custom_pattern():
    flags = extract_flags("key: ABC123XYZ", r"ABC\d+XYZ")
    assert flags == ["ABC123XYZ"]


def test_no_match():
    flags = extract_flags("nothing here", DEFAULT_FLAG_PATTERN)
    assert flags == []


def test_nested_braces():
    flags = extract_flags("FLAG{a{b}c}", DEFAULT_FLAG_PATTERN)
    assert len(flags) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_flag_pattern.py -v
```

- [ ] **Step 3: Write implementation**

```python
"""Flag pattern matching — extract and validate CTF flags from text."""

from __future__ import annotations

import re

DEFAULT_FLAG_PATTERN = r"([Ff][Ll][Aa][Gg]|[Cc][Tt][Ff])\{([^}]+)\}"


def extract_flags(text: str, pattern: str = DEFAULT_FLAG_PATTERN) -> list[str]:
    """Extract unique flags from text using regex pattern. Preserves order."""
    seen: set[str] = set()
    results: list[str] = []
    for match in re.finditer(pattern, text):
        flag = match.group(0)
        if flag not in seen:
            seen.add(flag)
            results.append(flag)
    return results
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/test_flag_pattern.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add flag pattern matcher with dedup"
```

---

## Task 9: Provider Base + Stubs

**Files:**
- Create: `src/ctf_solver/providers/base.py`
- Create: `src/ctf_solver/providers/claude.py`
- Create: `src/ctf_solver/providers/codex.py`
- Create: `src/ctf_solver/providers/zai.py`
- Create: `src/ctf_solver/providers/__init__.py`

- [ ] **Step 1: Write provider base**

```python
"""Provider protocol and data models — the interface all AI providers implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class ToolResult:
    content: str | tuple[bytes, str]
    error: str | None = None


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0


@dataclass
class SolverResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    structured_output: dict | None = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    done: bool = False


class SolverSession(ABC):
    """Active session with an AI provider for one solver instance."""

    @abstractmethod
    async def send(self, message: str, tool_results: list[ToolResult] | None = None) -> SolverResponse: ...

    @abstractmethod
    async def inject_context(self, text: str) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...


class ProviderProtocol(ABC):
    # ProviderProtocol uses ABC (nominal subtyping) because providers share
    # common base logic and explicit inheritance is clearer for factories.
    name: str

    @abstractmethod
    async def create_session(
        self,
        solver_id: str,
        system_prompt: str,
        tools: list[ToolDef],
        config: dict,
    ) -> SolverSession: ...

    @abstractmethod
    def validate_config(self, config: dict) -> bool: ...
```

- [ ] **Step 2: Write Claude stub**

```python
"""Claude provider — stub for future integration."""

from __future__ import annotations

from ctf_solver.providers.base import ProviderProtocol


class ClaudeProvider(ProviderProtocol):
    name = "claude"

    def validate_config(self, config: dict) -> bool:
        api_key = config.get("anthropic_api_key", "")
        has_key = bool(api_key)
        try:
            import claude_agent_sdk  # noqa: F401

            has_sdk = True
        except ImportError:
            has_sdk = False
        return has_key and has_sdk

    async def create_session(self, solver_id: str, system_prompt: str, tools: list, config: dict):
        msg = (
            "Claude provider not yet integrated. "
            "Requires: ANTHROPIC_API_KEY env var + claude-agent-sdk package. "
            "Install with: pip install claude-agent-sdk"
        )
        raise NotImplementedError(msg)
```

- [ ] **Step 3: Write Codex stub**

```python
"""Codex provider — stub for future integration."""

from __future__ import annotations

from ctf_solver.providers.base import ProviderProtocol


class CodexProvider(ProviderProtocol):
    name = "codex"

    def validate_config(self, config: dict) -> bool:
        api_key = config.get("openai_api_key", "")
        return bool(api_key)

    async def create_session(self, solver_id: str, system_prompt: str, tools: list, config: dict):
        msg = (
            "Codex provider not yet integrated. "
            "Requires: OPENAI_API_KEY env var + codex CLI."
        )
        raise NotImplementedError(msg)
```

- [ ] **Step 4: Write z.ai stub**

```python
"""z.ai provider — stub for future integration."""

from __future__ import annotations

from ctf_solver.providers.base import ProviderProtocol


class ZAIProvider(ProviderProtocol):
    name = "zai"

    def validate_config(self, config: dict) -> bool:
        api_key = config.get("zai_api_key", "")
        return bool(api_key)

    async def create_session(self, solver_id: str, system_prompt: str, tools: list, config: dict):
        msg = "z.ai provider not yet integrated. Requires: ZAI_API_KEY env var."
        raise NotImplementedError(msg)
```

- [ ] **Step 5: Write provider registry**

```python
"""Provider registry — maps provider names to implementations."""

from ctf_solver.providers.base import ProviderProtocol
from ctf_solver.providers.claude import ClaudeProvider
from ctf_solver.providers.codex import CodexProvider
from ctf_solver.providers.zai import ZAIProvider

PROVIDERS: dict[str, type[ProviderProtocol]] = {
    "claude": ClaudeProvider,
    "codex": CodexProvider,
    "zai": ZAIProvider,
}


def get_provider(name: str) -> ProviderProtocol:
    cls = PROVIDERS.get(name)
    if not cls:
        msg = f"Unknown provider: {name}. Available: {list(PROVIDERS)}"
        raise ValueError(msg)
    return cls()
```

- [ ] **Step 6: Verify imports**

```bash
uv run python -c "from ctf_solver.providers import get_provider; print(get_provider('claude').name)"
```
Expected: `claude`

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: add provider base protocol and stubs for claude, codex, zai"
```

---

## Task 10: Sandbox Protocol + DockerSandbox

> **Note**: This task creates `sandbox/docker.py` first because Task 11 (`solver_base.py`) imports `SandboxProtocol` from it.

**Files:**
- Create: `src/ctf_solver/sandbox/docker.py`
- Test: `tests/test_sandbox.py`

- [ ] **Step 1: Write failing test (with mock Docker)**

```python
"""Tests for DockerSandbox — uses mock Docker daemon when available."""

import subprocess

import pytest
from ctf_solver.sandbox.docker import DockerSandbox, ExecResult


def _docker_available():
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=5, check=True)
        return True
    except Exception:
        return False


def test_exec_result_dataclass():
    r = ExecResult(exit_code=0, stdout="hello", stderr="")
    assert r.exit_code == 0
    assert r.stdout == "hello"


def test_parse_memory_limit():
    sandbox = DockerSandbox(image="test", challenge_dir="/tmp")
    assert sandbox._parse_memory_limit("4g") == 4 * 1024 * 1024 * 1024
    assert sandbox._parse_memory_limit("512m") == 512 * 1024 * 1024
    assert sandbox._parse_memory_limit("2048") == 2048


@pytest.mark.skipif(
    "not _docker_available()",
    reason="Docker not available",
)
@pytest.mark.asyncio
async def test_sandbox_lifecycle():
    sandbox = DockerSandbox(image="alpine:latest", challenge_dir="/tmp")
    await sandbox.start()
    result = await sandbox.exec("echo hello", timeout_s=10)
    assert result.exit_code == 0
    assert "hello" in result.stdout
    await sandbox.stop()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_sandbox.py -v
```

- [ ] **Step 3: Write implementation**

```python
"""Docker sandbox — isolated container for each solver with CTF tools."""

from __future__ import annotations

import asyncio
import io
import logging
import shlex
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import aiodocker

logger = logging.getLogger(__name__)

CONTAINER_LABEL = "ctf-agent"


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str


class SandboxProtocol(Protocol):
    async def start(self) -> None: ...
    async def exec(self, command: str, timeout_s: int = 300) -> ExecResult: ...
    async def read_file(self, path: str) -> str | bytes: ...
    async def read_file_bytes(self, path: str) -> bytes: ...
    async def write_file(self, path: str, content: str | bytes) -> None: ...
    async def stop(self) -> None: ...
    @property
    def container_id(self) -> str: ...


@dataclass
class DockerSandbox:
    image: str
    challenge_dir: str
    memory_limit: str = "4g"
    cpu_limit: int = 2
    workspace_dir: str = ""
    _container: Any = field(default=None, repr=False)
    _docker: Any = field(default=None, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def container_id(self) -> str:
        if not self._container:
            msg = "Sandbox not started"
            raise RuntimeError(msg)
        return self._container.id

    def _parse_memory_limit(self, s: str | None = None) -> int:
        s = (s or self.memory_limit).strip().lower()
        try:
            if s.endswith("g"):
                return int(s[:-1]) * 1024 * 1024 * 1024
            if s.endswith("m"):
                return int(s[:-1]) * 1024 * 1024
            return int(s)
        except (ValueError, IndexError):
            logger.warning("Invalid memory_limit %r, defaulting to 4GB", s)
            return 4 * 1024 * 1024 * 1024

    async def start(self) -> None:
        self._docker = aiodocker.Docker()
        self.workspace_dir = tempfile.mkdtemp(prefix="ctf-workspace-")
        challenge_root = Path(self.challenge_dir).resolve()
        distfiles = str(challenge_root / "distfiles")
        binds: list[str] = [f"{self.workspace_dir}:/challenge/workspace:rw"]
        if Path(distfiles).exists():
            binds.append(f"{distfiles}:/challenge/distfiles:ro")
        config = {
            "Image": self.image,
            "Cmd": ["sleep", "infinity"],
            "WorkingDir": "/challenge",
            "Tty": False,
            "Labels": {CONTAINER_LABEL: "true"},
            "HostConfig": {
                "Binds": binds,
                "ExtraHosts": ["host.docker.internal:host-gateway"],
                "CapAdd": ["SYS_ADMIN", "SYS_PTRACE"],
                "SecurityOpt": ["seccomp=unconfined"],
                "Memory": self._parse_memory_limit(),
                "NanoCpus": int(self.cpu_limit * 1e9),
            },
        }
        self._container = await self._docker.containers.create(config)
        await self._container.start()
        logger.info("Sandbox started: %s", self._container.id[:12])

    async def exec(self, command: str, timeout_s: int = 300) -> ExecResult:
        if not self._container:
            msg = "Sandbox not started"
            raise RuntimeError(msg)
        async with self._lock:
            return await self._exec_inner(command, timeout_s)

    async def _exec_inner(self, command: str, timeout_s: int) -> ExecResult:
        wrapped = f"timeout --signal=KILL --kill-after=5 {timeout_s} bash -c {shlex.quote(command)}"
        exec_instance = await self._container.exec(
            cmd=["bash", "-c", wrapped], stdout=True, stderr=True, tty=False,
        )
        stream = exec_instance.start(detach=False)
        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []

        async def _collect() -> None:
            while True:
                msg = await stream.read_out()
                if msg is None:
                    break
                if msg.stream == 1:
                    stdout_chunks.append(msg.data)
                else:
                    stderr_chunks.append(msg.data)

        try:
            await asyncio.wait_for(_collect(), timeout=timeout_s + 30)
        except TimeoutError:
            try:
                await stream.close()
            except Exception:
                pass
            return ExecResult(exit_code=-1, stdout=b"".join(stdout_chunks).decode("utf-8", errors="replace"), stderr="Command timed out")
        inspect = await exec_instance.inspect()
        exit_code = inspect.get("ExitCode", 0)
        return ExecResult(
            exit_code=exit_code,
            stdout=b"".join(stdout_chunks).decode("utf-8", errors="replace"),
            stderr=b"".join(stderr_chunks).decode("utf-8", errors="replace"),
        )

    async def read_file(self, path: str) -> str | bytes:
        if not self._container:
            msg = "Sandbox not started"
            raise RuntimeError(msg)
        tar = await asyncio.wait_for(self._container.get_archive(path), timeout=30)
        with tar:
            for member in tar:
                if member.isfile():
                    f = tar.extractfile(member)
                    if f:
                        data = f.read()
                        try:
                            return data.decode("utf-8")
                        except UnicodeDecodeError:
                            return data
        msg = f"No file found at {path}"
        raise FileNotFoundError(msg)

    async def read_file_bytes(self, path: str) -> bytes:
        result = await self.read_file(path)
        if isinstance(result, str):
            return result.encode("utf-8")
        return result

    async def write_file(self, path: str, content: str | bytes) -> None:
        if not self._container:
            msg = "Sandbox not started"
            raise RuntimeError(msg)
        if isinstance(content, str):
            content = content.encode("utf-8")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            info = tarfile.TarInfo(name=Path(path).name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        buf.seek(0)
        await asyncio.wait_for(
            self._container.put_archive(str(Path(path).parent), buf.getvalue()),
            timeout=30,
        )

    async def stop(self) -> None:
        if self._container:
            try:
                await self._container.delete(force=True)
            except Exception:
                pass
            self._container = None
        if self._docker:
            try:
                await self._docker.close()
            except Exception:
                pass
            self._docker = None
        if self.workspace_dir:
            import shutil
            shutil.rmtree(self.workspace_dir, ignore_errors=True)
            self.workspace_dir = ""
        logger.info("Sandbox stopped")


async def cleanup_orphan_containers() -> None:
    try:
        docker = aiodocker.Docker()
        try:
            containers = await docker.containers.list(all=True, filters={"label": [CONTAINER_LABEL]})
            for c in containers:
                try:
                    await c.delete(force=True)
                except Exception:
                    pass
            if containers:
                logger.info("Cleaned up %d orphan container(s)", len(containers))
        finally:
            await docker.close()
    except Exception as e:
        logger.warning("Orphan cleanup failed: %s", e)
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/test_sandbox.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add DockerSandbox with exec, file I/O, and cleanup"
```

---

## Task 11: Solver Base Types

> **Depends on**: Task 10 (SandboxProtocol defined in `sandbox/docker.py`)

**Files:**
- Create: `src/ctf_solver/solver/solver_base.py`

- [ ] **Step 1: Write solver base types**

```python
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
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from ctf_solver.solver.solver_base import ResultStatus, SolverState, SolverProtocol; print(ResultStatus.SOLVED.value)"
```
Expected: `solved`

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: add solver base types and SolverProtocol"
```

---

## Task 12: Tools (core)

**Files:**
- Create: `src/ctf_solver/tools/core.py`
- Create: `src/ctf_solver/tools/vision.py`

- [ ] **Step 1: Write tools**

```python
"""SDK-agnostic tool logic — pure async functions."""

from __future__ import annotations

import json
import shlex

import httpx

MAX_OUTPUT = 24_000


def _truncate(text: str, limit: int = MAX_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    lines = text.split("\n")
    head = "\n".join(lines[:200])
    return head[:limit] + f"\n... [truncated — {len(text)} total chars, {len(lines)} lines]"


async def do_bash(sandbox, command: str, timeout_seconds: int = 60) -> str:
    result = await sandbox.exec(command, timeout_s=timeout_seconds)
    parts: list[str] = []
    if result.stdout:
        parts.append(result.stdout)
    if result.stderr:
        parts.append(f"[stderr]\n{result.stderr}")
    if result.exit_code != 0:
        parts.append(f"[exit {result.exit_code}]")
    out = "\n".join(parts).strip() or "(no output)"
    return _truncate(out)


async def do_read_file(sandbox, path: str) -> str:
    try:
        data = await sandbox.read_file(path)
    except Exception as e:
        return f"Error reading file: {e}"
    if isinstance(data, bytes):
        return (
            f"Binary file ({len(data)} bytes) — use bash to inspect:\n"
            f"  file {path}\n  xxd {path} | head -40\n  strings {path}"
        )
    return _truncate(data) if isinstance(data, str) else str(data)


async def do_write_file(sandbox, path: str, content: str) -> str:
    try:
        await sandbox.write_file(path, content)
        return f"Written {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


async def do_list_files(sandbox, path: str = "/challenge/distfiles") -> str:
    result = await sandbox.exec(f"ls -la {shlex.quote(path)}")
    if result.exit_code != 0:
        return result.stderr.strip() or f"Error listing {path}"
    return result.stdout.strip() or f"{path} is empty."


async def do_web_fetch(url: str, method: str = "GET", body: str = "") -> str:
    from urllib.parse import urlparse

    host = urlparse(url).hostname or ""
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return "Fetch error: access to localhost is blocked."
    try:
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            resp = await client.request(method, url, content=body or None, headers={"User-Agent": "Mozilla/5.0"})
            text = resp.text
            prefix = f"HTTP {resp.status_code} {resp.reason_phrase}\n{'─' * 40}\n"
            if len(text) > 20_000:
                text = text[:20_000] + f"\n... [truncated, total {len(resp.text)} bytes]"
            return prefix + text
    except Exception as e:
        return f"Fetch error: {e}"


async def do_webhook_create() -> str:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post("https://webhook.site/token")
            if resp.status_code != 200:
                return f"webhook.site error: HTTP {resp.status_code}"
            data = resp.json()
            return json.dumps({"uuid": data["uuid"], "url": f"https://webhook.site/{data['uuid']}"})
    except Exception as e:
        return f"webhook_create error: {e}"


async def do_webhook_get_requests(uuid: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"https://webhook.site/token/{uuid}/requests")
            if resp.status_code != 200:
                return f"webhook.site error: HTTP {resp.status_code}"
            data = resp.json()
            if not data.get("data"):
                return "No requests received yet."
            out = json.dumps(data["data"], indent=2)
            return out[:8000] if len(out) > 8000 else out
    except Exception as e:
        return f"webhook_get_requests error: {e}"


async def do_submit_flag(
    flag: str,
    flag_pattern: str,
    submitted_flags: set[str],
) -> tuple[str, bool]:
    """Validate flag against pattern and dedup set. Returns (display_message, is_new_valid)."""
    from ctf_solver.tools.flag import extract_flags

    flag = flag.strip()
    if not flag:
        return "Empty flag — nothing to validate.", False
    if flag in submitted_flags:
        return "Already tried this flag.", False
    matches = extract_flags(flag, flag_pattern)
    if not matches:
        return f"Flag '{flag}' does not match expected pattern.", False
    submitted_flags.add(flag)
    return f"Flag candidate accepted: {flag}", True


async def do_notify_coordinator(message: str, event_bus: EventBus | None = None, solver_id: str = "") -> str:
    """Send a message to the coordinator via the event bus."""
    if not event_bus:
        return "No event bus available."
    from ctf_solver.events import SolverEvent
    event_bus.publish(SolverEvent(type="coordinator_guidance", solver_id=solver_id, data={"message": message}))
    return "Message sent to coordinator."


async def do_check_findings(message_bus, model_spec: str) -> str:
    """Get unread findings from sibling solvers."""
    if not message_bus:
        return "No message bus available."
    findings = await message_bus.check(model_spec)
    if not findings:
        return "No new findings from other agents."
    return message_bus.format_unread(findings)
```

- [ ] **Step 2: Write vision tool**

```python
"""Image viewing tool for vision-capable models."""

from __future__ import annotations

from pathlib import Path

IMAGE_EXTS: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}

MAX_IMAGE_BYTES = 4 * 1024 * 1024


async def do_view_image(sandbox, filename: str, use_vision: bool = True) -> tuple[bytes, str] | str:
    basename = Path(filename).name
    ext = Path(basename).suffix.lower()
    mime_type = IMAGE_EXTS.get(ext)
    if not mime_type:
        return f"Not a supported image type: {filename}"
    if not use_vision:
        return "Vision not available for this model. Use bash tools instead."
    search_paths = [f"/challenge/distfiles/{basename}", f"/challenge/workspace/{basename}"]
    if filename.startswith("/"):
        search_paths.insert(0, filename)
    for path in search_paths:
        try:
            data = await sandbox.read_file_bytes(path)
            if len(data) > MAX_IMAGE_BYTES:
                return f"Image too large ({len(data) / 1024 / 1024:.1f} MB > 4 MB limit)."
            return (data, mime_type)
        except Exception:
            continue
    return f"File not found: {filename}"
```

- [ ] **Step 3: Verify imports**

```bash
uv run python -c "from ctf_solver.tools.core import do_bash, do_web_fetch; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: add sandbox tools (bash, file I/O, web, webhook, vision)"
```

---

## Task 13: JSONL Tracing

**Files:**
- Create: `src/ctf_solver/tracing.py`
- Test: `tests/test_tracing.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for JSONL tracer."""

from pathlib import Path

from ctf_solver.tracing import SolverTracer


def test_tracer_creates_file(tmp_path):
    tracer = SolverTracer("test-chall", "opus", log_dir=str(tmp_path))
    tracer.event("start", challenge="test")
    tracer.close()
    lines = Path(tracer.path).read_text().strip().split("\n")
    assert len(lines) == 1
    import json
    d = json.loads(lines[0])
    assert d["type"] == "start"
    assert d["challenge"] == "test-chall"


def test_tool_call_logging(tmp_path):
    tracer = SolverTracer("test", "model", log_dir=str(tmp_path))
    tracer.tool_call("bash", {"command": "ls"}, step=1)
    tracer.tool_result("bash", "file1\nfile2", step=1)
    tracer.close()
    lines = Path(tracer.path).read_text().strip().split("\n")
    assert len(lines) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_tracing.py -v
```

- [ ] **Step 3: Write implementation**

```python
"""SolverTracer — JSONL event log for solver sessions."""

from __future__ import annotations

import json
import time
from pathlib import Path


class SolverTracer:
    def __init__(self, challenge_name: str, model_id: str, log_dir: str = "logs") -> None:
        self.challenge_name = challenge_name
        self.model_id = model_id
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        safe_name = challenge_name.replace("/", "_").replace(" ", "-")
        self.path = str(Path(log_dir) / f"{safe_name}-{model_id}-{timestamp}.jsonl")
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "a")  # noqa: SIM115

    def _write(self, data: dict) -> None:
        data["ts"] = time.time()
        self._file.write(json.dumps(data) + "\n")
        self._file.flush()

    def event(self, event_type: str, **kwargs) -> None:
        self._write({"type": event_type, **kwargs})

    def tool_call(self, tool: str, args: dict | str, step: int) -> None:
        self._write({"type": "tool_call", "tool": tool, "args": args, "step": step})

    def tool_result(self, tool: str, result: str, step: int) -> None:
        self._write({"type": "tool_result", "tool": tool, "result": result[:500], "step": step})

    def usage(self, input_tokens: int, output_tokens: int, cache_read_tokens: int, cost_usd: float) -> None:
        self._write({
            "type": "usage",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cost_usd": cost_usd,
        })

    def close(self) -> None:
        if self._file and not self._file.closed:
            self._file.close()
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/test_tracing.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add SolverTracer with JSONL event logging"
```

---

## Task 14: Prompts

**Files:**
- Create: `src/ctf_solver/prompts.py`

- [ ] **Step 1: Write prompt builder**

```python
"""System prompt builder — category-aware CTF solver prompts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ctf_solver.tools.vision import IMAGE_EXTS


@dataclass
class ChallengeMeta:
    name: str = "Unknown"
    category: str = ""
    value: int = 0
    description: str = ""
    tags: list[str] = field(default_factory=list)
    connection_info: str = ""
    hints: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> ChallengeMeta:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(
            name=data.get("name", "Unknown"),
            category=data.get("category", ""),
            value=data.get("value", 0),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            connection_info=data.get("connection_info", ""),
            hints=data.get("hints", []),
        )


def list_distfiles(challenge_dir: str) -> list[str]:
    dist = Path(challenge_dir) / "distfiles"
    if not dist.exists():
        return []
    return sorted(f.name for f in dist.iterdir() if f.is_file())


def _rewrite_connection_info(conn: str) -> str:
    if not conn:
        return conn
    conn = re.sub(r"\blocalhost\b", "host.docker.internal", conn)
    conn = re.sub(r"\b127\.0\.0\.1\b", "host.docker.internal", conn)
    return conn


def build_prompt(
    meta: ChallengeMeta,
    distfile_names: list[str],
    container_arch: str = "unknown",
    hint: str = "",
) -> str:
    conn_info = _rewrite_connection_info(meta.connection_info.strip())
    lines: list[str] = [
        "You are an expert CTF solver. Find the real flag for the challenge below.",
        "",
    ]

    if conn_info:
        lines += [
            "> FIRST ACTION: Connect to the service now.",
            f"> Run: `{conn_info}`",
            "",
        ]

    lines += [
        "## Challenge",
        f"**Name**: {meta.name}",
        f"**Category**: {meta.category or 'Unknown'}",
        f"**Points**: {meta.value or '?'}",
        f"**Arch**: {container_arch}",
    ]
    lines += ["", "## Description", meta.description or "No description provided.", ""]

    if distfile_names:
        lines.append("## Attached Files")
        for name in distfile_names:
            ext = Path(name).suffix.lower()
            is_img = ext in IMAGE_EXTS
            suffix = " <- IMAGE: use steghide/exiftool/strings via bash" if is_img else ""
            lines.append(f"- `/challenge/distfiles/{name}{suffix}`")
        lines.append("")

    if meta.hints:
        lines.append("## Hints")
        for h in meta.hints:
            lines.append(f"- {h}")
        lines.append("")

    if hint:
        lines += ["## Operator Hint", hint, ""]

    lines += [
        "",
        "## Instructions",
        "**Use tools immediately. Do not describe — execute.**",
        "",
        "1. Start working now.",
        "2. Keep using tools until you have the flag.",
        "3. Be creative and thorough.",
        "4. Ignore placeholder flags like CTF{flag}, CTF{placeholder}.",
        "5. Verify every candidate with submit_flag.",
        "6. Once confirmed: output `FLAG: <value>` on its own line.",
    ]

    return "\n".join(lines)
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from ctf_solver.prompts import build_prompt, ChallengeMeta; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: add system prompt builder with category-aware instructions"
```

---

## Task 15: ChallengeSwarm

**Files:**
- Create: `src/ctf_solver/solver/swarm.py`

- [ ] **Step 1: Write swarm implementation**

```python
"""ChallengeSwarm — parallel solver orchestration for a single challenge."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from ctf_solver.collaboration.loop_detect import LoopDetector
from ctf_solver.collaboration.message_bus import ChallengeMessageBus
from ctf_solver.config import Settings, get_active_providers
from ctf_solver.events import EventBus, SolverEvent
from ctf_solver.providers import get_provider
from ctf_solver.providers.base import SolverSession
from ctf_solver.sandbox.docker import DockerSandbox
from ctf_solver.solver.solver_base import ResultStatus, SolverResult
from ctf_solver.tracking.cost_tracker import CostTracker
from ctf_solver.tracing import SolverTracer
from pathlib import Path

logger = logging.getLogger(__name__)

SUBMISSION_COOLDOWNS = [0, 30, 120, 300, 600]


@dataclass
class SolverInstance:
    solver_id: str
    provider_name: str
    model_spec: str
    sandbox: DockerSandbox
    session: SolverSession | None = None
    tracer: SolverTracer | None = None
    loop_detector: LoopDetector = field(default_factory=LoopDetector)
    step_count: int = 0
    flag: str | None = None
    confirmed: bool = False
    findings: str = ""
    cost_usd: float = 0.0
    _bump_insights: str | None = None
    _wrong_submit_count: int = 0
    _last_submit_time: float = 0.0


@dataclass
class ChallengeSwarm:
    challenge_dir: str
    challenge_name: str
    description: str
    category: str
    settings: Settings
    event_bus: EventBus
    cost_tracker: CostTracker = field(default_factory=CostTracker)
    message_bus: ChallengeMessageBus = field(default_factory=ChallengeMessageBus)
    solvers: dict[str, SolverInstance] = field(default_factory=dict)
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    confirmed_flag: str | None = None
    winner_id: str | None = None
    _flag_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _submitted_flags: set[str] = field(default_factory=set)

    def _check_cooldown(self, inst: SolverInstance) -> tuple[bool, str]:
        """Check if solver is in cooldown. Returns (is_cooled_down, message)."""
        wrong_count = inst._wrong_submit_count
        cooldown_idx = min(wrong_count, len(SUBMISSION_COOLDOWNS) - 1)
        cooldown = SUBMISSION_COOLDOWNS[cooldown_idx]
        if cooldown > 0:
            elapsed = time.monotonic() - inst._last_submit_time
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                return False, f"COOLDOWN — wait {remaining}s. {wrong_count} wrong submissions."
        return True, ""

    def _record_wrong_submit(self, inst: SolverInstance) -> None:
        inst._wrong_submit_count += 1
        inst._last_submit_time = time.monotonic()

    def _create_solvers(self) -> list[SolverInstance]:
        instances = []
        for provider_name, count in get_active_providers(self.settings):
            for i in range(count):
                solver_id = f"{provider_name}-{i}"
                sandbox = DockerSandbox(
                    image=self.settings.sandbox_image,
                    challenge_dir=self.challenge_dir,
                    memory_limit=self.settings.sandbox_memory,
                    cpu_limit=self.settings.sandbox_cpus,
                )
                instance = SolverInstance(
                    solver_id=solver_id,
                    provider_name=provider_name,
                    model_spec=f"{provider_name}/default",
                    sandbox=sandbox,
                )
                instances.append(instance)
        return instances

    async def run(self) -> SolverResult | None:
        instances = self._create_solvers()
        for inst in instances:
            self.solvers[inst.solver_id] = inst
            self.event_bus.publish(SolverEvent(type="solver_started", solver_id=inst.solver_id, data={"provider": inst.provider_name}))

        tasks = [asyncio.create_task(self._run_solver(inst), name=f"solver-{inst.solver_id}") for inst in instances]

        try:
            while tasks:
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        result = task.result()
                    except Exception:
                        continue
                    if result and result.status == ResultStatus.SOLVED:
                        self.cancel_event.set()
                        for p in pending:
                            p.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)
                        return result
                tasks = list(pending)

            self.cancel_event.set()
            return None
        except Exception as e:
            logger.error("Swarm error: %s", e, exc_info=True)
            self.cancel_event.set()
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            return None

    async def _run_solver(self, inst: SolverInstance) -> SolverResult | None:
        t0 = time.monotonic()
        try:
            await inst.sandbox.start()
            self.event_bus.publish(SolverEvent(type="state_change", solver_id=inst.solver_id, data={"state": "running"}))

            provider = get_provider(inst.provider_name)
            config = {
                "anthropic_api_key": self.settings.anthropic_api_key,
                "openai_api_key": self.settings.openai_api_key,
                "zai_api_key": self.settings.zai_api_key,
                "zai_endpoint": self.settings.zai_endpoint,
            }

            if not provider.validate_config(config):
                return SolverResult(
                    solver_id=inst.solver_id,
                    status=ResultStatus.ERROR,
                    flag=None,
                    steps=0,
                    duration=time.monotonic() - t0,
                    error=f"Provider {inst.provider_name} not configured",
                )

            log_dir = self.settings.log_dir or "logs"
            inst.tracer = SolverTracer(self.challenge_name, inst.provider_name, log_dir=log_dir)
            inst.session = await provider.create_session(inst.solver_id, "", [], config)

            # This is where the actual solver loop would run.
            # For stub providers, create_session raises NotImplementedError.
            return SolverResult(
                solver_id=inst.solver_id,
                status=ResultStatus.FAILED,
                flag=None,
                steps=inst.step_count,
                duration=time.monotonic() - t0,
                cost_usd=inst.cost_usd,
                trace_path=Path(inst.tracer.path) if inst.tracer else Path(),
                findings_summary=inst.findings,
            )
        except NotImplementedError as e:
            logger.warning("[%s] Provider stub: %s", inst.solver_id, e)
            return SolverResult(
                solver_id=inst.solver_id,
                status=ResultStatus.ERROR,
                flag=None,
                steps=0,
                duration=time.monotonic() - t0,
                error=str(e),
            )
        except asyncio.CancelledError:
            return SolverResult(
                solver_id=inst.solver_id,
                status=ResultStatus.CANCELLED,
                flag=None,
                steps=inst.step_count,
                duration=time.monotonic() - t0,
            )
        except Exception as e:
            logger.error("[%s] Fatal: %s", inst.solver_id, e, exc_info=True)
            return SolverResult(
                solver_id=inst.solver_id,
                status=ResultStatus.ERROR,
                flag=None,
                steps=inst.step_count,
                duration=time.monotonic() - t0,
                error=str(e),
            )
        finally:
            await inst.sandbox.stop()
            if inst.tracer:
                inst.tracer.close()
            self.event_bus.publish(SolverEvent(type="solver_done", solver_id=inst.solver_id, data={}))

    def kill(self) -> None:
        self.cancel_event.set()

    def get_status(self) -> dict:
        return {
            "challenge": self.challenge_name,
            "cancelled": self.cancel_event.is_set(),
            "winner": self.winner_id,
            "confirmed_flag": self.confirmed_flag,
            "solvers": {
                sid: {
                    "steps": s.step_count,
                    "cost": s.cost_usd,
                    "findings": s.findings[:200],
                    "flag": s.flag,
                }
                for sid, s in self.solvers.items()
            },
        }
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add ChallengeSwarm with parallel solver orchestration"
```

---

## Task 16: Writeup Generator

**Files:**
- Create: `src/ctf_solver/writeup.py`
- Test: `tests/test_writeup.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for writeup generator."""

from ctf_solver.solver.solver_base import ResultStatus, SolverResult
from ctf_solver.writeup import generate_writeup


def test_generate_detail(tmp_path):
    result = SolverResult(
        solver_id="claude-0",
        status=ResultStatus.SOLVED,
        flag="FLAG{test}",
        steps=47,
        duration=154.0,
        findings_summary="Found buffer overflow at 0x0804...",
    )
    generate_writeup(str(tmp_path), "baby-pwn", "pwn", result, total_cost_usd=5.67, total_solvers=3)
    detail = (tmp_path / "solve-detail.md").read_text()
    assert "FLAG{test}" in detail
    assert "baby-pwn" in detail
    assert "claude-0" in detail


def test_generate_brief(tmp_path):
    result = SolverResult(
        solver_id="codex-0",
        status=ResultStatus.SOLVED,
        flag="CTF{win}",
        steps=20,
        duration=60.0,
        findings_summary="Simple XOR encoding",
    )
    generate_writeup(str(tmp_path), "easy-crypto", "crypto", result, total_cost_usd=1.00, total_solvers=5)
    brief = (tmp_path / "solve-brief.md").read_text()
    assert "CTF{win}" in brief
    assert "easy-crypto" in brief


def test_no_flag_skips(tmp_path):
    result = SolverResult(
        solver_id="zai-0",
        status=ResultStatus.FAILED,
        flag=None,
        steps=10,
        duration=30.0,
        findings_summary="Could not solve",
    )
    generate_writeup(str(tmp_path), "hard-rev", "rev", result, total_cost_usd=2.00, total_solvers=3)
    detail = (tmp_path / "solve-detail.md").read_text()
    assert "No flag found" in detail
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_writeup.py -v
```

- [ ] **Step 3: Write implementation**

```python
"""Writeup generator — solve-detail.md and solve-brief.md."""

from __future__ import annotations

from pathlib import Path

from ctf_solver.solver.solver_base import ResultStatus, SolverResult


def _format_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s"


def generate_writeup(
    output_dir: str,
    challenge_name: str,
    category: str,
    result: SolverResult,
    total_cost_usd: float = 0.0,
    total_solvers: int = 1,
) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    flag_display = result.flag or "No flag found"
    status_text = "SOLVED" if result.status == ResultStatus.SOLVED else result.status.value

    detail = (
        f"# Challenge: {challenge_name}\n"
        f"- **Flag**: `{flag_display}`\n"
        f"- **Category**: {category}\n"
        f"- **Status**: {status_text}\n"
        f"- **Winner**: {result.solver_id} ({result.steps} steps, {_format_duration(result.duration)}, ${result.cost_usd:.2f})\n"
        f"- **Total Cost**: ${total_cost_usd:.2f} across {total_solvers} solvers\n"
        f"\n"
        f"## Findings\n"
        f"{result.findings_summary or 'No findings recorded.'}\n"
        f"\n"
        f"## Trace\n"
        f"Full trace: `{result.trace_path}`\n"
    )
    (out / "solve-detail.md").write_text(detail)

    if result.flag:
        brief = (
            f"# {challenge_name} — Flag: `{result.flag}`\n"
            f"{result.findings_summary[:500] if result.findings_summary else 'See solve-detail.md for full writeup.'}\n"
        )
    else:
        brief = (
            f"# {challenge_name} — Unsolved\n"
            f"{result.findings_summary[:500] if result.findings_summary else 'No solution found.'}\n"
        )
    (out / "solve-brief.md").write_text(brief)
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/test_writeup.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add writeup generator (detail + brief)"
```

---

## Task 17: CLI Entry Point

**Files:**
- Create: `src/ctf_solver/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for CLI."""

from click.testing import CliRunner

from ctf_solver.cli import main


def test_no_args_shows_error():
    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code != 0


def test_help_shows_options():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--claude" in result.output
    assert "--codex" in result.output
    assert "--zai" in result.output


def test_dry_run():
    runner = CliRunner()
    result = runner.invoke(main, [
        "--files", "/dev/null",
        "--desc", "test challenge",
        "--claude", "1",
        "--dry-run",
    ])
    assert result.exit_code == 0
    assert "DRY RUN" in result.output or "dry" in result.output.lower()


def test_mutual_exclusion():
    runner = CliRunner()
    result = runner.invoke(main, [
        "--challenge-dir", "/tmp",
        "--files", "/dev/null",
        "--desc", "test",
        "--claude", "1",
    ])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_cli.py -v
```

- [ ] **Step 3: Write implementation**

```python
"""Click CLI entry point — ctf-solve and ctf-msg commands."""

from __future__ import annotations

import json
import logging
import sys

import click
from rich.console import Console

from ctf_solver.config import Settings, get_coordinator_provider, validate_provider_config

console = Console()


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiodocker").setLevel(logging.WARNING)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-8s %(message)s", datefmt="%X"))
    logging.basicConfig(level=level, handlers=[handler], force=True)


@click.command()
@click.option("--challenge-dir", default=None, help="Challenge directory")
@click.option("--files", multiple=True, help="Individual challenge files")
@click.option("--desc", default=None, help="Challenge description (required with --files)")
@click.option("--category", default="", help="Category hint")
@click.option("--claude", "claude_count", default=0, type=int, help="Number of Claude solvers")
@click.option("--codex", "codex_count", default=0, type=int, help="Number of Codex solvers")
@click.option("--zai", "zai_count", default=0, type=int, help="Number of z.ai solvers")
@click.option("--coordinator", default=None, help="Coordinator provider")
@click.option("--no-coordinator", is_flag=True, help="Disable coordinator")
@click.option("--timeout", default=600, type=int, help="Max seconds per challenge")
@click.option("--max-steps", default=100, type=int, help="Max tool calls per solver")
@click.option("--max-cost", default=10.0, type=float, help="Max USD cost")
@click.option("--flag-pattern", default=None, help="Regex for flag extraction")
@click.option("--hint", default="", help="Pre-inject hint")
@click.option("--interactive", is_flag=True, help="Enable stdin hint input")
@click.option("--sandbox-image", default="ctf-sandbox", help="Docker image")
@click.option("--sandbox-memory", default="4g", help="Memory limit per container")
@click.option("--sandbox-cpus", default=2, type=int, help="CPU limit per container")
@click.option("--no-docker", is_flag=True, help="Run on host (debug)")
@click.option("--output-dir", default="", help="Output directory")
@click.option("--log-dir", default="", help="Log directory")
@click.option("--no-tui", is_flag=True, help="CLI mode only")
@click.option("--dry-run", is_flag=True, help="Show config without executing")
@click.option("--port", default=0, type=int, help="Hint endpoint port (0=auto)")
@click.option("--verbose", is_flag=True, help="Debug logging")
def main(
    challenge_dir: str | None,
    files: tuple[str, ...],
    desc: str | None,
    category: str,
    claude_count: int,
    codex_count: int,
    zai_count: int,
    coordinator: str | None,
    no_coordinator: bool,
    timeout: int,
    max_steps: int,
    max_cost: float,
    flag_pattern: str | None,
    hint: str,
    interactive: bool,
    sandbox_image: str,
    sandbox_memory: str,
    sandbox_cpus: int,
    no_docker: bool,
    output_dir: str,
    log_dir: str,
    no_tui: bool,
    dry_run: bool,
    port: int,
    verbose: bool,
) -> None:
    """CTF Solver Agent — multi-model solver swarm."""
    _setup_logging(verbose)

    # Validate input mode
    if challenge_dir and files:
        console.print("[red]Error: --challenge-dir and --files are mutually exclusive[/red]")
        sys.exit(1)

    if files and not desc:
        console.print("[red]Error: --desc is required when using --files[/red]")
        sys.exit(1)

    if not challenge_dir and not files:
        console.print("[red]Error: specify --challenge-dir or --files[/red]")
        sys.exit(1)

    settings = Settings(
        claude_count=claude_count,
        codex_count=codex_count,
        zai_count=zai_count,
        coordinator=coordinator or "",
        no_coordinator=no_coordinator,
        timeout=timeout,
        max_steps=max_steps,
        max_cost=max_cost,
        flag_pattern=flag_pattern or Settings.model_fields["flag_pattern"].default,
        hint=hint,
        interactive=interactive,
        sandbox_image=sandbox_image,
        sandbox_memory=sandbox_memory,
        sandbox_cpus=sandbox_cpus,
        no_docker=no_docker,
        output_dir=output_dir,
        log_dir=log_dir,
        no_tui=no_tui,
        dry_run=dry_run,
        port=port,
        verbose=verbose,
    )

    try:
        validate_provider_config(settings)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    coord = get_coordinator_provider(settings)

    console.print("[bold]CTF Solver Agent[/bold]")
    console.print(f"  Providers: claude={claude_count}, codex={codex_count}, zai={zai_count}")
    console.print(f"  Coordinator: {coord or 'disabled'}")
    console.print(f"  Sandbox: {sandbox_image} ({sandbox_memory}, {sandbox_cpus} CPUs)")
    console.print(f"  Limits: {timeout}s, {max_steps} steps, ${max_cost:.2f}")

    if dry_run:
        console.print("\n[green]DRY RUN — configuration valid.[/green]")
        return

    console.print("\n[yellow]Solver execution not yet available (provider stubs).[/yellow]")
    console.print("Implement providers to enable full execution.")


@click.command()
@click.argument("message")
@click.option("--port", default=9400, type=int, help="Coordinator port")
@click.option("--host", default="127.0.0.1", help="Coordinator host")
def send_message(message: str, port: int, host: str) -> None:
    """Send a hint to a running ctf-solve instance."""
    import urllib.request

    body = json.dumps({"message": message}).encode()
    req = urllib.request.Request(
        f"http://{host}:{port}/hint",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            console.print(f"[green]Sent:[/green] {data.get('queued', message[:200])}")
    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        sys.exit(1)
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/test_cli.py -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: add CLI entry point with full option parsing"
```

---

## Task 18: Sandbox Dockerfile

**Files:**
- Create: `sandbox/Dockerfile`
- Create: `sandbox/sandbox-tools.txt`

- [ ] **Step 1: Write Dockerfile (base image — binary/pwn/web only, heavy tools deferred)**

Create `sandbox/Dockerfile` based on verialabs but with a lighter base set:

```dockerfile
# CTF Solver Sandbox — base image (binary/pwn/web categories)
# Heavy tools (SageMath, Podman, PyTorch) are deferred to a separate image.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm

RUN apt-get update && apt-get install -y \
    netcat-openbsd curl wget nmap \
    binutils file xxd bsdmainutils binwalk \
    gdb ltrace strace \
    exiftool steghide pngcheck imagemagick \
    foremost dcfldd testdisk \
    ffmpeg sox \
    tesseract-ocr tesseract-ocr-eng \
    openssl libssl-dev \
    gcc g++ make cmake \
    python3 python3-pip python3-dev \
    ruby ruby-dev \
    git jq zip unzip ca-certificates ncurses-term \
    && rm -rf /var/lib/apt/lists/*

# radare2
RUN git clone --depth=1 https://github.com/radareorg/radare2 /tmp/r2 \
    && cd /tmp/r2 && bash sys/install.sh --install \
    && ldconfig && rm -rf /tmp/r2

# zsteg
RUN gem install zsteg

# Python CTF libraries
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel
RUN pip3 install --no-cache-dir \
    pwntools pycryptodome sympy gmpy2 requests \
    Pillow z3-solver pytesseract scipy numpy \
    angr capstone unicorn ropgadget tqdm flask \
    PyJWT pyghidra volatility3 pycryptodome

# RsaCtfTool
RUN git clone --depth=1 https://github.com/RsaCtfTool/RsaCtfTool /opt/RsaCtfTool \
    && pip3 install --no-cache-dir /opt/RsaCtfTool

COPY sandbox/sandbox-tools.txt /tools.txt
WORKDIR /challenge
```

- [ ] **Step 2: Write tools reference**

Create `sandbox/sandbox-tools.txt` listing all installed tools.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: add sandbox Dockerfile with base CTF tools"
```

---

## Task 19: TUI Application

**Files:**
- Create: `src/ctf_solver/tui/app.py`
- Create: `src/ctf_solver/tui/screens/main.py`
- Create: `src/ctf_solver/tui/screens/__init__.py`
- Create: `src/ctf_solver/tui/widgets/__init__.py`
- Create: `src/ctf_solver/tui/widgets/solver_panel.py`
- Create: `src/ctf_solver/tui/widgets/message_log.py`
- Create: `src/ctf_solver/tui/widgets/cost_bar.py`
- Create: `src/ctf_solver/tui/widgets/input_bar.py`

- [ ] **Step 1: Write TUI app**

```python
"""Textual TUI application — main entry point."""

from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Footer, Header, Static

from ctf_solver.events import EventBus, SolverEvent
from ctf_solver.tui.widgets.cost_bar import CostBar
from ctf_solver.tui.widgets.input_bar import HintInputBar
from ctf_solver.tui.widgets.message_log import MessageLog
from ctf_solver.tui.widgets.solver_panel import SolverPanel


class CTFApp(App):
    """CTF Solver Agent TUI Dashboard."""

    CSS = """
    Screen { layout: vertical; }
    #main-content { layout: horizontal; height: 1fr; }
    #solver-area { width: 2fr; }
    #sidebar { width: 1fr; layout: vertical; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("l", "toggle_logs", "Logs"),
    ]

    def __init__(self, event_bus: EventBus, challenge_name: str = "Unknown", **kwargs) -> None:
        super().__init__(**kwargs)
        self.event_bus = event_bus
        self.challenge_name = challenge_name
        self._event_queue = event_bus.subscribe()
        self._update_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-content"):
            with Vertical(id="solver-area"):
                yield Static(f"Challenge: {self.challenge_name}", id="title")
                yield SolverPanel()
            with Vertical(id="sidebar"):
                yield MessageLog()
                yield CostBar()
                yield HintInputBar()
        yield Footer()

    async def on_mount(self) -> None:
        self._update_task = asyncio.create_task(self._event_loop())

    async def _event_loop(self) -> None:
        while True:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                self._handle_event(event)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    def _handle_event(self, event: SolverEvent) -> None:
        msg_log = self.query_one(MessageLog)
        msg_log.log_message(f"[{event.solver_id}] {event.type}: {str(event.data)[:100]}")

    def action_toggle_logs(self) -> None:
        pass
```

- [ ] **Step 2: Write solver panel widget**

```python
"""Solver status panel widget."""

from textual.widgets import Static


class SolverPanel(Static):
    DEFAULT_CSS = """
    SolverPanel {
        height: auto;
        padding: 1;
        border: solid green;
    }
    """

    def __init__(self) -> None:
        super().__init__("No solvers running yet.")
```

- [ ] **Step 3: Write message log widget**

```python
"""Message log widget — scrolling feed of solver events."""

from textual.widgets import Static


class MessageLog(Static):
    DEFAULT_CSS = """
    MessageLog {
        height: 1fr;
        padding: 1;
        border: solid blue;
        overflow-y: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__("Messages will appear here...")
        self._messages: list[str] = []

    def log_message(self, message: str) -> None:
        self._messages.append(message)
        if len(self._messages) > 100:
            self._messages = self._messages[-100:]
        self.update("\n".join(self._messages[-20:]))
```

- [ ] **Step 4: Write cost bar widget**

```python
"""Cost progress bar widget."""

from textual.widgets import Static


class CostBar(Static):
    DEFAULT_CSS = """
    CostBar {
        height: 3;
        padding: 1;
        border: solid yellow;
    }
    """

    def __init__(self) -> None:
        super().__init__("Cost: $0.00")

    def update_cost(self, cost: float, max_cost: float) -> None:
        pct = min(100, cost / max_cost * 100) if max_cost > 0 else 0
        bar_len = 30
        filled = int(pct / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        self.update(f"Cost: ${cost:.2f} / ${max_cost:.2f}\n[{bar}] {pct:.0f}%")
```

- [ ] **Step 5: Write hint input bar widget**

```python
"""Hint input bar — user types hints to inject into solvers."""

from textual.message import Message
from textual.widgets import Input


class HintInputBar(Input):
    DEFAULT_CSS = """
    HintInputBar {
        height: 3;
        dock: bottom;
    }
    """

    class HintSubmitted(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def __init__(self) -> None:
        super().__init__(placeholder="Type a hint and press Enter...", id="hint-input")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip():
            self.post_message(self.HintSubmitted(event.value.strip()))
            self.value = ""
```

- [ ] **Step 6: Verify TUI imports**

```bash
uv run python -c "from ctf_solver.tui.app import CTFApp; print('TUI OK')"
```

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: add Textual TUI with solver panel, message log, cost bar, hint input"
```

---

## Task 20: Coordinator Agent

**Files:**
- Create: `src/ctf_solver/solver/coordinator.py`

- [ ] **Step 1: Write coordinator skeleton**

```python
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
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from ctf_solver.solver.coordinator import CoordinatorAgent; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: add CoordinatorAgent with trace-based guidance injection"
```

---

## Task 21: Integration Test

**Files:**
- Test: `tests/test_swarm.py`

- [ ] **Step 1: Write swarm integration test (with mock)**

```python
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
```

- [ ] **Step 2: Run test**

```bash
uv run pytest tests/test_swarm.py -v
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "test: add swarm integration tests"
```

---

## Task 22: Final Verification

- [ ] **Step 1: Run all tests**

```bash
uv run pytest tests/ -v
```

- [ ] **Step 2: Run linter**

```bash
uv run ruff check src/ tests/
```

- [ ] **Step 3: Verify CLI works**

```bash
uv run ctf-solve --help
uv run ctf-solve --files /dev/null --desc "test" --claude 1 --dry-run
```

- [ ] **Step 4: Final commit**

```bash
git add -A && git commit -m "chore: verify all tests pass and lint clean"
```

---

## Deferred Items (Phase 2)

The following spec requirements are explicitly deferred to Phase 2 (post-stabilization). They are listed in the CLI options and spec but will be implemented after Phase 1 is functional:

| Feature | Spec Section | Reason for Deferral |
|---------|-------------|---------------------|
| HTTP hint endpoint server | §2 (ctf-msg transport) | Requires async HTTP server inside main loop; TUI input bar covers interactive hints in Phase 1 |
| `--resume` / session state persistence | §5.10 | Requires serialization design; JSONL traces are crash-safe already |
| `--config` TOML file loading | §2 | Pydantic Settings supports .env; TOML loader adds complexity |
| Retry with exponential backoff | §6 | Only relevant when real providers are integrated (Phase 5) |
| Non-TTY auto-detection | §5.9 | Simple check (`sys.stdout.isatty()`) — add in CLI polish pass |
| `tui/screens/logs.py` | §3 | Logs screen is secondary UI; main dashboard is sufficient for Phase 1 |
| `tui/widgets/coordinator_view.py` | §3 | Coordinator is functional without dedicated widget; messages show in MessageLog |
| Additional test coverage | §11 | Provider base, tools/core, prompts, coordinator tests — add alongside provider integration |
