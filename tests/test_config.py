"""Tests for config module."""

import pytest


def test_default_settings():
    from ctf_solver.config import Settings

    s = Settings()
    assert s.sandbox_image == "ctf-sandbox"
    assert s.sandbox_memory == "4g"
    assert s.sandbox_cpus == 2
    assert s.timeout == 600
    assert s.max_steps == 100
    assert s.max_cost == 10.0
    assert s.flag_pattern == r"([Ff][Ll][Aa][Gg]|[Cc][Tt][Ff])\{[^}]+\}"


def test_settings_from_env(monkeypatch):
    from ctf_solver.config import Settings

    monkeypatch.setenv("SANDBOX_IMAGE", "my-sandbox")
    monkeypatch.setenv("TIMEOUT", "300")
    monkeypatch.setenv("MAX_COST", "5.0")
    s = Settings()
    assert s.sandbox_image == "my-sandbox"
    assert s.timeout == 300
    assert s.max_cost == 5.0


def test_provider_counts_default():
    from ctf_solver.config import Settings

    s = Settings()
    assert s.claude_count == 0
    assert s.codex_count == 0
    assert s.zai_count == 0


def test_no_providers_raises():
    from ctf_solver.config import Settings, validate_provider_config

    s = Settings()
    with pytest.raises(ValueError, match="at least one provider"):
        validate_provider_config(s)


def test_coordinator_default_is_first_provider():
    from ctf_solver.config import Settings, get_coordinator_provider

    s = Settings(claude_count=0, codex_count=2, zai_count=1)
    assert get_coordinator_provider(s) == "codex"


def test_coordinator_zero_count_excluded():
    from ctf_solver.config import Settings, get_coordinator_provider

    s = Settings(claude_count=0, codex_count=3)
    assert get_coordinator_provider(s) == "codex"


def test_coordinator_explicit_overrides():
    from ctf_solver.config import Settings, get_coordinator_provider

    s = Settings(claude_count=2, codex_count=2, coordinator="codex")
    assert get_coordinator_provider(s) == "codex"
