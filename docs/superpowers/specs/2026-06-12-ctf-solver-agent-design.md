# CTF Solver Agent — Design Specification

**Date**: 2026-06-12
**Status**: Approved
**Python**: 3.12+

## 1. Overview

Autonomous CTF (Capture The Flag) solver agent that runs multiple AI models in parallel against CTF challenges. Users provide challenge files and descriptions manually via CLI. Inspired by verialabs/ctf-agent (1st place, BSidesSF 2026 CTF, 52/52 solved).

### Core Principles

- **Manual input only** — no auto-fetch from CTFd or any competition platform
- **Provider-agnostic** — abstract provider interface; 3 providers supported (z.ai, Claude, Codex)
- **Docker sandboxed** — each solver runs in an isolated container with CTF tools
- **Collaborative** — models share findings via message bus; optional coordinator LLM provides strategic guidance
- **Interactive TUI** — Textual-based terminal UI by default; `--no-tui` for CI/automation
- **Safe** — cost ceilings, loop detection, timeouts, step limits

---

## 2. CLI Interface

### Entry Points

```bash
# Main command (TUI mode by default)
ctf-solve [OPTIONS]

# External hint injection (sends HTTP POST to running ctf-solve's hint endpoint)
ctf-msg --port 9400 "hint text"
```

### Hint Transport (`ctf-msg`)

`ctf-solve` starts a lightweight HTTP hint endpoint during execution:
- Protocol: HTTP (plain TCP via `asyncio.start_server`)
- Default port: auto-assigned (logged on startup), configurable via `--port`
- Endpoint: `POST /hint` with JSON body `{"message": "text"}`
- Flow: `ctf-msg` → HTTP POST → `EventBus.publish(user_hint)` → all solvers receive hint on next turn
- The hint endpoint is also used by TUI's input bar (internal publish, no HTTP needed)
- `ctf-msg` requires `--port` to match the running `ctf-solve` instance

### Input Modes

Two mutually exclusive input modes with clear precedence:

| Mode | Flags | Behavior |
|------|-------|----------|
| **Directory** | `--challenge-dir ./chall/` | Reads `description.txt` from dir, mounts `distfiles/` subdir |
| **Files** | `--files a.bin b.py --desc "text"` | Creates temp dir, copies files, uses provided description. **`--desc` is required** when using `--files`. |

If both `--challenge-dir` and `--files` are provided, **error out** with a clear message.

### All CLI Options

```bash
ctf-solve \
  # --- Input (mutually exclusive) ---
  --challenge-dir ./chall/          # challenge directory
  --files a.bin b.py                # individual files (requires --desc)
  --desc "challenge description"    # challenge description text
  --category "pwn"                  # category hint (optional)

  # --- Provider Selection ---
  --claude 2                        # 2 Claude solvers
  --codex 2                         # 2 Codex solvers
  --zai 1                           # 1 z.ai solver
  --coordinator claude              # coordinator provider (default: first specified provider)
  --no-coordinator                  # disable coordinator (message bus only)

  # --- Execution Limits ---
  --timeout 600                     # max seconds per challenge (default: 600)
  --max-steps 100                   # max tool calls per solver (default: 100)
  --max-cost 10.00                  # max USD cost across all solvers (hard stop)
  --flag-pattern "FLAG\{[^}]+\}"    # regex for flag extraction (default: common CTF patterns)

  # --- Hints & Interaction ---
  --hint "check HTTP headers"       # pre-inject hint to all solvers
  --interactive                     # enable stdin hint input in CLI mode

  # --- Sandbox ---
  --sandbox-image ctf-sandbox       # Docker image (default: ctf-sandbox)
  --sandbox-memory 4g               # memory limit per container (default: 4g)
  --sandbox-cpus 2                  # CPU limit per container (default: 2)
  --no-docker                       # run on host (debug only, requires confirmation)

  # --- Output ---
  --output-dir ./results/           # output directory (default: challenge location)
  --log-dir ./logs/                 # JSONL trace directory

  # --- Modes ---
  --no-tui                          # CLI mode only (stdout logging, no TUI)
  --dry-run                         # show config without executing
  --resume ./logs/session-xxx/      # resume from previous session

  # --- General ---
  --config ./ctf-config.toml        # config file
  --port 0                          # hint endpoint port (0 = auto-assign)
  --verbose                         # debug logging
```

