"""Lightweight HTTP hint server — accepts JSON hints and publishes to EventBus."""

from __future__ import annotations

import asyncio
import json
import logging

from ctf_solver.events import EventBus, SolverEvent

logger = logging.getLogger(__name__)


async def start_hint_server(event_bus: EventBus, port: int = 0) -> tuple[asyncio.Server, int]:
    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            data = await reader.read(4096)
            raw = data.decode()
            _, _, body = raw.partition("\r\n\r\n")
            if not body:
                response = json.dumps({"status": "error", "message": "empty body"}).encode()
                writer.write(b"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nContent-Length: " + str(len(response)).encode() + b"\r\n\r\n" + response)
                await writer.drain()
                return
            body_json = json.loads(body)
            message = body_json.get("message", "")
            if message:
                event_bus.publish(SolverEvent(type="user_hint", solver_id="operator", data={"message": message}))
                response = json.dumps({"status": "ok", "queued": message[:200]}).encode()
            else:
                response = json.dumps({"status": "error", "message": "empty message"}).encode()
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: " + str(len(response)).encode() + b"\r\n\r\n" + response)
            await writer.drain()
        except Exception:
            logger.debug("hint_server error handling request", exc_info=True)
        finally:
            writer.close()

    server = await asyncio.start_server(handle_client, "127.0.0.1", port)
    actual_port = server.sockets[0].getsockname()[1]
    return server, actual_port
