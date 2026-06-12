"""Lightweight HTTP hint server — accepts JSON hints and publishes to EventBus."""

from __future__ import annotations

import asyncio
import json
import logging

from ctf_solver.events import EventBus, SolverEvent

logger = logging.getLogger(__name__)

MAX_HEADER_BYTES = 8192
MAX_BODY_BYTES = 65536


async def start_hint_server(event_bus: EventBus, port: int = 0) -> tuple[asyncio.Server, int]:
    async def _json_response(writer: asyncio.StreamWriter, status: int, data: dict) -> None:
        body = json.dumps(data).encode()
        writer.write(
            f"HTTP/1.1 {status} {'OK' if status == 200 else 'Bad Request' if status == 400 else 'Not Found'}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"\r\n".encode() + body
        )
        await writer.drain()

    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            header_data = await reader.readuntil(b"\r\n\r\n")
            if len(header_data) > MAX_HEADER_BYTES:
                await _json_response(writer, 400, {"status": "error", "message": "headers too large"})
                return

            header_part, _, initial_body = header_data.partition(b"\r\n\r\n")
            header_text = header_part.decode("iso-8859-1")
            request_line = header_text.split("\r\n")[0]
            parts = request_line.split(" ", 2)
            method = parts[0] if len(parts) >= 1 else ""
            path = parts[1] if len(parts) >= 2 else ""

            if method != "POST" or path != "/hint":
                await _json_response(writer, 404, {"status": "error", "message": "not found"})
                return

            content_length = 0
            for line in header_text.split("\r\n")[1:]:
                if line.lower().startswith("content-length:"):
                    try:
                        content_length = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                    break

            if content_length > MAX_BODY_BYTES:
                await _json_response(writer, 400, {"status": "error", "message": "body too large"})
                return

            body_data = initial_body
            remaining = content_length - len(body_data)
            if remaining > 0:
                body_data += await asyncio.wait_for(reader.readexactly(remaining), timeout=5)

            if not body_data:
                await _json_response(writer, 400, {"status": "error", "message": "empty body"})
                return

            try:
                body_json = json.loads(body_data)
            except json.JSONDecodeError:
                await _json_response(writer, 400, {"status": "error", "message": "invalid JSON"})
                return

            message = body_json.get("message", "")
            if message:
                event_bus.publish(SolverEvent(type="user_hint", solver_id="operator", data={"message": message}))
                await _json_response(writer, 200, {"status": "ok", "queued": message[:200]})
            else:
                await _json_response(writer, 400, {"status": "error", "message": "empty message"})
        except Exception:
            logger.debug("hint_server error handling request", exc_info=True)
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", port)
    actual_port = server.sockets[0].getsockname()[1]
    return server, actual_port
