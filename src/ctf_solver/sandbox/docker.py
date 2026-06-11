"""Docker sandbox — isolated container for each solver with CTF tools."""

from __future__ import annotations

import asyncio
import io
import logging
import shlex
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import aiodocker

logger = logging.getLogger(__name__)

CONTAINER_LABEL = "ctf-agent"


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str


class SandboxProtocol(Protocol):
    async def start(self) -> None: ...
    async def exec(self, command: str, timeout_s: int = 300) -> ExecResult: ...
    async def read_file(self, path: str) -> str | bytes: ...
    async def read_file_bytes(self, path: str) -> bytes: ...
    async def write_file(self, path: str, content: str | bytes) -> None: ...
    async def stop(self) -> None: ...
    @property
    def container_id(self) -> str: ...


@dataclass
class DockerSandbox:
    image: str
    challenge_dir: str
    memory_limit: str = "4g"
    cpu_limit: int = 2
    workspace_dir: str = ""
    _container: Any = field(default=None, repr=False)
    _docker: Any = field(default=None, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def container_id(self) -> str:
        if not self._container:
            msg = "Sandbox not started"
            raise RuntimeError(msg)
        return self._container.id

    def _parse_memory_limit(self, s: str | None = None) -> int:
        s = (s or self.memory_limit).strip().lower()
        try:
            if s.endswith("g"):
                return int(s[:-1]) * 1024 * 1024 * 1024
            if s.endswith("m"):
                return int(s[:-1]) * 1024 * 1024
            return int(s)
        except (ValueError, IndexError):
            logger.warning("Invalid memory_limit %r, defaulting to 4GB", s)
            return 4 * 1024 * 1024 * 1024

    async def start(self) -> None:
        self._docker = aiodocker.Docker()
        self.workspace_dir = tempfile.mkdtemp(prefix="ctf-workspace-")
        challenge_root = Path(self.challenge_dir).resolve()
        distfiles = str(challenge_root / "distfiles")
        binds: list[str] = [f"{self.workspace_dir}:/challenge/workspace:rw"]
        if Path(distfiles).exists():
            binds.append(f"{distfiles}:/challenge/distfiles:ro")
        config = {
            "Image": self.image,
            "Cmd": ["sleep", "infinity"],
            "WorkingDir": "/challenge",
            "Tty": False,
            "Labels": {CONTAINER_LABEL: "true"},
            "HostConfig": {
                "Binds": binds,
                "ExtraHosts": ["host.docker.internal:host-gateway"],
                "CapAdd": ["SYS_ADMIN", "SYS_PTRACE"],
                "SecurityOpt": ["seccomp=unconfined"],
                "Memory": self._parse_memory_limit(),
                "NanoCpus": int(self.cpu_limit * 1e9),
            },
        }
        self._container = await self._docker.containers.create(config)
        await self._container.start()
        logger.info("Sandbox started: %s", self._container.id[:12])

    async def exec(self, command: str, timeout_s: int = 300) -> ExecResult:
        if not self._container:
            msg = "Sandbox not started"
            raise RuntimeError(msg)
        async with self._lock:
            return await self._exec_inner(command, timeout_s)

    async def _exec_inner(self, command: str, timeout_s: int) -> ExecResult:
        wrapped = f"timeout --signal=KILL --kill-after=5 {timeout_s} bash -c {shlex.quote(command)}"
        exec_instance = await self._container.exec(
            cmd=["bash", "-c", wrapped], stdout=True, stderr=True, tty=False,
        )
        stream = exec_instance.start(detach=False)
        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []

        async def _collect() -> None:
            while True:
                msg = await stream.read_out()
                if msg is None:
                    break
                if msg.stream == 1:
                    stdout_chunks.append(msg.data)
                else:
                    stderr_chunks.append(msg.data)

        try:
            await asyncio.wait_for(_collect(), timeout=timeout_s + 30)
        except TimeoutError:
            try:
                await stream.close()
            except Exception:
                pass
            return ExecResult(exit_code=-1, stdout=b"".join(stdout_chunks).decode("utf-8", errors="replace"), stderr="Command timed out")
        inspect = await exec_instance.inspect()
        exit_code = inspect.get("ExitCode", 0)
        return ExecResult(
            exit_code=exit_code,
            stdout=b"".join(stdout_chunks).decode("utf-8", errors="replace"),
            stderr=b"".join(stderr_chunks).decode("utf-8", errors="replace"),
        )

    async def read_file(self, path: str) -> str | bytes:
        if not self._container:
            msg = "Sandbox not started"
            raise RuntimeError(msg)
        tar = await asyncio.wait_for(self._container.get_archive(path), timeout=30)
        with tar:
            for member in tar:
                if member.isfile():
                    f = tar.extractfile(member)
                    if f:
                        data = f.read()
                        try:
                            return data.decode("utf-8")
                        except UnicodeDecodeError:
                            return data
        msg = f"No file found at {path}"
        raise FileNotFoundError(msg)

    async def read_file_bytes(self, path: str) -> bytes:
        result = await self.read_file(path)
        if isinstance(result, str):
            return result.encode("utf-8")
        return result

    async def write_file(self, path: str, content: str | bytes) -> None:
        if not self._container:
            msg = "Sandbox not started"
            raise RuntimeError(msg)
        if isinstance(content, str):
            content = content.encode("utf-8")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            info = tarfile.TarInfo(name=Path(path).name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        buf.seek(0)
        await asyncio.wait_for(
            self._container.put_archive(str(Path(path).parent), buf.getvalue()),
            timeout=30,
        )

    async def stop(self) -> None:
        if self._container:
            try:
                await self._container.delete(force=True)
            except Exception:
                pass
            self._container = None
        if self._docker:
            try:
                await self._docker.close()
            except Exception:
                pass
            self._docker = None
        if self.workspace_dir:
            import shutil
            shutil.rmtree(self.workspace_dir, ignore_errors=True)
            self.workspace_dir = ""
        logger.info("Sandbox stopped")


async def cleanup_orphan_containers() -> None:
    try:
        docker = aiodocker.Docker()
        try:
            containers = await docker.containers.list(all=True, filters={"label": [CONTAINER_LABEL]})
            for c in containers:
                try:
                    await c.delete(force=True)
                except Exception:
                    pass
            if containers:
                logger.info("Cleaned up %d orphan container(s)", len(containers))
        finally:
            await docker.close()
    except Exception as e:
        logger.warning("Orphan cleanup failed: %s", e)
