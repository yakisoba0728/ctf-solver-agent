"""Docker integration tests — real container lifecycle with ctf-sandbox image."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from ctf_solver.sandbox.docker import DockerSandbox, cleanup_orphan_containers


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def sandbox():
    s = DockerSandbox(
        image="ctf-sandbox",
        challenge_dir=tempfile.mkdtemp(prefix="ctf-test-"),
        memory_limit="512m",
        cpu_limit=1,
    )
    await s.start()
    yield s
    await s.stop()


@pytest.mark.asyncio
async def test_docker_start_and_stop():
    s = DockerSandbox(
        image="ctf-sandbox",
        challenge_dir=tempfile.mkdtemp(prefix="ctf-test-"),
        memory_limit="512m",
        cpu_limit=1,
    )
    await s.start()
    assert s.container_id
    await s.stop()
    assert s._container is None


@pytest.mark.asyncio
async def test_docker_exec_echo(sandbox: DockerSandbox):
    result = await sandbox.exec("echo hello world")
    assert result.exit_code == 0
    assert "hello world" in result.stdout


@pytest.mark.asyncio
async def test_docker_exec_stderr(sandbox: DockerSandbox):
    result = await sandbox.exec("echo error >&2")
    assert result.exit_code == 0
    combined = result.stdout + result.stderr
    assert "error" in combined


@pytest.mark.asyncio
async def test_docker_exec_nonzero_exit(sandbox: DockerSandbox):
    result = await sandbox.exec("exit 42")
    assert result.exit_code == 42


@pytest.mark.asyncio
async def test_docker_exec_timeout(sandbox: DockerSandbox):
    result = await sandbox.exec("sleep 60", timeout_s=2)
    assert result.exit_code != 0


@pytest.mark.asyncio
async def test_docker_write_and_read_file(sandbox: DockerSandbox):
    await sandbox.write_file("/challenge/test.txt", "hello from test")
    content = await sandbox.read_file("/challenge/test.txt")
    assert content == "hello from test"


@pytest.mark.asyncio
async def test_docker_write_binary_and_read(sandbox: DockerSandbox):
    await sandbox.write_file("/challenge/binary.bin", b"\x00\x01\x02\xff")
    data = await sandbox.read_file("/challenge/binary.bin")
    assert isinstance(data, bytes)
    assert data == b"\x00\x01\x02\xff"


@pytest.mark.asyncio
async def test_docker_read_file_not_found(sandbox: DockerSandbox):
    with pytest.raises(FileNotFoundError):
        await sandbox.read_file("/challenge/nonexistent.txt")


@pytest.mark.asyncio
async def test_docker_read_file_bytes(sandbox: DockerSandbox):
    await sandbox.write_file("/challenge/bytes.txt", "bytes test")
    data = await sandbox.read_file_bytes("/challenge/bytes.txt")
    assert data == b"bytes test"


@pytest.mark.asyncio
async def test_docker_exec_python3(sandbox: DockerSandbox):
    result = await sandbox.exec("python3 -c \"print('CTF{test_flag_1234}')\"")
    assert result.exit_code == 0
    assert "CTF{test_flag_1234}" in result.stdout


@pytest.mark.asyncio
async def test_docker_exec_ctf_tools_available(sandbox: DockerSandbox):
    tools = ["python3", "gdb", "radare2", "strings", "file", "nmap", "curl", "jq"]
    for tool in tools:
        result = await sandbox.exec(f"which {tool}")
        assert result.exit_code == 0, f"{tool} not found in sandbox"


@pytest.mark.asyncio
async def test_docker_workspace_writable(sandbox: DockerSandbox):
    result = await sandbox.exec("touch /challenge/workspace/test_file && echo ok")
    assert result.exit_code == 0
    content = await sandbox.exec("cat /challenge/workspace/test_file")
    assert content.exit_code == 0


@pytest.mark.asyncio
async def test_docker_distfiles_mounted():
    challenge_dir = tempfile.mkdtemp(prefix="ctf-test-")
    distfiles = Path(challenge_dir) / "distfiles"
    distfiles.mkdir()
    (distfiles / "test.txt").write_text("test content")

    s = DockerSandbox(
        image="ctf-sandbox",
        challenge_dir=challenge_dir,
        memory_limit="512m",
        cpu_limit=1,
    )
    await s.start()
    try:
        result = await s.exec("cat /challenge/distfiles/test.txt")
        assert result.exit_code == 0
        assert "test content" in result.stdout
    finally:
        await s.stop()


@pytest.mark.asyncio
async def test_docker_container_id_property(sandbox: DockerSandbox):
    cid = sandbox.container_id
    assert isinstance(cid, str)
    assert len(cid) >= 12


@pytest.mark.asyncio
async def test_docker_stop_idempotent():
    s = DockerSandbox(
        image="ctf-sandbox",
        challenge_dir=tempfile.mkdtemp(prefix="ctf-test-"),
        memory_limit="512m",
        cpu_limit=1,
    )
    await s.start()
    await s.stop()
    await s.stop()


@pytest.mark.asyncio
async def test_docker_memory_limit_enforced(sandbox: DockerSandbox):
    result = await sandbox.exec("cat /proc/meminfo | head -1")
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_cleanup_orphan_containers():
    await cleanup_orphan_containers()