### Provider Count Validation

- Zero-count providers (e.g., `--claude 0`) are silently ignored.
- At least one provider must have a positive count. Otherwise, error out.
- `--coordinator` defaults to the first provider with a **positive** solver count.
- If `--coordinator` names a provider with zero count, error out with a clear message.

### Config File (TOML)

```toml
[providers.claude]
api_key = "sk-ant-..."           # or OAuth config
model = "claude-opus-4-6"

[providers.codex]
api_key = "sk-..."
model = "gpt-5.4"

[providers.zai]
api_key = "..."
endpoint = "https://api.z.ai/v1/..."

[sandbox]
image = "ctf-sandbox"
memory = "4g"
cpus = 2

[limits]
timeout = 600
max_steps = 100
max_cost = 10.00
```

**Layering**: CLI args > env vars > config file > defaults.

---

## 3. Project Structure

```
ctf-solver-agent/
├── pyproject.toml
├── sandbox/
│   ├── Dockerfile                    # CTF tools sandbox image
│   └── sandbox-tools.txt             # installed tools reference
├── src/
│   └── ctf_solver/
│       ├── __init__.py
│       ├── cli.py                    # Click CLI entry point
│       ├── config.py                 # Pydantic Settings
│       │
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py               # ProviderProtocol(ABC), SolverSession(ABC), SolverResponse
│       │   ├── claude.py             # ClaudeProvider (stub → later)
│       │   ├── codex.py              # CodexProvider (stub → later)
│       │   └── zai.py                # ZAIProvider (stub → later)
│       │
│       ├── solver/
│       │   ├── __init__.py
│       │   ├── solver_base.py        # SolverProtocol, SolverResult, ResultStatus, SolverEvent
│       │   ├── swarm.py              # ChallengeSwarm — parallel solver orchestration
│       │   └── coordinator.py        # CoordinatorAgent — strategic guidance
│       │
│       ├── sandbox/
│       │   ├── __init__.py
│       │   └── docker.py             # DockerSandbox — container lifecycle
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── core.py               # bash, read/write, web_fetch, webhook, list_files
│       │   ├── vision.py             # view_image (for vision-capable models)
│       │   └── flag.py               # submit_flag (local validation), flag pattern matching
│       │
│       ├── collaboration/
│       │   ├── __init__.py
│       │   ├── message_bus.py        # inter-model insight sharing with per-model cursors
│       │   └── loop_detect.py        # loop detection (warn 3x → break 5x)
│       │
│       ├── tracking/
│       │   ├── __init__.py
│       │   ├── cost_tracker.py       # per-agent token/cost tracking with genai-prices
│       │   └── circuit_breaker.py    # per-provider circuit breaker
│       │
│       ├── tracing.py                # SolverTracer (JSONL event log)
│       ├── prompts.py                # system prompt builder (category-aware)
│       ├── writeup.py                # solve-detail.md + solve-brief.md generation
│       ├── events.py                 # SolverEvent enum + event bus
│       │
│       └── tui/
│           ├── __init__.py
│           ├── app.py                # Textual App main
│           ├── screens/
│           │   ├── main.py           # dashboard screen
│           │   └── logs.py           # detailed logs screen
│           └── widgets/
│               ├── solver_panel.py   # per-solver status card
│               ├── message_log.py    # insight/message feed
│               ├── cost_bar.py       # cost progress bar
│               ├── coordinator_view.py  # coordinator guidance display
│               └── input_bar.py      # user hint input
│
├── tests/
│   ├── test_swarm.py
│   ├── test_loop_detect.py
│   ├── test_message_bus.py
│   ├── test_cost_tracker.py
│   ├── test_sandbox.py
│   ├── test_writeup.py
│   ├── test_flag_pattern.py
│   ├── test_events.py
│   └── test_cli.py
│
└── challenges/                       # example challenge structure
    └── example/
        ├── distfiles/
        │   └── chall.bin
        └── description.txt
```

---

## 4. Core Interfaces

### 4.1 Provider Protocol

