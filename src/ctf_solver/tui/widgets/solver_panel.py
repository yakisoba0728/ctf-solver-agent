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

    def update_solver(self, solver_id: str, steps: int | None = None, cost: float | None = None, last_action: str | None = None) -> None:
        if solver_id in self._solvers:
            if steps is not None:
                self._solvers[solver_id]["steps"] = steps
            if cost is not None:
                self._solvers[solver_id]["cost"] = cost
            if last_action is not None:
                self._solvers[solver_id]["last_action"] = last_action
            self._update_display()

    def _update_display(self) -> None:
        lines = []
        for sid, info in self._solvers.items():
            status = info.get("status", "?")
            icon = "\u25cf" if status == "running" else ("\u2691" if status == "winner" else "\u25cb")
            parts = [f"{icon} {sid}"]
            if "steps" in info:
                parts.append(f"{info['steps']}steps")
            if "cost" in info:
                parts.append(f"${info['cost']:.2f}")
            if "last_action" in info:
                parts.append(f"last:{info['last_action'][:20]}")
            lines.append(" ".join(parts))
        self.update("\n".join(lines) if lines else "No solvers running yet.")
