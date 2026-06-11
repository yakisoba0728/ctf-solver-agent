# CTF Solver Agent — Subagent-Driven Implementation Prompt

## Copy this entire content as your first message in a new opencode session.

---

You are implementing the **CTF Solver Agent** project using **Subagent-Driven Development**.

**Working directory:** `/home/yakihyuk0728/ctf-solver-agent`
**GitHub repo:** https://github.com/yakisoba0728/ctf-solver-agent (public, main branch)
**Git identity:** user.name=yakisoba0728, user.email=yakisoba0728@users.noreply.github.com

## What We're Building

An autonomous CTF solver agent that runs multiple AI models (Claude, Codex, z.ai) in parallel against CTF challenges. Each solver gets an isolated Docker container. Models share findings via a message bus. An optional coordinator LLM provides strategic guidance. Textual-based TUI dashboard by default, `--no-tui` for CI.

**Tech Stack:** Python 3.12+, asyncio, Click, Textual, Rich, Pydantic, aiodocker, httpx, PyYAML

## Key Documents (READ THESE FIRST)

1. **Design Spec:** `docs/superpowers/specs/2026-06-12-ctf-solver-agent-design.md`
2. **Implementation Plan:** `docs/superpowers/plans/2026-06-12-ctf-solver-agent.md`

The implementation plan has 22 tasks across 4 phases with full code for each file. **The plan contains exact source code to copy.** Your job is to execute the plan faithfully.

## Execution Strategy

### Phase Grouping

Execute tasks grouped by phase, one subagent per phase:

| Phase | Tasks | Branch Name | Description |
|-------|-------|-------------|-------------|
| Phase 1 (Foundation) | 1-14 | `feat/phase-1-foundation` | Scaffolding, config, events, loop detect, message bus, circuit breaker, cost tracker, flag, providers, sandbox, solver base, tools, tracing, prompts |
| Phase 2 (Orchestration) | 15 | `feat/phase-2-orchestration` | ChallengeSwarm (parallel solver orchestration + flag cooldown) |
| Phase 3 (Interface) | 16-19 | `feat/phase-3-interface` | Writeup, CLI, Dockerfile, TUI |
| Phase 4 (Integration) | 20-22 | `feat/phase-4-integration` | CoordinatorAgent, integration tests, final verification |

### Per-Phase Workflow

For EACH phase:

1. **Create feature branch** from `main`:
   ```bash
   git checkout main && git pull origin main
   git checkout -b <branch-name>
   ```

2. **Dispatch one implementer subagent** (Task tool, general-purpose agent) with:
   - ALL task descriptions for that phase (copy full text from plan)
   - ALL source code for that phase (copy from plan)
   - Context about dependencies on previous phases
   - Instructions to implement ALL tasks in the phase, in order
   - Instructions to run `uv run pytest tests/ -v` and `uv run ruff check src/ tests/` after each task commit
   - Instructions to commit after each individual task

3. **After implementer finishes**, dispatch **TWO review subagents in parallel**:
   - **Spec compliance reviewer** — verify implementation matches design spec
   - **Code quality reviewer** — verify code quality, patterns, test coverage

4. **If reviewers find issues**, dispatch fix subagent to address them, then re-review.

5. **When both reviewers approve**:
   ```bash
   git push origin <branch-name>
   # Create PR and merge
   gh pr create --title "feat: Phase N - <description>" --body "Implements tasks <N-M>" --base main
   gh pr merge <number> --merge
   # Push the branch (do NOT delete it)
   git push origin <branch-name>
   ```

6. **Merge back to main** and proceed to next phase.

### Important Notes