```python
# providers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict  # JSON Schema

@dataclass
class ToolCall:
    name: str
    arguments: dict

@dataclass
class ToolResult:
    content: str | tuple[bytes, str]  # text or (image_bytes, mime_type)
    error: str | None = None

@dataclass
class SolverResponse:
    text: str
    tool_calls: list[ToolCall]
    structured_output: dict | None  # JSON output for future provider features (e.g. structured flag reporting)
    usage: TokenUsage
    done: bool  # True = model finished (no more tool calls)

@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0

class SolverSession(ABC):
    """Active session with an AI provider for one solver instance."""

    @abstractmethod
    async def send(self, message: str, tool_results: list[ToolResult] | None = None) -> SolverResponse: ...

    @abstractmethod
    async def inject_context(self, text: str) -> None:
        """Inject additional context (insights, hints) into the conversation."""
        ...

    @abstractmethod
    async def close(self) -> None: ...

class ProviderProtocol(ABC):
    """Factory for creating solver sessions."""

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
    def validate_config(self, config: dict) -> bool:
        """Check if required credentials are present."""
        ...
```

### 4.2 Sandbox Protocol

```python
# sandbox/docker.py

from dataclasses import dataclass
from typing import Protocol

@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str

class SandboxProtocol(Protocol):
    """Interface for sandbox environments (Docker, in-memory mock, etc.)."""

    async def start(self) -> None:
        """Initialize and start the sandbox environment."""
        ...

    async def exec(self, command: str, timeout_s: int = 300) -> ExecResult:
        """Execute a command in the sandbox. Returns stdout, stderr, exit code."""
        ...

    async def read_file(self, path: str) -> str | bytes:
        """Read a file from the sandbox. Returns str for text, bytes for binary."""
        ...

    async def read_file_bytes(self, path: str) -> bytes:
        """Read a file from the sandbox as raw bytes."""
        ...

    async def write_file(self, path: str, content: str | bytes) -> None:
        """Write a file into the sandbox."""
        ...

    async def stop(self) -> None:
        """Stop and clean up the sandbox environment."""
        ...

    @property
    def container_id(self) -> str:
        """Unique identifier for the sandbox instance."""
        ...
```

### 4.3 Solver Protocol & Result

```python
# solver/solver_base.py
# SolverProtocol uses typing.Protocol (structural subtyping) so any class with
# matching methods works — enables easy mocking. ProviderProtocol uses ABC
# (nominal subtyping) because providers share common base logic and explicit
# inheritance is clearer.

from enum import Enum
from dataclasses import dataclass
from typing import Protocol
from pathlib import Path

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
    token_usage: TokenUsage
    cost_usd: float
    trace_path: Path
    findings_summary: str
    error: str | None = None

class SolverProtocol(Protocol):
    model_spec: str
    sandbox: SandboxProtocol  # abstract — not coupled to DockerSandbox
    state: SolverState

    async def start(self) -> None:
        """Initialize sandbox container and provider session. Must be called first."""
        ...

    async def run_until_done(self) -> SolverResult:
        """Run the tool-call loop until flag found, limit reached, or cancelled.
        This is the main blocking call — it drives the LLM ↔ tool execution cycle."""
        ...

    def inject_insights(self, insights: str) -> None:
        """Enqueue insights (from siblings or coordinator) for injection into
        the next LLM turn. Can be called anytime between start() and run_until_done()."""
        ...

    async def stop(self) -> None:
        """Cancel the running loop, close provider session, stop sandbox container."""
        ...
```

### 4.4 Event System

```python
# events.py

from dataclasses import dataclass
from typing import Any, Literal
import asyncio

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

class EventBus:
    """Async pub/sub for solver events. Both TUI and CLI subscribe to the same stream."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue[SolverEvent]] = []

    def subscribe(self) -> asyncio.Queue[SolverEvent]: ...

    def publish(self, event: SolverEvent) -> None: ...
        """Fire-and-forget: puts event into all subscriber queues immediately."""

    async def publish_and_wait(self, event: SolverEvent) -> None: ...
        """Publish and yield to the event loop once, allowing subscribers to process."""
```

### 4.5 Insight Message

```python
# collaboration/message_bus.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class InsightMessage:
    solver_id: str
    step: int
    category: Literal["technique", "finding", "dead_end", "flag_candidate"]
    content: str
    confidence: float  # 0.0-1.0, LLM self-assessed or heuristic
```

### 4.6 Circuit Breaker

