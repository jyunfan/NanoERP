from datetime import date

from textual.app import App
from textual.binding import Binding
from textual.reactive import reactive

from menu_data import MENU_TREE
from screens.menu_screen import MenuScreen


class NanoERPApp(App):
    CSS_PATH = "nanoerp.tcss"
    TITLE = "NanoERP"
    SUB_TITLE = ""

    BINDINGS = [
        Binding("f10", "change_work_date", "工作日期", show=True),
    ]

    work_date: reactive[str] = reactive(lambda: date.today().isoformat())

    def on_mount(self) -> None:
        self.sub_title = f"工作日期: {self.work_date}"
        self.push_screen(MenuScreen(MENU_TREE, is_root=True))

    def watch_work_date(self, new_value: str) -> None:
        self.sub_title = f"工作日期: {new_value}"

    def action_change_work_date(self) -> None:
        from screens.date_dialog import DateDialog
        self.push_screen(DateDialog(self.work_date))


if __name__ == "__main__":
    NanoERPApp().run()
