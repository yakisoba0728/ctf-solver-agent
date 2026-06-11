"""Claude provider — stub for future integration."""

from __future__ import annotations

from ctf_solver.providers.base import ProviderProtocol


class ClaudeProvider(ProviderProtocol):
    name = "claude"

    def validate_config(self, config: dict) -> bool:
        api_key = config.get("anthropic_api_key", "")
        has_key = bool(api_key)
        try:
            import claude_agent_sdk  # noqa: F401

            has_sdk = True
        except ImportError:
            has_sdk = False
        return has_key and has_sdk

    async def create_session(self, solver_id: str, system_prompt: str, tools: list, config: dict):
        msg = (
            "Claude provider not yet integrated. "
            "Requires: ANTHROPIC_API_KEY env var + claude-agent-sdk package. "
            "Install with: pip install claude-agent-sdk"
        )
        raise NotImplementedError(msg)