```python
# tracking/circuit_breaker.py

class CircuitBreaker:
    """Per-provider circuit breaker. Stops dispatching after N consecutive failures."""

    failure_threshold: int = 3
    recovery_timeout: float = 60.0  # seconds before trying again

    def record_success(self) -> None: ...
    def record_failure(self) -> None: ...
    def is_available(self) -> bool: ...
```

---

## 5. Component Details

### 5.1 ChallengeSwarm

Manages parallel solvers for a single challenge. Responsibilities:

- Create N solver instances based on `--claude N --codex N --zai N`
- Run all solvers concurrently via `asyncio`
- First solver to find a valid flag wins — cancel all others
- Share insights every 5 steps via Message Bus
- Inject sibling insights on solver failure/retry (bump)
- Respect timeout, max-steps, max-cost limits
- Flag candidate cooldown: when a solver submits a flag candidate, apply a cooldown before accepting the next candidate from that solver. Cooldown escalates with each consecutive wrong candidate (0s → 30s → 120s → 300s → 600s). A "wrong" candidate is one that matches the flag pattern but is later determined invalid (e.g., duplicate of an already-rejected flag)
- Deduplicate flag candidates across solvers
- Tiebreaker for simultaneous flags: first candidate across the wire (acquired via `asyncio.Lock`) wins. If two solvers submit different valid-looking flags simultaneously, the first one to acquire the lock is recorded as the winner. The second is logged but does not override
- Publish all state changes as SolverEvents
- If a provider's circuit breaker trips, its solvers are stopped gracefully

### 5.2 CoordinatorAgent

Optional strategic coordinator. Reads solver traces, injects targeted guidance.

- Backed by one of the 3 providers (via `--coordinator`)
- Polls solver traces periodically (every 30 seconds or on solver completion)
- Generates technical guidance based on solver progress
- Can bump stuck solvers with new approaches
- Relays user hints to all solvers
- Disabled with `--no-coordinator` — swarm still works with message bus alone
- Its own cost tracked separately

### 5.3 DockerSandbox

One container per solver instance. Based on verialabs pattern.

- Image: `ctf-sandbox` (customizable via `--sandbox-image`)
- Mount challenge files read-only at `/challenge/distfiles/`
- Mount workspace read-write at `/challenge/workspace/`
- `host.docker.internal` for host network access
- `SYS_ADMIN`, `SYS_PTRACE` capabilities for debugging
- Memory limit (default 4g), CPU limit (default 2)
- Command execution with timeout (`timeout --signal=KILL`)
- File I/O via tar archives (aiodocker)
- Auto-cleanup on exit
- Container label for orphan detection/cleanup

### 5.4 Tools (available to all solvers)

| Tool | Description |
|------|-------------|
| `bash` | Execute command in sandbox (with timeout) |
| `read_file` | Read file from sandbox (auto-detect binary/text) |
| `write_file` | Write file to sandbox |
| `list_files` | List directory contents in sandbox |
| `submit_flag` | Validate flag against pattern, record it |
| `web_fetch` | HTTP request (blocks internal/private IPs) |
| `webhook_create` | Create webhook.site token for out-of-band callbacks |
| `webhook_get_requests` | Retrieve webhook requests |
| `view_image` | View image for vision-capable models |
| `notify_coordinator` | Send message to coordinator |

Tools are defined in a **provider-neutral format** (`ToolDef`). Each provider's `SolverSession` maps them to its native tool/function-calling schema.

### 5.5 Flag Pattern Matching

- Default patterns: `FLAG{...}`, `flag{...}`, `CTF{...}`, `ctf{...}`, and common variants
- Configurable via `--flag-pattern` (regex)
- Solver output (both tool results and LLM text) is scanned for flag patterns
- Multiple candidates are deduplicated
- Candidates are logged and displayed in real-time

### 5.6 Loop Detector

Tracks tool call signatures in a sliding window (default 12 calls).

- Same signature 3 times → **warn** (inject warning message)
- Same signature 5 times → **break** (force different approach)
- Reset on bump (insight injection)

### 5.7 Cost Tracker

- Per-agent, per-model, per-provider tracking
- Uses `genai-prices` library with fallback pricing table
- Hard stop at `--max-cost` threshold
- Cache hit rate tracking
- Real-time cost display in TUI

