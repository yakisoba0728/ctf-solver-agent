"""Tests for solver base types."""

from ctf_solver.solver.solver_base import ResultStatus, SolverResult, SolverState


def test_result_status_values():
    assert ResultStatus.SOLVED.value == "solved"
    assert ResultStatus.FAILED.value == "failed"
    assert ResultStatus.TIMEOUT.value == "timeout"
    assert ResultStatus.CANCELLED.value == "cancelled"
    assert ResultStatus.LOOP_DETECTED.value == "loop_detected"
    assert ResultStatus.ERROR.value == "error"
    assert ResultStatus.QUOTA_ERROR.value == "quota_error"


def test_solver_state_values():
    assert SolverState.INITIALIZING.value == "initializing"
    assert SolverState.RUNNING.value == "running"
    assert SolverState.DONE.value == "done"


def test_solver_result_defaults():
    r = SolverResult(
        solver_id="test", status=ResultStatus.SOLVED, flag="FLAG{x}", steps=10, duration=5.0
    )
    assert r.flag == "FLAG{x}"
    assert r.error is None
    assert r.cost_usd == 0.0
