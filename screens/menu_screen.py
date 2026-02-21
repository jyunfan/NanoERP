from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, OptionList, Label
from textual.widgets.option_list import Option
from textual.binding import Binding
from menu_data import MenuNode


class MenuScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
    ]

    def __init__(self, node: MenuNode, is_root: bool = False) -> None:
        super().__init__()
        self._node = node
        self._is_root = is_root

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._node.label, id="menu-title")
        options = [
            Option(child.label, id=child.id)
            for child in self._node.children
        ]
        yield OptionList(*options, id="menu-list")
        yield Footer()

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        event.stop()
        selected_id = event.option.id
        child = next(
            (c for c in self._node.children if c.id == selected_id), None
        )
        if child is None:
            return

        if child.is_back:
            self.app.pop_screen()
        elif child.children:
            self.app.push_screen(MenuScreen(child))
        elif self._node.id == "1" and selected_id in ("1", "2", "3"):
            from screens.customer_screen import CustomerScreen
            self.app.push_screen(
                CustomerScreen(market=int(selected_id), title=child.label)
            )
        elif self._node.id == "root" and selected_id == "2":
            from screens.product_screen import ProductScreen
            self.app.push_screen(ProductScreen(title=child.label))
        else:
            from screens.placeholder import PlaceholderScreen
            self.app.push_screen(PlaceholderScreen(child.label))

    def action_go_back(self) -> None:
        if self._is_root:
            from screens.quit_dialog import QuitScreen
            self.app.push_screen(QuitScreen())
        else:
            self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen
        self.app.push_screen(QuitScreen())
