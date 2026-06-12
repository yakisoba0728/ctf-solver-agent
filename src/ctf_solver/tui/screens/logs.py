import asyncio

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header

from ctf_solver.tui.widgets.message_log import MessageLog


class LogsScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, event_bus, **kwargs):
        super().__init__(**kwargs)
        self.event_bus = event_bus
        self._log_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield MessageLog(id="logs-detail")
        yield Footer()

    async def on_mount(self) -> None:
        self._log_task = asyncio.create_task(self._event_loop())

    async def _event_loop(self) -> None:
        queue = self.event_bus.subscribe()
        log = self.query_one(MessageLog)
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                log.log_message(f"[{event.solver_id}] {event.type}: {str(event.data)[:200]}")
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    def on_unmount(self) -> None:
        if hasattr(self, "_log_task") and self._log_task:
            self._log_task.cancel()
