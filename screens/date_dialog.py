from __future__ import annotations

from datetime import date

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Input
from textual.containers import Vertical
from textual.binding import Binding


class DateDialog(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "取消", show=True),
    ]

    def __init__(self, current_date: str) -> None:
        super().__init__()
        self._current_date = current_date

    def compose(self) -> ComposeResult:
        with Vertical(id="date-dialog"):
            yield Label("請輸入工作日期 (YYYY-MM-DD):", id="date-prompt")
            yield Input(value=self._current_date, id="date-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        try:
            date.fromisoformat(value)
        except ValueError:
            self.query_one("#date-prompt", Label).update(
                "日期格式錯誤，請重新輸入 (YYYY-MM-DD):"
            )
            return
        self.app.work_date = value
        self.app.pop_screen()

    def action_cancel(self) -> None:
        self.app.pop_screen()
