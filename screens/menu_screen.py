from __future__ import annotations
from textual.app import ComposeResult
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Header, Footer, OptionList, Label
from textual.widgets.option_list import Option
from textual.binding import Binding
from menu_data import MenuNode
from screens.ui4_common import format_work_date


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
        yield Label(self._node.title or self._node.label, id="menu-title")
        options = [
            Option(child.label, id=child.id)
            for child in self._node.children
        ]
        yield OptionList(*options, id="menu-list")
        if self._node.footer is not None:
            yield Label(format_work_date(self.app.work_date), id="menu-work-date")
            yield Label(self._footer_text(), id="menu-footer-options")
        yield Footer()

    def on_mount(self) -> None:
        if self._node.footer is not None:
            self.watch(self.app, "work_date", self._on_work_date_changed, init=False)

    def _on_work_date_changed(self, new_value: str) -> None:
        self.query_one("#menu-work-date", Label).update(format_work_date(new_value))

    def _footer_text(self) -> str:
        if self._node.footer is not None:
            return self._node.footer
        labels = [child.label.replace(". ", ".") for child in self._node.children]
        return "  ".join(labels)

    def on_key(self, event: Key) -> None:
        if not event.character or not event.character.isdigit():
            return
        key_num = event.character
        for index, child in enumerate(self._node.children):
            if child.label.startswith(f"{key_num}."):
                event.prevent_default()
                self.query_one(OptionList).highlighted = index
                self._navigate_to(child)
                return

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
        self._navigate_to(child)

    def _navigate_to(self, child: MenuNode) -> None:
        selected_id = child.id
        if child.is_back:
            self.app.pop_screen()
        elif self._node.id == "root" and selected_id == "1":
            from screens.customer_screen import CustomerScreen

            self.app.push_screen(CustomerScreen(market=1, title="1. 其餘市場"))
        elif self._node.id == "3" and selected_id == "customer_orders":
            from screens.order_screen import MARKET_NAMES, OrderScreen

            self.app.push_screen(
                OrderScreen(market=1, title=MARKET_NAMES[1])
            )
        elif child.children:
            self.app.push_screen(MenuScreen(child))
        elif self._node.id == "1" and selected_id in ("1", "2", "3"):
            from screens.customer_screen import CustomerScreen
            self.app.push_screen(
                CustomerScreen(market=int(selected_id), title=child.label)
            )
        elif self._node.id == "1" and selected_id == "supplier":
            from screens.supplier_screen import SupplierScreen
            self.app.push_screen(SupplierScreen(title=child.label))
        elif self._node.id == "root" and selected_id == "2":
            from screens.product_screen import ProductScreen
            self.app.push_screen(ProductScreen(title=child.label))
        elif self._node.id == "3" and selected_id == "purchase":
            from screens.purchase_screen import PurchaseScreen
            self.app.push_screen(PurchaseScreen(title=child.label))
        elif self._node.id == "posting" and selected_id == "customer_return":
            from screens.customer_return_screen import CustomerReturnScreen
            self.app.push_screen(
                CustomerReturnScreen(title="4.1.1 過帳與日報表\n客戶退貨")
            )
        elif self._node.id == "posting" and selected_id == "execute_posting":
            from screens.posting_screen import PostingScreen
            self.app.push_screen(
                PostingScreen(title="4.1.2 過帳與日報表\n執行過帳")
            )
        elif self._node.id == "daily_reports" and selected_id == "shipping":
            from screens.shipping_report_screen import ShippingReportScreen
            self.app.push_screen(ShippingReportScreen(title=child.label))
        elif self._node.id == "daily_account" and selected_id == "print_settings":
            from screens.print_settings_screen import PrintSettingsScreen
            self.app.push_screen(
                PrintSettingsScreen(title="4.2.1.1 過帳與日報表\n列印設定")
            )
        elif self._node.id == "daily_account" and selected_id == "execute_daily_account":
            from screens.daily_report_screen import DailyReportScreen
            self.app.push_screen(DailyReportScreen(title="4.2.1 過帳與日報表\n日帳單"))
        elif self._node.id == "account_lookup" and selected_id == "sales_detail":
            from screens.checkout_screen import CheckoutScreen

            self.app.push_screen(
                CheckoutScreen(
                    title="5.1.1 結帳與期報表\n進銷明細",
                    mode="sales_detail",
                )
            )
        elif self._node.id == "account_lookup" and selected_id == "business_total":
            from screens.checkout_screen import CheckoutScreen

            self.app.push_screen(
                CheckoutScreen(
                    title="5.1.2 結帳與期報表\n營業總額",
                    mode="business_total",
                )
            )
        elif self._node.id == "5" and selected_id == "period_print":
            from screens.checkout_screen import CheckoutScreen

            self.app.push_screen(
                CheckoutScreen(
                    title="5.2 結帳與期報表\n列印",
                    mode="print",
                )
            )
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
