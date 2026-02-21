from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label
from textual.binding import Binding


class PlaceholderScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
    ]

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(
            f"{self._title}\n\n[dim]（尚未實作 / Not yet implemented）[/dim]",
            id="placeholder-message",
        )
        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen
        self.app.push_screen(QuitScreen())