### 5.8 Writeup Generator

Generates two files on completion:

**solve-detail.md**:
```markdown
# Challenge: <name>
- **Flag**: `FLAG{...}`
- **Category**: pwn
- **Winner**: claude-1 (47 steps, 2m 34s, $2.34)
- **Total Cost**: $5.67 across 5 solvers

## Approach
<detailed step-by-step solution from solver trace>

## Tools Used
- bash (23 calls), pwntools, radare2

## Flag Extraction
<how the flag was found>

## Raw Trace
<key tool calls and outputs from JSONL trace>
```

**solve-brief.md**:
```markdown
# <name> — Flag: `FLAG{...}`
<3-5 sentence summary of the solution>
```

### 5.9 TUI (Textual)

**Main Dashboard Screen**:
- Header: challenge name, category, elapsed time, total cost
- Solver panels: per-solver status card (running/stopped/winner, steps, cost, last action)
- Coordinator view: latest coordinator guidance
- Message log: scrolling feed of insights, findings, user hints
- Cost bar: visual progress toward `--max-cost`
- Input bar: type hints to inject into all solvers
- Keyboard shortcuts: `s`=status, `h`=hint, `q`=quit, `l`=logs, `c`=cost

**Logs Screen**:
- Detailed JSONL trace viewer per solver
- Filterable by solver, tool, step range

**Mode Detection**:
- Non-TTY environment → auto-enable `--no-tui`
- `--no-tui` → Rich-formatted stdout logging
- `SIGINT` (Ctrl+C) → graceful shutdown, save state, generate partial writeup

### 5.10 Persistence & Resume

- JSONL traces written in real-time (already crash-safe)
- Session state file (`session-state.json`) written on graceful shutdown:
  - Challenge metadata
  - Solver states and results
  - Cost totals
  - Flags found
- `--resume <session-dir>` reloads state, skips already-completed solvers

---

## 6. Error Handling

| Scenario | Response |
|----------|----------|
| Provider API error | Retry with exponential backoff (3 attempts), then circuit breaker |
| Provider quota exhausted | Mark solver as QUOTA_ERROR, continue others |
| Docker container crash | Log error, mark solver as ERROR, continue others |
| Solver stuck in loop | Loop detector breaks after 5 repetitions |
| Cost ceiling reached | Hard stop all solvers immediately |
| Timeout reached | Cancel all solvers, generate partial writeup |
| User Ctrl+C | Graceful shutdown, save state, partial writeup |
| Invalid challenge input | Error message with usage instructions |
| No providers configured | Error: "Specify at least one provider (--claude, --codex, or --zai)" |
| Docker not running | Error with instructions to start Docker |
| Sandbox image not found | Error with build instructions (`docker build ...`) |

---

## 7. Data Flow

