"""Codex provider — stub for future integration."""

from __future__ import annotations

from ctf_solver.providers.base import ProviderProtocol


class CodexProvider(ProviderProtocol):
    name = "codex"

    def validate_config(self, config: dict) -> bool:
        api_key = config.get("openai_api_key", "")
        return bool(api_key)

    async def create_session(self, solver_id: str, system_prompt: str, tools: list, config: dict):
        msg = (
            "Codex provider not yet integrated. "
            "Requires: OPENAI_API_KEY env var + codex CLI."
        )
        raise NotImplementedError(msg)
