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
