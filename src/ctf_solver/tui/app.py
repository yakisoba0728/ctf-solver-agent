"""Textual TUI application — main entry point."""

from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Footer, Header, Static

from ctf_solver.events import EventBus, SolverEvent
from ctf_solver.tui.widgets.coordinator_view import CoordinatorView
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
        ("s", "toggle_status", "Status"),
        ("h", "focus_hint", "Hint"),
        ("c", "toggle_cost", "Cost"),
    ]

    def __init__(self, event_bus: EventBus, challenge_name: str = "Unknown", max_cost: float = 10.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.event_bus = event_bus
        self.challenge_name = challenge_name
        self.max_cost = max_cost
        self._event_queue = event_bus.subscribe()
        self._update_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-content"):
            with Vertical(id="solver-area"):
                yield Static(f"Challenge: {self.challenge_name}", id="title")
                yield SolverPanel()
            with Vertical(id="sidebar"):
                yield CoordinatorView()
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
        try:
            msg_log = self.query_one(MessageLog)
            msg_log.log_message(f"[{event.solver_id}] {event.type}: {str(event.data)[:100]}")

            if event.type == "cost_update":
                cost_bar = self.query_one(CostBar)
                cost_bar.update_cost(event.data.get("cost", 0.0), self.max_cost)

            if event.type == "solver_started":
                panel = self.query_one(SolverPanel)
                panel.add_solver(event.solver_id, event.data)

            if event.type == "solver_done":
                panel = self.query_one(SolverPanel)
                panel.mark_done(event.solver_id)

            if event.type == "tool_call":
                panel = self.query_one(SolverPanel)
                panel.update_solver(event.solver_id, last_action=event.data.get("tool", ""))

            if event.type == "cost_update":
                panel = self.query_one(SolverPanel)
                panel.update_solver(event.solver_id, cost=event.data.get("cost", 0.0))

            if event.type == "flag_found":
                panel = self.query_one(SolverPanel)
                panel.update_solver(event.solver_id, last_action=f"FLAG: {event.data}")

            if event.type == "coordinator_guidance":
                coord_view = self.query_one(CoordinatorView)
                guidance = event.data.get("guidance", str(event.data))
                coord_view.add_guidance(guidance)
        except Exception:
            pass

    def on_hint_input_bar_hint_submitted(self, event: HintInputBar.HintSubmitted) -> None:
        self.event_bus.publish(SolverEvent(type="user_hint", solver_id="operator", data={"message": event.text}))
        msg_log = self.query_one(MessageLog)
        msg_log.log_message(f"[operator] hint: {event.text}")

    def action_toggle_logs(self) -> None:
        from ctf_solver.tui.screens.logs import LogsScreen

        self.push_screen(LogsScreen(self.event_bus))

    def action_toggle_status(self) -> None:
        pass

    def action_focus_hint(self) -> None:
        self.query_one(HintInputBar).focus()

    def action_toggle_cost(self) -> None:
        pass
