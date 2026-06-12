"""Claude provider — Anthropic Messages API via httpx."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ctf_solver.providers.base import (
    ProviderBase,
    SolverResponse,
    SolverSession,
    TokenUsage,
    ToolCall,
    ToolDef,
    ToolResult,
)

logger = logging.getLogger(__name__)


def _tools_to_anthropic(tools: list[ToolDef]) -> list[dict]:
    return [
        {"name": t.name, "description": t.description, "input_schema": t.parameters}
        for t in tools
    ]


class ClaudeSession(SolverSession):
    def __init__(self, solver_id: str, system_prompt: str, tools: list[ToolDef], config: dict) -> None:
        self._solver_id = solver_id
        self._api_key = config.get("anthropic_api_key", "")
        self._model = config.get("claude_model", "claude-opus-4-6-20250612")
        self._tools = _tools_to_anthropic(tools)
        self._messages: list[dict] = []
        self._system_prompt = system_prompt
        self._pending_context: str | None = None
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=300.0)
        return self._client

    async def send(self, message: str, tool_results: list[ToolResult] | None = None) -> SolverResponse:
        if tool_results:
            content_blocks = []
            for tr in tool_results:
                content = tr.content if isinstance(tr.content, str) else str(tr.content)
                content_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tr.tool_use_id or tr.call_id,
                    "content": content,
                })
            self._messages.append({"role": "user", "content": content_blocks})
        elif message:
            self._messages.append({"role": "user", "content": message})

        if self._pending_context:
            last_user_idx = None
            for i in range(len(self._messages) - 1, -1, -1):
                if self._messages[i]["role"] == "user":
                    last_user_idx = i
                    break
            if last_user_idx is not None:
                entry = self._messages[last_user_idx]
                if isinstance(entry["content"], str):
                    entry["content"] += f"\n\n{self._pending_context}"
            self._pending_context = None

        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 16384,
            "system": self._system_prompt,
            "messages": self._messages,
        }
        if self._tools:
            body["tools"] = self._tools

        client = self._get_client()
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block["text"])
            elif block.get("type") == "tool_use":
                tool_calls.append(ToolCall(
                    name=block["name"],
                    arguments=block.get("input", {}),
                    call_id=block["id"],
                ))

        usage_data = data.get("usage", {})
        usage = TokenUsage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
            cache_read_tokens=usage_data.get("cache_read_input_tokens", 0),
        )

        stop_reason = data.get("stop_reason", "")
        done = stop_reason == "end_turn" and not tool_calls

        self._messages.append({"role": "assistant", "content": data.get("content", [])})

        return SolverResponse(
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            usage=usage,
            done=done,
        )

    async def inject_context(self, text: str) -> None:
        self._pending_context = text

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


class ClaudeProvider(ProviderBase):
    name = "claude"

    def validate_config(self, config: dict) -> bool:
        return bool(config.get("anthropic_api_key", ""))

    async def create_session(
        self, solver_id: str, system_prompt: str, tools: list[ToolDef], config: dict
    ) -> ClaudeSession:
        return ClaudeSession(solver_id, system_prompt, tools, config)
