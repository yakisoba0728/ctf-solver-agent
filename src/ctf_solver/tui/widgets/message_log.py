"""Message log widget — scrolling feed of solver events."""

from textual.widgets import Static


class MessageLog(Static):
    DEFAULT_CSS = """
    MessageLog {
        height: 1fr;
        padding: 1;
        border: solid blue;
        overflow-y: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__("Messages will appear here...")
        self._messages: list[str] = []

    def log_message(self, message: str) -> None:
        self._messages.append(message)
        if len(self._messages) > 100:
            self._messages = self._messages[-100:]
        self.update("\n".join(self._messages[-20:]))
