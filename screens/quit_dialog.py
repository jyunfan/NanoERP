from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Vertical, Horizontal
from textual.binding import Binding


class QuitScreen(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss", "取消", show=True)]

    def compose(self) -> ComposeResult:
        with Vertical(id="quit-dialog"):
            yield Label("確定離開 NanoERP？", id="quit-message")
            with Horizontal(id="quit-buttons"):
                yield Button("是 (Yes)", id="quit-yes", variant="error")
                yield Button("否 (No)", id="quit-no", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit-yes":
            self.app.exit()
        else:
            self.dismiss()
