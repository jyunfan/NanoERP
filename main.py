from textual.app import App
from menu_data import MENU_TREE
from screens.menu_screen import MenuScreen


class NanoERPApp(App):
    CSS_PATH = "nanoerp.tcss"
    TITLE = "NanoERP"
    SUB_TITLE = "Terminal ERP System"

    def on_mount(self) -> None:
        self.push_screen(MenuScreen(MENU_TREE, is_root=True))


if __name__ == "__main__":
    NanoERPApp().run()
