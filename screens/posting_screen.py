from __future__ import annotations

import os
import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label
from screens.ui4_common import format_work_date

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")


class PostingScreen(Screen):
    BINDINGS = [
        Binding("space", "execute_posting", "執行過帳", show=True),
        Binding("escape", "go_back", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
    ]

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title
        self._posting = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="posting-title")
        yield Label("過帳對象", id="posting-target")
        yield Label("完成率:", id="posting-progress")
        yield Label("", id="posting-summary")
        yield DataTable(id="posting-table", cursor_type="none")
        yield Label("==> 按 空鍵棒 : 即行過帳 ?    Esc : 取消", id="posting-help")
        yield Label(format_work_date(self.app.work_date), id="posting-work-date")
        yield Label(
            "0.回上系統  1.客戶退貨  2.執行過帳",
            id="posting-footer-options",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#posting-table", DataTable)
        table.add_column("品名", key="product_name")
        table.add_column("筆數", key="row_count")
        table.add_column("數量", key="quantity")
        self._load_summary()
        self.watch(self.app, "work_date", self._on_work_date_changed, init=False)

    def _on_work_date_changed(self, new_value: str) -> None:
        self.query_one("#posting-work-date", Label).update(format_work_date(new_value))
        self._load_summary()

    def _load_summary(self) -> None:
        table = self.query_one("#posting-table", DataTable)
        table.clear()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*), COUNT(DISTINCT customer_id), COALESCE(SUM(quantity), 0) "
            "FROM order_draft"
        )
        row_count, customer_count, total_qty = cur.fetchone()
        cur.execute(
            "SELECT p.short_name, COUNT(d.id), COALESCE(SUM(d.quantity), 0) "
            "FROM order_draft d "
            "JOIN product p ON p.id = d.product_id "
            "GROUP BY d.product_id "
            "ORDER BY d.product_id"
        )
        product_rows = cur.fetchall()
        conn.close()

        summary = (
            f"過帳日期: {self.app.work_date}    "
            f"暫存筆數: {row_count}    客戶數: {customer_count}    數量合計: {total_qty}"
        )
        self.query_one("#posting-target", Label).update(
            f"過帳對象: {customer_count} 位客戶 / {row_count} 筆暫存資料"
        )
        self.query_one("#posting-progress", Label).update("完成率: 尚未開始")
        self.query_one("#posting-summary", Label).update(summary)

        for name, count, qty in product_rows:
            table.add_row(name or "", str(count), str(qty))

    def action_execute_posting(self) -> None:
        if self._posting:
            return
        self._posting = True
        try:
            posted_count = self._post_drafts()
        except sqlite3.Error as exc:
            self.query_one("#posting-summary", Label).update(f"過帳失敗: {exc}")
        else:
            self._load_summary()
            self.query_one("#posting-progress", Label).update(
                "完成率: 100%" if posted_count else "完成率: 無資料"
            )
            self.query_one("#posting-summary", Label).update(
                f"過帳完成: {posted_count} 筆已儲存到 {self.app.work_date}"
            )
        finally:
            self._posting = False

    def _post_drafts(self) -> int:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT d.id, d.customer_id, d.product_id, d.quantity, d.is_return, "
                "       p.purchase_price, COALESCE(cp.sale_price, p.sale_price) "
                "FROM order_draft d "
                "JOIN product p ON p.id = d.product_id "
                "LEFT JOIN customer_product cp "
                "  ON cp.customer_id = d.customer_id AND cp.product_id = d.product_id "
                "ORDER BY d.id"
            )
            drafts = cur.fetchall()
            if not drafts:
                return 0

            cur.execute("BEGIN")
            cur.execute(
                "INSERT INTO posting_batch (work_date, status, note) "
                "VALUES (?, 'posted', ?)",
                (self.app.work_date, "customer order posting"),
            )
            batch_id = cur.lastrowid

            for (
                _draft_id,
                customer_id,
                product_id,
                quantity,
                is_return,
                purchase_price,
                sale_price,
            ) in drafts:
                cur.execute(
                    "INSERT INTO order_table ("
                    "customer_id, product_id, quantity, order_date, is_return, "
                    "posting_batch_id, purchase_price, sale_price, posted_at"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                    (
                        customer_id,
                        product_id,
                        quantity,
                        self.app.work_date,
                        int(is_return or 0),
                        batch_id,
                        purchase_price,
                        sale_price,
                    ),
                )

            cur.execute("DELETE FROM order_draft")
            conn.commit()
            return len(drafts)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen

        self.app.push_screen(QuitScreen())
