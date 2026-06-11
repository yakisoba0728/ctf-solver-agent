"""z.ai provider — stub for future integration."""

from __future__ import annotations

from ctf_solver.providers.base import ProviderProtocol


class ZAIProvider(ProviderProtocol):
    name = "zai"

    def validate_config(self, config: dict) -> bool:
        api_key = config.get("zai_api_key", "")
        return bool(api_key)

    async def create_session(self, solver_id: str, system_prompt: str, tools: list, config: dict):
        msg = "z.ai provider not yet integrated. Requires: ZAI_API_KEY env var."
        raise NotImplementedError(msg)
