"""Hint input bar — user types hints to inject into solvers."""

from textual.message import Message
from textual.widgets import Input


class HintInputBar(Input):
    DEFAULT_CSS = """
    HintInputBar {
        height: 3;
        dock: bottom;
    }
    """

    class HintSubmitted(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def __init__(self) -> None:
        super().__init__(placeholder="Type a hint and press Enter...", id="hint-input")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip():
            self.post_message(self.HintSubmitted(event.value.strip()))
            self.value = ""
