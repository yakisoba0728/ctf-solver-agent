"""Sandbox abstractions — protocol and data types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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
