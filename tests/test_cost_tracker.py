"""Tests for cost tracker."""

from ctf_solver.tracking.cost_tracker import CostTracker


def test_record_and_total():
    ct = CostTracker()
    ct.record_tokens("solver-1", "claude-opus-4-6", input_tokens=1000, output_tokens=500, provider_spec="claude-sdk")
    expected = (1000 * 5.0 + 500 * 25.0) / 1_000_000
    assert abs(ct.total_cost_usd - expected) < 0.001
    assert ct.total_tokens == 1500


def test_multiple_agents():
    ct = CostTracker()
    ct.record_tokens("s1", "gpt-5.4", input_tokens=2000, output_tokens=1000, provider_spec="codex")
    ct.record_tokens("s2", "gpt-5.4-mini", input_tokens=500, output_tokens=200, provider_spec="codex")
    assert ct.total_tokens == 3700


def test_format_usage():
    ct = CostTracker()
    ct.record_tokens("s1", "claude-opus-4-6", input_tokens=50000, output_tokens=5000, provider_spec="claude-sdk")
    formatted = ct.format_usage("s1")
    assert "$" in formatted


def test_max_cost_exceeded():
    ct = CostTracker()
    ct.record_tokens("s1", "gpt-5.4", input_tokens=100000, output_tokens=50000, provider_spec="codex")
    assert ct.is_over_budget(0.01)
