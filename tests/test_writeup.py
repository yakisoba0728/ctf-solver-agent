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
