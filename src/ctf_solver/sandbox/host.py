"""Host sandbox — runs commands directly on the host (no isolation)."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from ctf_solver.sandbox import ExecResult


class HostSandbox:
    def __init__(self, challenge_dir: str = "") -> None:
        self.challenge_dir = challenge_dir
        self._workspace_dir = ""

    @property
    def container_id(self) -> str:
        return "host"

    async def start(self) -> None:
        self._workspace_dir = tempfile.mkdtemp(prefix="ctf-host-workspace-")

    async def exec(self, command: str, timeout_s: int = 300) -> ExecResult:
        try:
            proc = await asyncio.create_subprocess_exec(
                "bash", "-c", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.challenge_dir or None,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
            return ExecResult(
                exit_code=proc.returncode or 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
            )
        except TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return ExecResult(exit_code=-1, stdout="", stderr="Command timed out")
        except Exception as e:
            return ExecResult(exit_code=-1, stdout="", stderr=str(e))

    async def read_file(self, path: str) -> str | bytes:
        p = Path(path)
        if not p.is_absolute():
            p = Path(self.challenge_dir) / path
        try:
            data = p.read_bytes()
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return data
        except FileNotFoundError:
            raise
        except Exception as e:
            raise FileNotFoundError(str(e)) from e

    async def read_file_bytes(self, path: str) -> bytes:
        p = Path(path)
        if not p.is_absolute():
            p = Path(self.challenge_dir) / path
        return p.read_bytes()

    async def write_file(self, path: str, content: str | bytes) -> None:
        p = Path(path)
        if not p.is_absolute():
            p = Path(self.challenge_dir) / path
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            content = content.encode("utf-8")
        p.write_bytes(content)

    async def stop(self) -> None:
        if self._workspace_dir:
            import shutil
            shutil.rmtree(self._workspace_dir, ignore_errors=True)
            self._workspace_dir = ""
