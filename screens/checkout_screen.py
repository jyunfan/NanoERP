from __future__ import annotations

import calendar
import sqlite3
import os
from datetime import date

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Label, Select
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

from constants import CHECKOUT_CODES

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")

MARKETS = [
    (1, "其餘市場"),
    (2, "建國市場"),
    (3, "南部市場"),
]


class CheckoutScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back_or_toggle", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
    ]

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title
        self._market: int = 1
        self._customer_ids: list[int] = []
        self._customer_checkout_codes: dict[int, int] = {}
        self._selected_customer_id: int | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="checkout-title")
        with Horizontal(id="checkout-container"):
            with Vertical(id="checkout-left"):
                yield Select(
                    [(name, mid) for mid, name in MARKETS],
                    value=1,
                    id="checkout-market-select",
                    allow_blank=False,
                )
                yield DataTable(id="checkout-customer-list", cursor_type="row")
            yield DataTable(id="checkout-table", cursor_type="none")
        yield Footer()

    def on_mount(self) -> None:
        cust_table = self.query_one("#checkout-customer-list", DataTable)
        cust_table.add_column("客戶名稱", key="cust_name")
        cust_table.add_column("結帳方式", key="checkout_type")

        report_table = self.query_one("#checkout-table", DataTable)
        report_table.add_column("項目名稱", key="product_name")
        report_table.add_column("數量", key="quantity")
        report_table.add_column("價格", key="price")

        self._load_customers()
        self.watch(self.app, "work_date", self._on_work_date_changed, init=False)

    def _on_work_date_changed(self, new_value: str) -> None:
        self._load_customers()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "checkout-market-select":
            return
        if event.value is not Select.BLANK:
            self._market = event.value
            self._load_customers()

    def _load_customers(self) -> None:
        cust_table = self.query_one("#checkout-customer-list", DataTable)
        cust_table.clear()
        self._customer_ids = []
        self._customer_checkout_codes = {}
        self._selected_customer_id = None

        report_table = self.query_one("#checkout-table", DataTable)
        report_table.clear()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, checkout_code "
            "FROM customer WHERE market = ? "
            "ORDER BY id",
            (self._market,),
        )
        for row in cur.fetchall():
            cid, name, checkout_code = row
            self._customer_ids.append(cid)
            cc = checkout_code if checkout_code is not None else 0
            self._customer_checkout_codes[cid] = cc
            checkout_label = CHECKOUT_CODES.get(cc, str(cc))
            cust_table.add_row(
                name or str(cid), checkout_label, key=f"cust_{cid}"
            )
        conn.close()

    @staticmethod
    def _get_date_range(checkout_code: int, work_date_str: str) -> tuple[str, str] | None:
        """Return (start_date, end_date) or None if checkout_code is 0."""
        if checkout_code == 0:
            return None

        wd = date.fromisoformat(work_date_str)

        if checkout_code in (1, 2, 3, 4):
            # 出貨(1), 日(2): work_date only
            # 週(3), 旬(4): undefined, fallback to work_date
            return (work_date_str, work_date_str)

        if checkout_code == 5:
            # 半月: 1~15 or 16~month end
            if wd.day <= 15:
                start = wd.replace(day=1)
                end = wd.replace(day=15)
            else:
                start = wd.replace(day=16)
                last_day = calendar.monthrange(wd.year, wd.month)[1]
                end = wd.replace(day=last_day)
            return (start.isoformat(), end.isoformat())

        if checkout_code == 6:
            # 月: 1~month end
            start = wd.replace(day=1)
            last_day = calendar.monthrange(wd.year, wd.month)[1]
            end = wd.replace(day=last_day)
            return (start.isoformat(), end.isoformat())

        return (work_date_str, work_date_str)

    def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        if event.data_table.id != "checkout-customer-list":
            return
        if event.cursor_row < len(self._customer_ids):
            self._selected_customer_id = self._customer_ids[event.cursor_row]
            self._load_report()

    def _load_report(self) -> None:
        report_table = self.query_one("#checkout-table", DataTable)
        report_table.clear()

        if self._selected_customer_id is None:
            return

        checkout_code = self._customer_checkout_codes.get(
            self._selected_customer_id, 0
        )
        date_range = self._get_date_range(checkout_code, self.app.work_date)

        if date_range is None:
            report_table.add_row("(不印)", "", "")
            return

        start_date, end_date = date_range

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT p.short_name, SUM(o.quantity), p.sale_price "
            "FROM order_table o "
            "JOIN product p ON o.product_id = p.id "
            "WHERE o.customer_id = ? AND o.order_date >= ? AND o.order_date <= ? "
            "GROUP BY o.product_id "
            "ORDER BY MIN(o.id)",
            (self._selected_customer_id, start_date, end_date),
        )

        total = 0
        for row in cur.fetchall():
            name, qty, sale_price = row
            qty = qty if qty is not None else 0
            price = sale_price if sale_price is not None else 0
            line_total = qty * price
            total += line_total
            report_table.add_row(name or "", str(qty), str(line_total))
        conn.close()

        report_table.add_row("", "合計", str(total))

    def action_go_back_or_toggle(self) -> None:
        focused = self.app.focused
        report_table = self.query_one("#checkout-table", DataTable)
        if focused is report_table:
            self.query_one("#checkout-customer-list", DataTable).focus()
        else:
            self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen
        self.app.push_screen(QuitScreen())
