"""Solver status panel widget."""

from textual.widgets import Static


class SolverPanel(Static):
    DEFAULT_CSS = """
    SolverPanel {
        height: auto;
        padding: 1;
        border: solid green;
    }
    """

    def __init__(self) -> None:
        super().__init__("No solvers running yet.")