- **DO NOT delete feature branches** after merge. Push them and keep them.
- Each feature branch should be based on the latest `main` (which includes merged previous phases).
- Phase 1 is the largest (14 tasks). The implementer should work through them sequentially, committing after each task.
- Tasks 10→11 have a dependency (Task 11 imports from Task 10's output).
- All provider stubs raise `NotImplementedError` — that's intentional.
- `tools/core.py` has an unused import of `EventBus` in `do_notify_coordinator` — this is intentional as it's imported inside the function body. But the actual `from ctf_solver.events import SolverEvent` inside that function needs `EventBus` type hint. The plan code handles this correctly.
- `prompts.py` references `yaml` but doesn't import it at top level — the `from_yaml` classmethod needs `import yaml` added if used.

### Subagent Prompt Templates

#### Implementer Prompt (per phase)

```
Task tool (general-purpose):
  description: "Implement Phase N: [name]"
  prompt: |
    You are implementing Phase N of the CTF Solver Agent project.

    ## Working Directory
    /home/yakihyuk0728/ctf-solver-agent

    ## Git Setup
    - Branch: <branch-name> (already checked out)
    - Git identity: user.name=yakisoba0728, user.email=yakisoba0728@users.noreply.github.com
    - Commit after EACH task with message from the plan

    ## Tasks to Implement (in order)

    [PASTE FULL TEXT OF ALL TASKS IN THIS PHASE FROM THE PLAN]

    ## Rules

    1. Follow the plan EXACTLY. Copy code from the plan — do not improvise.
    2. Use `uv run` prefix for all commands (pytest, ruff, python).
    3. After each task: run tests and commit.
    4. After ALL tasks in this phase: run `uv run pytest tests/ -v` and `uv run ruff check src/ tests/`
    5. If a test fails or ruff reports errors, fix them before committing.
    6. For Task 1 (scaffolding): run `uv sync` to install dependencies.
    7. For Task 10 (sandbox): the `_parse_memory_limit` method is tested, so it must be public.
    8. For Task 14 (prompts): `ChallengeMeta.from_yaml` needs `import yaml` inside the method body — but since it's not in the plan's code, skip calling it for now. The plan's code references `yaml` without importing it — add `import yaml` at the top of the file.

    ## Report Format
    When done, report:
    - **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED
    - What you implemented (list each task)
    - Test results (pass/fail counts)
    - Ruff results
    - Files changed
    - Any issues or concerns
```

#### Spec Compliance Reviewer Prompt (per phase)

```
Task tool (general-purpose):
  description: "Spec review Phase N"
  prompt: |
    You are reviewing whether the Phase N implementation matches its specification.

    ## What Was Requested

    [PASTE RELEVANT SECTIONS FROM THE DESIGN SPEC]

    ## What Was Implemented

    [PASTE IMPLEMENTER'S REPORT]

    ## Your Job

    Read ALL implementation code in the following files and verify:
    - Every requirement from the spec is implemented
    - Nothing extra was added that wasn't requested
    - No misunderstandings of requirements

    Files to check: [LIST FILES FOR THIS PHASE]

    ## CRITICAL: Do Not Trust the Report

    Read the actual code. Compare to spec line by line.

    Report:
    - ✅ Spec compliant (if everything matches)
    - ❌ Issues found: [list with file:line references]
```

#### Code Quality Reviewer Prompt (per phase)

```
Task tool (general-purpose):
  description: "Code quality review Phase N"
  prompt: |
    You are reviewing code quality for Phase N of the CTF Solver Agent.

    ## Files to Review

    [LIST ALL FILES CREATED/MODIFIED IN THIS PHASE]

    ## Review Criteria

    1. **Code style:** Clean, consistent, follows Python conventions
    2. **Test coverage:** Every module has tests, tests verify real behavior
    3. **Error handling:** Appropriate error types, no bare except
    4. **Type hints:** Functions have type annotations
    5. **No dead code:** No unused imports, no unreachable code
    6. **Security:** No hardcoded secrets, no eval/exec
    7. **File organization:** Each file has one clear responsibility
    8. **Docstrings:** Modules have docstrings

    ## Run these commands and include output:
    ```bash
    cd /home/yakihyuk0728/ctf-solver-agent
    uv run pytest tests/ -v
    uv run ruff check src/ tests/
    ```

    Report:
    - **Strengths:** What's good
    - **Issues:** Critical / Important / Minor (with file:line references)
    - **Assessment:** APPROVED or NEEDS FIXES
```

## Phase Details

### Phase 1: Foundation (Tasks 1-14, Branch: feat/phase-1-foundation)

This is the bulk of the project. Tasks:

| Task | Files | Key Details |
|------|-------|-------------|
| 1: Project Scaffolding | pyproject.toml, src/ctf_solver/__init__.py | Run `uv sync` |
| 2: Config Module | config.py, test_config.py | Pydantic Settings, 6 tests |
| 3: Event System | events.py, test_events.py | EventBus + SolverEvent, 3 tests |
| 4: Loop Detector | collaboration/loop_detect.py, test_loop_detect.py | Sliding window, 6 tests |
| 5: Message Bus | collaboration/message_bus.py, test_message_bus.py | Per-model cursors, 4 tests |
| 6: Circuit Breaker | tracking/circuit_breaker.py, test_circuit_breaker.py | Recovery timeout, 4 tests |
| 7: Cost Tracker | tracking/cost_tracker.py, test_cost_tracker.py | Fallback pricing, 4 tests |
| 8: Flag Pattern | tools/flag.py, test_flag_pattern.py | Regex matching, 7 tests |
| 9: Provider Stubs | providers/*.py | ABC-based, validate_config |
| 10: Sandbox | sandbox/docker.py, test_sandbox.py | DockerSandbox + SandboxProtocol |
| 11: Solver Base | solver/solver_base.py | ResultStatus, SolverState, SolverProtocol |
| 12: Tools Core | tools/core.py, tools/vision.py | bash, file I/O, web, webhook, vision |
| 13: Tracing | tracing.py, test_tracing.py | JSONL logger, 2 tests |
| 14: Prompts | prompts.py | System prompt builder |

**Dependency:** Task 11 depends on Task 10 (SandboxProtocol).

### Phase 2: Orchestration (Task 15, Branch: feat/phase-2-orchestration)

| Task | Files | Key Details |
|------|-------|-------------|
| 15: ChallengeSwarm | solver/swarm.py | Parallel solver orchestration, flag cooldown, cancel propagation |

This is the most complex single task. It wires together providers, sandbox, events, message bus, cost tracker, and tracing.

### Phase 3: Interface (Tasks 16-19, Branch: feat/phase-3-interface)

| Task | Files | Key Details |
|------|-------|-------------|
| 16: Writeup Generator | writeup.py, test_writeup.py | solve-detail.md + solve-brief.md |
| 17: CLI Entry Point | cli.py, test_cli.py | Click CLI, ctf-solve + ctf-msg |
| 18: Sandbox Dockerfile | sandbox/Dockerfile, sandbox-tools.txt | Ubuntu-based CTF tools |
| 19: TUI Application | tui/*.py | Textual app, widgets |

### Phase 4: Integration (Tasks 20-22, Branch: feat/phase-4-integration)

| Task | Files | Key Details |
|------|-------|-------------|
| 20: Coordinator Agent | solver/coordinator.py | Trace-based guidance injection |
| 21: Integration Tests | test_swarm.py | Swarm integration with stubs |
| 22: Final Verification | All | Full test suite + lint + CLI verification |

## Final Validation (After All Phases)

After all 4 phases are merged to main, dispatch TWO final review subagents **in parallel**:

1. **Final Spec Compliance Review** — review entire codebase against the design spec
2. **Final Code Quality Review** — review entire codebase for quality

If either finds issues, create a `fix/final-review-fixes` branch, dispatch a fix subagent, review again, then merge.

## Known Issues in Plan Code

These are minor issues in the plan's source code that the implementer should be aware of:

1. **`tools/core.py` line `do_notify_coordinator`**: The function signature uses `EventBus | None` but doesn't import `EventBus` at the top. The import `from ctf_solver.events import SolverEvent` is inside the function body. Add the `EventBus` type hint import or remove the type hint. **Recommended fix:** Change `event_bus: EventBus | None = None` to `event_bus: Any = None` and add `from typing import Any` to the imports.

2. **`prompts.py`**: The `ChallengeMeta.from_yaml` classmethod uses `yaml.safe_load` but `yaml` is not imported. Add `import yaml` at the top of the file.

3. **`swarm.py`**: The import `from ctf_solver.tracing import SolverTracer` uses the module directly (not from a subpackage). This is correct since `tracing.py` is at `src/ctf_solver/tracing.py`.

## Quick Reference Commands

```bash
# Setup (only needed once in Task 1)
uv sync

# Run all tests
uv run pytest tests/ -v

# Run specific test
uv run pytest tests/test_config.py -v

# Lint
uv run ruff check src/ tests/

# Fix lint issues
uv run ruff check --fix src/ tests/

# Verify import works
uv run python -c "from ctf_solver.config import Settings; print('OK')"

# CLI test
uv run ctf-solve --help
```

## Start Here

1. Read the implementation plan: `docs/superpowers/plans/2026-06-12-ctf-solver-agent.md`
2. Read the design spec: `docs/superpowers/specs/2026-06-12-ctf-solver-agent-design.md`
3. Create Phase 1 branch and dispatch implementer subagent
4. Follow the per-phase workflow described above

**Load the superpowers-subagent-driven-development skill first** — it provides detailed workflow guidance for this exact execution pattern.
