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
