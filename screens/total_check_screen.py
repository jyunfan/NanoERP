from __future__ import annotations

import os
import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")


class TotalCheckScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
    ]

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="total-check-title")
        yield DataTable(id="total-check-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#total-check-table", DataTable)
        table.add_column("其餘市場", key="market_1")
        table.add_column("建國市場", key="market_2")
        table.add_column("南部市場", key="market_3")
        table.add_column("品名", key="product_name")
        table.add_column("總數量", key="total")
        self._load_data()

    def _load_data(self) -> None:
        table = self.query_one("#total-check-table", DataTable)
        table.clear()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT p.id, p.short_name, "
            "       COALESCE(SUM(CASE WHEN c.market = 1 THEN d.quantity ELSE 0 END), 0), "
            "       COALESCE(SUM(CASE WHEN c.market = 2 THEN d.quantity ELSE 0 END), 0), "
            "       COALESCE(SUM(CASE WHEN c.market = 3 THEN d.quantity ELSE 0 END), 0), "
            "       COALESCE(SUM(d.quantity), 0) "
            "FROM product p "
            "LEFT JOIN order_draft d ON d.product_id = p.id AND d.is_return = 0 "
            "LEFT JOIN customer c ON c.id = d.customer_id "
            "GROUP BY p.id "
            "ORDER BY p.id"
        )
        for product_id, name, market_1, market_2, market_3, total in cur.fetchall():
            table.add_row(
                str(market_1 or 0),
                str(market_2 or 0),
                str(market_3 or 0),
                name or str(product_id),
                str(total or 0),
                key=str(product_id),
            )
        conn.close()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen

        self.app.push_screen(QuitScreen())
