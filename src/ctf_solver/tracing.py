"""SolverTracer — JSONL event log for solver sessions."""

from __future__ import annotations

import atexit
import json
import time
from pathlib import Path


class SolverTracer:
    def __init__(self, challenge_name: str, model_id: str, log_dir: str = "logs") -> None:
        self.challenge_name = challenge_name
        self.model_id = model_id
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        safe_name = challenge_name.replace("/", "_").replace(" ", "-")
        self.path = str(Path(log_dir) / f"{safe_name}-{model_id}-{timestamp}.jsonl")
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "a")  # noqa: SIM115
        atexit.register(self.close)

    def _write(self, data: dict) -> None:
        data["ts"] = time.time()
        data["challenge"] = self.challenge_name
        self._file.write(json.dumps(data, default=str) + "\n")
        self._file.flush()

    def event(self, event_type: str, **kwargs) -> None:
        self._write({"type": event_type, **kwargs})

    def tool_call(self, tool: str, args: dict | str, step: int) -> None:
        self._write({"type": "tool_call", "tool": tool, "args": args, "step": step})

    def tool_result(self, tool: str, result: str, step: int) -> None:
        self._write({"type": "tool_result", "tool": tool, "result": result[:500], "step": step})

    def usage(self, input_tokens: int, output_tokens: int, cache_read_tokens: int, cost_usd: float) -> None:
        self._write({
            "type": "usage",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cost_usd": cost_usd,
        })

    def close(self) -> None:
        if self._file and not self._file.closed:
            self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
