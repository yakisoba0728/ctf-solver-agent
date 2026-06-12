"""Provider registry — maps provider names to implementations."""

from ctf_solver.providers.base import ProviderBase
from ctf_solver.providers.claude import ClaudeProvider
from ctf_solver.providers.codex import CodexProvider
from ctf_solver.providers.zai import ZAIProvider

PROVIDERS: dict[str, type[ProviderBase]] = {
    "claude": ClaudeProvider,
    "codex": CodexProvider,
    "zai": ZAIProvider,
}


def get_provider(name: str) -> ProviderBase:
    cls = PROVIDERS.get(name)
    if not cls:
        msg = f"Unknown provider: {name}. Available: {list(PROVIDERS)}"
        raise ValueError(msg)
    return cls()
