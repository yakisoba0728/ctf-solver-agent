"""Click CLI entry point — ctf-solve and ctf-msg commands."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import signal
import sys
import tempfile
from pathlib import Path

import click
from rich.console import Console

from ctf_solver.config import Settings, get_coordinator_provider, load_toml_config, validate_provider_config
from ctf_solver.events import EventBus
from ctf_solver.session_state import SessionState
from ctf_solver.solver.swarm import ChallengeSwarm

console = Console()
logger = logging.getLogger(__name__)


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
@click.option("--resume", default=None, help="Resume from previous session log dir")
@click.option("--config", default=None, help="TOML config file")
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
    resume: str | None,
    config: str | None,
) -> None:
    """CTF Solver Agent — multi-model solver swarm."""
    _setup_logging(verbose)

    if config:
        toml_data = load_toml_config(config)
        env_overrides: dict[str, str] = {}
        providers = toml_data.get("providers", {})
        if "anthropic_api_key" in providers:
            env_overrides["ANTHROPIC_API_KEY"] = providers["anthropic_api_key"]
        if "openai_api_key" in providers:
            env_overrides["OPENAI_API_KEY"] = providers["openai_api_key"]
        if "zai_api_key" in providers:
            env_overrides["ZAI_API_KEY"] = providers["zai_api_key"]
        if "zai_endpoint" in providers:
            env_overrides["ZAI_ENDPOINT"] = providers["zai_endpoint"]
        import os

        for k, v in env_overrides.items():
            os.environ.setdefault(k, v)

    if resume:
        try:
            prev = SessionState.load(resume)
        except Exception as e:
            console.print(f"[red]Error loading session state: {e}[/red]")
            sys.exit(1)
        console.print(f"[bold]Previous session: {prev.challenge_name}[/bold]")
        console.print(f"  Started: {prev.started_at}")
        for s in prev.solvers:
            console.print(f"  {s.solver_id}: {s.status}, {s.steps} steps, ${s.cost_usd:.4f}, flag={s.flag}")
        if prev.confirmed_flag:
            console.print(f"\n[bold green]FLAG ALREADY FOUND: {prev.confirmed_flag} (by {prev.winner_id})[/bold green]")
            return
        console.print("\n[yellow]No flag found previously. Re-launching...[/yellow]")

    if not no_tui and not sys.stdout.isatty():
        no_tui = True

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

    if no_docker:
        confirmed = click.confirm("Running without Docker sandbox is dangerous. Continue?", default=False)
        if not confirmed:
            return

    if challenge_dir:
        chall_dir = challenge_dir
    else:
        chall_dir = tempfile.mkdtemp(prefix="ctf-chall-")
        for f in files:
            shutil.copy2(f, chall_dir)
        (Path(chall_dir) / "description.txt").write_text(desc or "")

    event_bus = EventBus()
    swarm = ChallengeSwarm(
        challenge_dir=chall_dir,
        challenge_name=Path(chall_dir).name,
        description=desc or "",
        category=category,
        settings=settings,
        event_bus=event_bus,
    )

    swarm_ref = [swarm]
    sigint_triggered = [False]

    def handle_sigint(signum: int, frame: object) -> None:
        console.print("\n[yellow]SIGINT received, shutting down gracefully...[/yellow]")
        swarm_ref[0].kill()
        swarm_ref[0]._update_session_state()
        swarm_ref[0]._save_session_state()
        sigint_triggered[0] = True

    signal.signal(signal.SIGINT, handle_sigint)

    if no_tui:
        result = asyncio.run(_run_cli(swarm, event_bus, settings, interactive, port, sigint_triggered))
        from ctf_solver.writeup import generate_writeup

        if result and result.flag:
            console.print(f"\n[bold green]FLAG FOUND: {result.flag}[/bold green]")
            console.print(f"  Solver: {result.solver_id}")
            console.print(f"  Steps: {result.steps}, Duration: {result.duration:.1f}s, Cost: ${result.cost_usd:.4f}")
        elif sigint_triggered[0]:
            console.print("\n[yellow]Interrupted — generating partial writeup.[/yellow]")
        else:
            console.print("\n[red]No flag found.[/red]")
        if result:
            generate_writeup(output_dir or chall_dir, Path(chall_dir).name, category, result)
    else:
        from ctf_solver.tui.app import CTFApp

        app = CTFApp(event_bus=event_bus, challenge_name=Path(chall_dir).name, max_cost=max_cost)

        async def run_with_tui() -> object:
            from ctf_solver.hint_server import start_hint_server
            from ctf_solver.writeup import generate_writeup

            hint_server, hint_port = await start_hint_server(event_bus, port)
            console.print(f"  Hint endpoint: port {hint_port}")
            console.print(f"  Use: ctf-msg --port {hint_port} \"your hint\"")
            swarm_task = asyncio.create_task(swarm.run())
            await app.run_async()
            swarm.kill()
            hint_server.close()
            await hint_server.wait_closed()
            result = await swarm_task
            if result:
                generate_writeup(output_dir or chall_dir, Path(chall_dir).name, category, result)
            return result

        result = asyncio.run(run_with_tui())
        if result and result.flag:
            console.print(f"\n[bold green]FLAG: {result.flag}[/bold green]")


async def _run_cli(
    swarm: ChallengeSwarm,
    event_bus: EventBus,
    settings: Settings,
    interactive: bool,
    port: int,
    sigint_triggered: list[bool],
) -> object:
    from ctf_solver.events import SolverEvent
    from ctf_solver.hint_server import start_hint_server

    hint_server, hint_port = await start_hint_server(event_bus, port)
    console.print(f"  Hint endpoint: port {hint_port}")
    console.print(f"  Use: ctf-msg --port {hint_port} \"your hint\"")

    coordinator = None
    coord_provider = get_coordinator_provider(settings)
    if coord_provider:
        from ctf_solver.solver.coordinator import CoordinatorAgent

        coordinator = CoordinatorAgent(
            provider_name=coord_provider,
            settings=settings,
            event_bus=event_bus,
            cost_tracker=swarm.cost_tracker,
            message_bus=swarm.message_bus,
            swarm=swarm,
        )

    queue = event_bus.subscribe()

    async def print_events() -> None:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                if event.type == "solver_started":
                    console.print(f"[green]\u25b6 {event.solver_id} started[/green]")
                elif event.type == "solver_done":
                    console.print(f"[blue]\u25cb {event.solver_id} done[/blue]")
                elif event.type == "flag_found":
                    console.print(f"[bold yellow]\u2691 {event.solver_id}: {event.data}[/bold yellow]")
                elif event.type == "cost_update":
                    pass
                else:
                    console.print(f"  [{event.solver_id}] {event.type}")
            except TimeoutError:
                continue

    events_task = asyncio.create_task(print_events())

    stdin_task: asyncio.Task | None = None
    if interactive:
        loop = asyncio.get_running_loop()

        async def read_stdin() -> None:
            while True:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                hint_text = line.strip()
                if hint_text:
                    event_bus.publish(SolverEvent(type="user_hint", solver_id="operator", data={"message": hint_text}))

        stdin_task = asyncio.create_task(read_stdin())

    if coordinator:
        await coordinator.start()

    result = await swarm.run()

    if coordinator:
        await coordinator.stop()

    if sigint_triggered[0] and result is None:
        best: object = None
        for sid, inst in swarm.solvers.items():
            if inst.flag:
                from ctf_solver.solver.solver_base import ResultStatus, SolverResult

                best = SolverResult(
                    solver_id=sid,
                    status=ResultStatus.CANCELLED,
                    flag=inst.flag,
                    steps=inst.step_count,
                    duration=0.0,
                    cost_usd=inst.cost_usd,
                    findings_summary=inst.findings,
                )
                break
        result = best

    events_task.cancel()
    if stdin_task:
        stdin_task.cancel()
    hint_server.close()
    await hint_server.wait_closed()
    return result


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
