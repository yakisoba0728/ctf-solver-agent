"""Tests for hint server."""

import asyncio
import json

from ctf_solver.events import EventBus
from ctf_solver.hint_server import start_hint_server


async def test_hint_server_receives_hint():
    bus = EventBus()
    queue = bus.subscribe()
    server, port = await start_hint_server(bus, port=0)

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        body = json.dumps({"message": "test hint"})
        request = (
            f"POST /hint HTTP/1.1\r\nHost: localhost\r\n"
            f"Content-Length: {len(body)}\r\n\r\n{body}"
        )
        writer.write(request.encode())
        await writer.drain()

        response = await asyncio.wait_for(reader.read(4096), timeout=2.0)
        assert b"200" in response

        event = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert event.type == "user_hint"
        assert event.data["message"] == "test hint"
    finally:
        server.close()
        await server.wait_closed()
        writer.close()
