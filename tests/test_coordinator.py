"""Tests for coordinator."""

import json

from ctf_solver.solver.coordinator import CoordinatorAgent


def test_coordinator_summarize_trace():
    agent = CoordinatorAgent.__new__(CoordinatorAgent)
    lines = [
        json.dumps({"type": "tool_call", "tool": "bash", "step": 1, "args": {"command": "ls"}}),
        json.dumps({"type": "tool_result", "tool": "bash", "step": 1, "result": "file.txt"}),
    ]
    summary = agent._summarize_trace(lines)
    assert "bash" in summary
    assert "Step 1" in summary


def test_coordinator_summarize_empty():
    agent = CoordinatorAgent.__new__(CoordinatorAgent)
    summary = agent._summarize_trace([])
    assert "No recent" in summary
