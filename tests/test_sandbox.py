"""Tests for DockerSandbox — uses mock Docker daemon when available."""

import subprocess

import pytest
from ctf_solver.sandbox.docker import DockerSandbox, ExecResult


def _docker_available():
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=5, check=True)
        return True
    except Exception:
        return False


def test_exec_result_dataclass():
    r = ExecResult(exit_code=0, stdout="hello", stderr="")
    assert r.exit_code == 0
    assert r.stdout == "hello"


def test_parse_memory_limit():
    sandbox = DockerSandbox(image="test", challenge_dir="/tmp")
    assert sandbox._parse_memory_limit("4g") == 4 * 1024 * 1024 * 1024
    assert sandbox._parse_memory_limit("512m") == 512 * 1024 * 1024
    assert sandbox._parse_memory_limit("2048") == 2048


@pytest.mark.skipif(
    "not _docker_available()",
    reason="Docker not available",
)
@pytest.mark.asyncio
async def test_sandbox_lifecycle():
    sandbox = DockerSandbox(image="alpine:latest", challenge_dir="/tmp")
    await sandbox.start()
    result = await sandbox.exec("echo hello", timeout_s=10)
    assert result.exit_code == 0
    assert "hello" in result.stdout
    await sandbox.stop()
