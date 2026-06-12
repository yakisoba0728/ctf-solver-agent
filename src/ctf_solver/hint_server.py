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
            header_data = b""
            while b"\r\n\r\n" not in header_data:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                header_data += chunk

            header_text = header_data.decode("utf-8", errors="replace")
            headers_end = header_text.find("\r\n\r\n")
            if headers_end < 0:
                writer.close()
                return

            body_start_raw = header_data[headers_end + 4:]
            content_length = 0
            for line in header_text[:headers_end].split("\r\n"):
                if line.lower().startswith("content-length:"):
                    try:
                        content_length = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                    break

            body_data = body_start_raw
            remaining = content_length - len(body_data)
            if remaining > 0:
                body_data += await reader.readexactly(remaining)

            body = body_data.decode("utf-8", errors="replace")

            if not body:
                response = json.dumps({"status": "error", "message": "empty body"}).encode()
                writer.write(b"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nContent-Length: " + str(len(response)).encode() + b"\r\n\r\n" + response)
                await writer.drain()
                return

            try:
                body_json = json.loads(body)
            except json.JSONDecodeError:
                response = json.dumps({"status": "error", "message": "invalid JSON"}).encode()
                writer.write(b"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nContent-Length: " + str(len(response)).encode() + b"\r\n\r\n" + response)
                await writer.drain()
                return

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
            await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", port)
    actual_port = server.sockets[0].getsockname()[1]
    return server, actual_port
