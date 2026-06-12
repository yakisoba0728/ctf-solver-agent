from textual.widgets import Static


class CoordinatorView(Static):
    DEFAULT_CSS = """
    CoordinatorView {
        height: auto;
        max-height: 8;
        padding: 1;
        border: solid magenta;
        overflow-y: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__("Coordinator: idle")
        self._messages: list[str] = []

    def add_guidance(self, message: str) -> None:
        self._messages.append(message)
        if len(self._messages) > 20:
            self._messages = self._messages[-20:]
        self.update("Coordinator guidance:\n" + "\n".join(self._messages[-5:]))

    def set_status(self, status: str) -> None:
        if not self._messages:
            self.update(f"Coordinator: {status}")
