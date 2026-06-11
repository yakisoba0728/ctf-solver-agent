"""Cost progress bar widget."""

from textual.widgets import Static


class CostBar(Static):
    DEFAULT_CSS = """
    CostBar {
        height: 3;
        padding: 1;
        border: solid yellow;
    }
    """

    def __init__(self) -> None:
        super().__init__("Cost: $0.00")

    def update_cost(self, cost: float, max_cost: float) -> None:
        pct = min(100, cost / max_cost * 100) if max_cost > 0 else 0
        bar_len = 30
        filled = int(pct / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        self.update(f"Cost: ${cost:.2f} / ${max_cost:.2f}\n[{bar}] {pct:.0f}%")
