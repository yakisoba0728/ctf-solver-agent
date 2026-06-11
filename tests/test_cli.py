"""Tests for CLI."""

from click.testing import CliRunner

from ctf_solver.cli import main


def test_no_args_shows_error():
    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code != 0


def test_help_shows_options():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--claude" in result.output
    assert "--codex" in result.output
    assert "--zai" in result.output


def test_dry_run():
    runner = CliRunner()
    result = runner.invoke(main, [
        "--files", "/dev/null",
        "--desc", "test challenge",
        "--claude", "1",
        "--dry-run",
    ])
    assert result.exit_code == 0
    assert "DRY RUN" in result.output


def test_mutual_exclusion():
    runner = CliRunner()
    result = runner.invoke(main, [
        "--challenge-dir", "/tmp",
        "--files", "/dev/null",
        "--desc", "test",
        "--claude", "1",
    ])
    assert result.exit_code != 0
