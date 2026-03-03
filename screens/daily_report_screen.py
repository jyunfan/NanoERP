from __future__ import annotations

import sqlite3
import os

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Label, Select
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")

MARKETS = [
    (1, "其餘市場"),
    (2, "建國市場"),
    (3, "南部市場"),
]


class DailyReportScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back_or_toggle", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
    ]

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title
        self._market: int = 1
        self._customer_ids: list[int] = []
        self._selected_customer_id: int | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="report-title")
        with Horizontal(id="report-container"):
            with Vertical(id="report-left"):
                yield Select(
                    [(name, mid) for mid, name in MARKETS],
                    value=1,
                    id="market-select",
                    allow_blank=False,
                )
                yield DataTable(id="report-customer-list", cursor_type="row")
            yield DataTable(id="report-table", cursor_type="none")
        yield Footer()

    def on_mount(self) -> None:
        # Setup customer list columns
        cust_table = self.query_one("#report-customer-list", DataTable)
        cust_table.add_column("客戶名稱", key="cust_name")
        cust_table.add_column("訂單數目", key="order_count")

        # Setup report table columns
        report_table = self.query_one("#report-table", DataTable)
        report_table.add_column("項目名稱", key="product_name")
        report_table.add_column("數量", key="quantity")

        self._load_customers()
        self.watch(self.app, "work_date", self._on_work_date_changed, init=False)

    def _on_work_date_changed(self, new_value: str) -> None:
        self._load_customers()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "market-select":
            return
        if event.value is not Select.BLANK:
            self._market = event.value
            self._load_customers()

    def _load_customers(self) -> None:
        cust_table = self.query_one("#report-customer-list", DataTable)
        cust_table.clear()
        self._customer_ids = []
        self._selected_customer_id = None

        # Clear report table too
        report_table = self.query_one("#report-table", DataTable)
        report_table.clear()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT c.id, c.name, COUNT(o.id) as order_count "
            "FROM customer c "
            "LEFT JOIN order_table o ON o.customer_id = c.id AND o.order_date = ? "
            "WHERE c.market = ? "
            "GROUP BY c.id "
            "ORDER BY c.id",
            (self.app.work_date, self._market),
        )
        for row in cur.fetchall():
            cid, name, count = row
            self._customer_ids.append(cid)
            count_str = str(count) if count > 0 else ""
            cust_table.add_row(name or str(cid), count_str, key=f"cust_{cid}")
        conn.close()

    def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        if event.data_table.id != "report-customer-list":
            return
        if event.cursor_row < len(self._customer_ids):
            self._selected_customer_id = self._customer_ids[event.cursor_row]
            self._load_report()

    def _load_report(self) -> None:
        report_table = self.query_one("#report-table", DataTable)
        report_table.clear()

        if self._selected_customer_id is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT p.short_name, o.quantity "
            "FROM order_table o "
            "JOIN product p ON o.product_id = p.id "
            "WHERE o.customer_id = ? AND o.order_date = ? "
            "ORDER BY o.id",
            (self._selected_customer_id, self.app.work_date),
        )
        for row in cur.fetchall():
            name, qty = row
            report_table.add_row(
                name or "", str(qty) if qty is not None else ""
            )
        conn.close()

    def action_go_back_or_toggle(self) -> None:
        focused = self.app.focused
        report_table = self.query_one("#report-table", DataTable)
        if focused is report_table:
            self.query_one("#report-customer-list", DataTable).focus()
        else:
            self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen
        self.app.push_screen(QuitScreen())
