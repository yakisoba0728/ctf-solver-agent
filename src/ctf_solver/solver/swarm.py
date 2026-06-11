"""ChallengeSwarm — parallel solver orchestration for a single challenge."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import aiodocker

from ctf_solver.collaboration.loop_detect import LOOP_WARNING_MESSAGE, LoopDetector
from ctf_solver.collaboration.message_bus import ChallengeMessageBus
from ctf_solver.config import Settings, get_active_providers
from ctf_solver.events import EventBus, SolverEvent
from ctf_solver.prompts import ChallengeMeta, build_prompt, list_distfiles
from ctf_solver.providers import get_provider
from ctf_solver.providers.base import SolverSession, ToolCall, ToolResult
from ctf_solver.sandbox.docker import DockerSandbox
from ctf_solver.solver.solver_base import ResultStatus, SolverResult
from ctf_solver.tools.core import (
    do_bash,
    do_check_findings,
    do_list_files,
    do_notify_coordinator,
    do_read_file,
    do_submit_flag,
    do_web_fetch,
    do_write_file,
)
from ctf_solver.tools.flag import extract_flags
from ctf_solver.tracing import SolverTracer
from ctf_solver.tracking.circuit_breaker import CircuitBreaker
from ctf_solver.tracking.cost_tracker import CostTracker

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
    _circuit_breakers: dict[str, CircuitBreaker] = field(default_factory=dict)

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

    def _create_circuit_breakers(self) -> dict[str, CircuitBreaker]:
        return {name: CircuitBreaker() for name, _ in get_active_providers(self.settings)}

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
        self._circuit_breakers = self._create_circuit_breakers()
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
            try:
                docker = aiodocker.Docker()
                await docker.version()
                await docker.close()
            except Exception:
                return SolverResult(
                    solver_id=inst.solver_id,
                    status=ResultStatus.ERROR,
                    flag=None,
                    steps=0,
                    duration=time.monotonic() - t0,
                    error="Docker is not running. Start Docker and try again.",
                )

            await inst.sandbox.start()
            self.event_bus.publish(SolverEvent(type="state_change", solver_id=inst.solver_id, data={"state": "running"}))

            provider = get_provider(inst.provider_name)
            config = self.settings.to_provider_config()

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

            meta = ChallengeMeta(
                name=self.challenge_name,
                category=self.category,
                description=self.description,
            )
            distfiles = list_distfiles(self.challenge_dir)
            container_arch = "linux/amd64"
            system_prompt = build_prompt(meta, distfiles, container_arch, hint=self.settings.hint)
            tools: list = []
            inst.session = await provider.create_session(inst.solver_id, system_prompt, tools, config)

            message = ""
            submitted_flags: set[str] = set()

            while not self.cancel_event.is_set():
                if inst.step_count >= self.settings.max_steps:
                    break
                elapsed = time.monotonic() - t0
                if elapsed >= self.settings.timeout:
                    return SolverResult(
                        solver_id=inst.solver_id,
                        status=ResultStatus.TIMEOUT,
                        flag=inst.flag,
                        steps=inst.step_count,
                        duration=elapsed,
                        cost_usd=inst.cost_usd,
                        trace_path=Path(inst.tracer.path) if inst.tracer else Path(),
                        findings_summary=inst.findings,
                    )
                if self.cost_tracker.is_over_budget(self.settings.max_cost):
                    break

                cb = self._circuit_breakers.get(inst.provider_name)
                if cb and not cb.is_available():
                    break

                if inst.step_count > 0 and inst.step_count % 5 == 0:
                    insights_text = await do_check_findings(self.message_bus, inst.solver_id)
                    if insights_text and "No new findings" not in insights_text:
                        await inst.session.inject_context(insights_text)

                try:
                    response = await inst.session.send(message)
                except Exception as e:
                    if cb:
                        cb.record_failure()
                    logger.warning("[%s] LLM call failed: %s", inst.solver_id, e)
                    break

                if cb:
                    cb.record_success()

                self.cost_tracker.record_tokens(
                    inst.solver_id, inst.model_spec,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    cache_read_tokens=response.usage.cache_read_tokens,
                    provider_spec=inst.provider_name,
                )
                step_cost = self.cost_tracker.by_agent.get(inst.solver_id)
                if step_cost:
                    inst.cost_usd = step_cost.cost_usd
                self.event_bus.publish(SolverEvent(type="cost_update", solver_id=inst.solver_id, data={"cost": inst.cost_usd}))

                if inst.tracer:
                    inst.tracer.usage(
                        response.usage.input_tokens,
                        response.usage.output_tokens,
                        response.usage.cache_read_tokens,
                        inst.cost_usd,
                    )

                flags_found = extract_flags(response.text, self.settings.flag_pattern)
                if flags_found:
                    for flag in flags_found:
                        msg_text, is_valid = await do_submit_flag(flag, self.settings.flag_pattern, self._submitted_flags)
                        if is_valid:
                            inst.flag = flag
                            inst.confirmed = True
                            async with self._flag_lock:
                                if not self.confirmed_flag:
                                    self.confirmed_flag = flag
                                    self.winner_id = inst.solver_id

                if response.done or not response.tool_calls:
                    break

                tool_results: list[ToolResult] = []
                for tc in response.tool_calls:
                    inst.step_count += 1
                    if inst.tracer:
                        inst.tracer.tool_call(tc.name, tc.arguments, inst.step_count)
                    result_str = await self._execute_tool(inst, tc, submitted_flags)
                    if inst.tracer:
                        inst.tracer.tool_result(tc.name, result_str, inst.step_count)
                    tool_results.append(ToolResult(content=result_str))

                    loop_status = inst.loop_detector.check(tc.name, tc.arguments)
                    if loop_status == "warn":
                        await inst.session.inject_context(LOOP_WARNING_MESSAGE)
                    elif loop_status == "break":
                        return SolverResult(
                            solver_id=inst.solver_id,
                            status=ResultStatus.LOOP_DETECTED,
                            flag=inst.flag,
                            steps=inst.step_count,
                            duration=time.monotonic() - t0,
                            cost_usd=inst.cost_usd,
                            trace_path=Path(inst.tracer.path) if inst.tracer else Path(),
                            findings_summary=inst.findings,
                        )

                message = ""

            if inst.confirmed and inst.flag:
                return SolverResult(
                    solver_id=inst.solver_id,
                    status=ResultStatus.SOLVED,
                    flag=inst.flag,
                    steps=inst.step_count,
                    duration=time.monotonic() - t0,
                    cost_usd=inst.cost_usd,
                    trace_path=Path(inst.tracer.path) if inst.tracer else Path(),
                    findings_summary=inst.findings,
                )

            return SolverResult(
                solver_id=inst.solver_id,
                status=ResultStatus.FAILED,
                flag=inst.flag,
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
                flag=inst.flag,
                steps=inst.step_count,
                duration=time.monotonic() - t0,
            )
        except Exception as e:
            logger.error("[%s] Fatal: %s", inst.solver_id, e, exc_info=True)
            return SolverResult(
                solver_id=inst.solver_id,
                status=ResultStatus.ERROR,
                flag=inst.flag,
                steps=inst.step_count,
                duration=time.monotonic() - t0,
                error=str(e),
            )
        finally:
            await inst.sandbox.stop()
            if inst.tracer:
                inst.tracer.close()
            self.event_bus.publish(SolverEvent(type="solver_done", solver_id=inst.solver_id, data={}))

    async def _execute_tool(self, inst: SolverInstance, tc: ToolCall, submitted_flags: set[str]) -> str:
        name = tc.name
        args = tc.arguments

        if name == "bash":
            return await do_bash(inst.sandbox, args.get("command", ""), args.get("timeout", 60))
        elif name == "read_file":
            return await do_read_file(inst.sandbox, args.get("path", ""))
        elif name == "write_file":
            return await do_write_file(inst.sandbox, args.get("path", ""), args.get("content", ""))
        elif name == "list_files":
            return await do_list_files(inst.sandbox, args.get("path", "/challenge/distfiles"))
        elif name == "web_fetch":
            return await do_web_fetch(args.get("url", ""), args.get("method", "GET"), args.get("body", ""))
        elif name == "submit_flag":
            flag = args.get("flag", "")
            cooled, msg_text = self._check_cooldown(inst)
            if not cooled:
                return msg_text
            result, is_valid = await do_submit_flag(flag, self.settings.flag_pattern, submitted_flags)
            if is_valid:
                inst.flag = flag
                inst.confirmed = True
                async with self._flag_lock:
                    if not self.confirmed_flag:
                        self.confirmed_flag = flag
                        self.winner_id = inst.solver_id
            else:
                self._record_wrong_submit(inst)
            return result
        elif name == "check_findings":
            return await do_check_findings(self.message_bus, inst.solver_id)
        elif name == "notify_coordinator":
            return await do_notify_coordinator(args.get("message", ""), self.event_bus, inst.solver_id)
        else:
            return f"Unknown tool: {name}"

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
