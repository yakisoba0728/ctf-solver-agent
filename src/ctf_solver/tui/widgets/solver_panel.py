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
        self._solvers: dict[str, dict] = {}

    def add_solver(self, solver_id: str, data: dict) -> None:
        self._solvers[solver_id] = {"status": "running", **data}
        self._update_display()

    def mark_done(self, solver_id: str) -> None:
        if solver_id in self._solvers:
            self._solvers[solver_id]["status"] = "done"
            self._update_display()

    def _update_display(self) -> None:
        lines = []
        for sid, info in self._solvers.items():
            status = info.get("status", "?")
            icon = "\u25cf" if status == "running" else "\u25cb"
            lines.append(f"{icon} {sid} [{status}]")
        self.update("\n".join(lines) if lines else "No solvers running yet.")
