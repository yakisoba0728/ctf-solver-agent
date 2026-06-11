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
