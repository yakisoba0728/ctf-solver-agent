"""System prompt builder — category-aware CTF solver prompts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ctf_solver.tools.vision import IMAGE_EXTS


@dataclass
class ChallengeMeta:
    name: str = "Unknown"
    category: str = ""
    value: int = 0
    description: str = ""
    tags: list[str] = field(default_factory=list)
    connection_info: str = ""
    hints: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> ChallengeMeta:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(
            name=data.get("name", "Unknown"),
            category=data.get("category", ""),
            value=data.get("value", 0),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            connection_info=data.get("connection_info", ""),
            hints=data.get("hints", []),
        )


def list_distfiles(challenge_dir: str) -> list[str]:
    dist = Path(challenge_dir) / "distfiles"
    if not dist.exists():
        return []
    return sorted(f.name for f in dist.iterdir() if f.is_file())


def _rewrite_connection_info(conn: str) -> str:
    if not conn:
        return conn
    conn = re.sub(r"\blocalhost\b", "host.docker.internal", conn)
    conn = re.sub(r"\b127\.0\.0\.1\b", "host.docker.internal", conn)
    return conn


def build_prompt(
    meta: ChallengeMeta,
    distfile_names: list[str],
    container_arch: str = "unknown",
    hint: str = "",
) -> str:
    conn_info = _rewrite_connection_info(meta.connection_info.strip())
    lines: list[str] = [
        "You are an expert CTF solver. Find the real flag for the challenge below.",
        "",
    ]

    if conn_info:
        lines += [
            "> FIRST ACTION: Connect to the service now.",
            f"> Run: `{conn_info}`",
            "",
        ]

    lines += [
        "## Challenge",
        f"**Name**: {meta.name}",
        f"**Category**: {meta.category or 'Unknown'}",
        f"**Points**: {meta.value or '?'}",
        f"**Arch**: {container_arch}",
    ]
    lines += ["", "## Description", meta.description or "No description provided.", ""]

    if distfile_names:
        lines.append("## Attached Files")
        for name in distfile_names:
            ext = Path(name).suffix.lower()
            is_img = ext in IMAGE_EXTS
            suffix = " <- IMAGE: use steghide/exiftool/strings via bash" if is_img else ""
            lines.append(f"- `/challenge/distfiles/{name}`{suffix}")
        lines.append("")

    if meta.hints:
        lines.append("## Hints")
        for h in meta.hints:
            lines.append(f"- {h}")
        lines.append("")

    if hint:
        lines += ["## Operator Hint", hint, ""]

    lines += [
        "",
        "## Instructions",
        "**Use tools immediately. Do not describe — execute.**",
        "",
        "1. Start working now.",
        "2. Keep using tools until you have the flag.",
        "3. Be creative and thorough.",
        "4. Ignore placeholder flags like CTF{flag}, CTF{placeholder}.",
        "5. Verify every candidate with submit_flag.",
        "6. Once confirmed: output `FLAG: <value>` on its own line.",
    ]

    return "\n".join(lines)