```
User runs ctf-solve
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ 1. Initialization                                        │
│    • Parse CLI args / config file                         │
│    • Validate challenge input (files + description)       │
│    • Build challenge metadata                             │
│    • Verify Docker is running + image exists              │
│    • Create EventBus                                      │
│    • Start TUI or CLI logger (subscribes to EventBus)     │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Swarm Setup                                           │
│    • For each --claude N --codex N --zai N:               │
│      - Create Solver instance with unique ID              │
│      - Each gets its own DockerSandbox                    │
│    • Start CoordinatorAgent (if enabled)                  │
│    • Publish solver_started events                        │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Parallel Execution (ChallengeSwarm)                    │
│    ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│    │Solver 0  │ │Solver 1  │ │Solver 2  │  ...          │
│    │claude-0  │ │codex-0   │ │zai-0     │               │
│    │[Docker]  │ │[Docker]  │ │[Docker]  │               │
│    │          │ │          │ │          │               │
│    │ ┌──────┐ │ │ ┌──────┐ │ │ ┌──────┐ │               │
│    │ │Event │ │ │ │Event │ │ │ │Event │ │               │
│    │ │  Bus │◄┼─┼─┤  Bus │◄┼─┼─┤  Bus │ │               │
│    │ └──┬───┘ │ │ └──┬───┘ │ │ └──┬───┘ │               │
│    └────┼─────┘ └────┼─────┘ └────┼─────┘               │
│         │            │            │                      │
│    ┌────▼────────────▼────────────▼────┐                 │
│    │         Message Bus               │                 │
│    │  • share insights every 5 steps   │                 │
│    │  • broadcast user hints           │                 │
│    │  • structured InsightMessages     │                 │
│    └──────────────┬────────────────────┘                 │
│                   │                                      │
│    ┌──────────────▼────────────────────┐                 │
│    │       Loop Detector (per solver)  │                 │
│    └───────────────────────────────────┘                 │
│                                                          │
│    ┌───────────────────────────────────┐                 │
│    │    Cost Tracker + Circuit Breaker │                 │
│    └───────────────────────────────────┘                 │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Coordinator (optional, periodic)                       │
│    • Read solver traces (JSONL)                           │
│    • Analyze progress, generate strategic guidance        │
│    • Inject guidance into stuck solvers                   │
│    • Relay user hints from EventBus                       │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Completion                                            │
│    • First solver finds valid flag → winner               │
│      - Cancel all other solvers                           │
│      - OR timeout/max-steps/max-cost reached              │
│    • Generate solve-detail.md + solve-brief.md            │
│    • Save session state                                   │
│    • Display cost summary                                 │
│    • Clean up Docker containers                           │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Dependencies

```toml
[project]
name = "ctf-solver-agent"
version = "0.1.0"
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

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.8",
]
```

---

## 9. Provider Implementation Strategy

All three providers start as **stubs** — they implement the full interface but raise `NotImplementedError` with clear messages. The rest of the system (swarm, sandbox, tools, TUI, events, writeup) is fully functional without real AI backends.

Stub behavior:
- `validate_config()` → checks if required env vars are set AND if the provider SDK is importable. Returns `True` only if both conditions are met. This prevents the confusing case where validation passes but `create_session()` fails.
- `create_session()` → if `validate_config()` returned `False`, raises `NotImplementedError` with a message listing exactly what's missing (e.g. "Claude provider not yet integrated. Requires: ANTHROPIC_API_KEY env var + claude-agent-sdk package. Install with: pip install claude-agent-sdk")

When providers are integrated later, only `providers/{name}.py` files change. Everything else remains untouched.

---

## 10. Sandbox Docker Image

Based on verialabs/ctf-agent's `Dockerfile.sandbox`. Includes:

| Category | Tools |
|----------|-------|
| Binary | radare2, GDB, objdump, binwalk, strings, readelf, pyghidra |
| Pwn | pwntools, ROPgadget, angr, unicorn, capstone |
| Crypto | SageMath, RsaCtfTool, z3, gmpy2, pycryptodome, cado-nfs, flatter |
| Forensics | volatility3, Sleuthkit, foremost, exiftool |
| Stego | steghide, stegseek, zsteg, ImageMagick, tesseract OCR |
| Web | curl, nmap, Python requests, flask |
| Misc | ffmpeg, sox, Pillow, numpy, scipy, PyTorch, podman |

> **Note**: SageMath (~3GB) and Podman (Docker-in-Docker) significantly increase build time and image size. Consider splitting into a base image (binary/pwn/web) + category-specific layers, or deferring heavy packages to a separate `ctf-sandbox-full` image. The base `Dockerfile` should install core tools only; optional categories can be added via build args.

---

## 11. Testing Strategy

- **Unit tests**: loop_detect, message_bus, cost_tracker, flag_pattern, events, circuit_breaker
- **Integration tests**: swarm with mock providers, sandbox lifecycle, writeup generation
- **CLI tests**: argument parsing, input validation, config layering
- **TUI tests**: snapshot tests for Textual widgets (optional, later)

---

## 12. Implementation Phases

### Phase 1: Core Infrastructure (no AI)
- config.py, cli.py, events.py
- DockerSandbox
- tools/core.py
- SolverProtocol, SolverResult, ResultStatus
- JSONL tracing

### Phase 2: Orchestration (no AI)
- ChallengeSwarm (with mock provider)
- Message Bus + Loop Detector
- Cost Tracker + Circuit Breaker
- Flag Pattern Matcher

### Phase 3: Output & TUI
- Writeup generator
- Textual TUI app
- CLI logger (--no-tui mode)

### Phase 4: Coordinator
- CoordinatorAgent (with mock provider)

### Phase 5: Provider Integration (later)
- ClaudeProvider
- CodexProvider
- ZAIProvider
