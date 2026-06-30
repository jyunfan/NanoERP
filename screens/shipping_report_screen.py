from __future__ import annotations

import os
import sqlite3
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Select

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")

MARKETS = [
    (1, "其餘市場"),
    (2, "建國市場"),
    (3, "南部市場"),
]

MARKET_NAMES = dict(MARKETS)


class ShippingReportScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back_or_toggle", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
    ]

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title
        self._market: int = 1
        self._customer_ids: list[int] = []
        self._customer_names: dict[int, str] = {}
        self._selected_customer_id: int | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="shipping-title")
        with Horizontal(id="shipping-container"):
            with Vertical(id="shipping-left"):
                yield Select(
                    [(name, mid) for mid, name in MARKETS],
                    value=1,
                    id="shipping-market-select",
                    allow_blank=False,
                )
                yield DataTable(id="shipping-customer-list", cursor_type="row")
            with Vertical(id="shipping-document"):
                yield Label("", id="shipping-document-title")
                yield DataTable(id="shipping-table", cursor_type="none")
        yield Footer()

    def on_mount(self) -> None:
        cust_table = self.query_one("#shipping-customer-list", DataTable)
        cust_table.add_column("客戶名稱", key="cust_name")
        cust_table.add_column("筆數", key="order_count")

        shipping_table = self.query_one("#shipping-table", DataTable)
        shipping_table.add_column("品名", key="product_name")
        shipping_table.add_column("數量", key="quantity")

        self._load_customers()
        cust_table.focus()
        self.watch(self.app, "work_date", self._on_work_date_changed, init=False)

    def _on_work_date_changed(self, new_value: str) -> None:
        self._load_customers()

    def on_key(self, event: Key) -> None:
        if event.character in ("1", "2", "3"):
            event.prevent_default()
            self._switch_market(int(event.character))

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "shipping-market-select":
            return
        if event.value is not Select.BLANK:
            self._switch_market(int(event.value))

    def _switch_market(self, market: int) -> None:
        if self._market == market:
            return
        self._market = market
        select = self.query_one("#shipping-market-select", Select)
        if select.value != market:
            select.value = market
        self._load_customers()

    def _load_customers(self) -> None:
        cust_table = self.query_one("#shipping-customer-list", DataTable)
        cust_table.clear()
        self._customer_ids = []
        self._customer_names = {}
        self._selected_customer_id = None

        self._set_document_title()
        self.query_one("#shipping-table", DataTable).clear()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT c.id, c.name, COUNT(o.id) AS order_count "
            "FROM customer c "
            "LEFT JOIN order_table o "
            "  ON o.customer_id = c.id "
            " AND o.order_date = ? "
            " AND COALESCE(o.is_return, 0) = 0 "
            "WHERE c.market = ? "
            "GROUP BY c.id "
            "ORDER BY c.id",
            (self.app.work_date, self._market),
        )
        for customer_id, name, order_count in cur.fetchall():
            display_name = name or str(customer_id)
            self._customer_ids.append(customer_id)
            self._customer_names[customer_id] = display_name
            count_str = str(order_count) if order_count else ""
            cust_table.add_row(display_name, count_str, key=f"cust_{customer_id}")
        conn.close()

    def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        if event.data_table.id != "shipping-customer-list":
            return
        if event.cursor_row < len(self._customer_ids):
            self._selected_customer_id = self._customer_ids[event.cursor_row]
            self._load_shipping_document()

    def _load_shipping_document(self) -> None:
        shipping_table = self.query_one("#shipping-table", DataTable)
        shipping_table.clear()
        self._set_document_title()

        if self._selected_customer_id is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT p.short_name, SUM(o.quantity) AS quantity "
            "FROM order_table o "
            "JOIN product p ON p.id = o.product_id "
            "WHERE o.customer_id = ? "
            "  AND o.order_date = ? "
            "  AND COALESCE(o.is_return, 0) = 0 "
            "GROUP BY o.product_id "
            "ORDER BY MIN(o.id)",
            (self._selected_customer_id, self.app.work_date),
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            shipping_table.add_row("(無出貨資料)", "")
            return

        for product_name, quantity in rows:
            shipping_table.add_row(product_name or "", self._format_quantity(quantity))

    def _set_document_title(self) -> None:
        customer_name = ""
        if self._selected_customer_id is not None:
            customer_name = self._customer_names.get(self._selected_customer_id, "")
        if not customer_name:
            customer_name = "未選擇客戶"

        self.query_one("#shipping-document-title", Label).update(
            f"{customer_name}    {self._format_work_date()}    {MARKET_NAMES[self._market]}"
        )

    def _format_work_date(self) -> str:
        try:
            work_date = date.fromisoformat(self.app.work_date)
        except ValueError:
            return self.app.work_date
        return f"{work_date.month}-{work_date.day}"

    @staticmethod
    def _format_quantity(quantity: object) -> str:
        if quantity is None:
            return ""
        if isinstance(quantity, float) and quantity.is_integer():
            return str(int(quantity))
        return str(quantity)

    def action_go_back_or_toggle(self) -> None:
        focused = self.app.focused
        shipping_table = self.query_one("#shipping-table", DataTable)
        if focused is shipping_table:
            self.query_one("#shipping-customer-list", DataTable).focus()
        else:
            self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen

        self.app.push_screen(QuitScreen())
