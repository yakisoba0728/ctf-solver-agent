"""Textual TUI application — main entry point."""

from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Footer, Header, Static

from ctf_solver.events import EventBus, SolverEvent
from ctf_solver.tui.widgets.cost_bar import CostBar
from ctf_solver.tui.widgets.input_bar import HintInputBar
from ctf_solver.tui.widgets.message_log import MessageLog
from ctf_solver.tui.widgets.solver_panel import SolverPanel


class CTFApp(App):
    """CTF Solver Agent TUI Dashboard."""

    CSS = """
    Screen { layout: vertical; }
    #main-content { layout: horizontal; height: 1fr; }
    #solver-area { width: 2fr; }
    #sidebar { width: 1fr; layout: vertical; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("l", "toggle_logs", "Logs"),
    ]

    def __init__(self, event_bus: EventBus, challenge_name: str = "Unknown", **kwargs) -> None:
        super().__init__(**kwargs)
        self.event_bus = event_bus
        self.challenge_name = challenge_name
        self._event_queue = event_bus.subscribe()
        self._update_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-content"):
            with Vertical(id="solver-area"):
                yield Static(f"Challenge: {self.challenge_name}", id="title")
                yield SolverPanel()
            with Vertical(id="sidebar"):
                yield MessageLog()
                yield CostBar()
                yield HintInputBar()
        yield Footer()

    async def on_mount(self) -> None:
        self._update_task = asyncio.create_task(self._event_loop())

    async def _event_loop(self) -> None:
        while True:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                self._handle_event(event)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    def _handle_event(self, event: SolverEvent) -> None:
        msg_log = self.query_one(MessageLog)
        msg_log.log_message(f"[{event.solver_id}] {event.type}: {str(event.data)[:100]}")

    def action_toggle_logs(self) -> None:
        pass
