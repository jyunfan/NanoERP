from __future__ import annotations

import calendar
import os
import sqlite3
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label

from constants import CHECKOUT_CODES
from screens.ui4_common import format_number, format_work_date

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")

MARKETS = [
    (1, "其餘市場"),
    (2, "建國市場"),
    (3, "南部市場"),
]

CATEGORY_NAMES = {
    1: "其餘市場",
    2: "建國市場",
    3: "南部市場",
    4: "廠商",
}


class CheckoutScreen(Screen):
    BINDINGS = [
        Binding("left", "focus_previous_pane", "左欄", show=False),
        Binding("right", "focus_next_pane", "右欄", show=False),
        Binding("escape", "go_back_or_toggle", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
    ]

    def __init__(self, title: str, mode: str = "sales_detail") -> None:
        super().__init__()
        self._title = title
        self._mode = mode
        self._category: int = 1
        self._entity_ids: list[int] = []
        self._entity_names: dict[int, str] = {}
        self._entity_checkout_codes: dict[int, int] = {}
        self._date_rows: list[str] = []
        self._selected_entity_id: int | None = None
        self._selected_date: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="checkout-title")
        if self._mode == "business_total":
            yield DataTable(id="checkout-business-total-table", cursor_type="row")
        elif self._mode == "print":
            with Horizontal(id="checkout-container"):
                with Vertical(id="checkout-left"):
                    yield Label("", id="checkout-category-label")
                    yield DataTable(id="checkout-entity-list", cursor_type="row")
                yield DataTable(id="checkout-detail-table", cursor_type="none")
        else:
            with Horizontal(id="checkout-container"):
                yield DataTable(id="checkout-entity-list", cursor_type="row")
                yield DataTable(id="checkout-date-list", cursor_type="row")
                yield DataTable(id="checkout-detail-table", cursor_type="none")
        yield Label(format_work_date(self.app.work_date), id="checkout-work-date")
        yield Label(self._footer_text(), id="checkout-footer-options")
        yield Footer()

    def on_mount(self) -> None:
        if self._mode == "business_total":
            table = self.query_one("#checkout-business-total-table", DataTable)
            table.add_column("市場/類別", key="category")
            table.add_column("日期或區間", key="range")
            table.add_column("交易數", key="count")
            table.add_column("營業總額", key="amount")
            self._load_business_total()
        else:
            entity_table = self.query_one("#checkout-entity-list", DataTable)
            entity_table.add_column("客戶選擇", key="name")
            if self._mode == "print":
                entity_table.add_column("結帳", key="checkout")
            else:
                date_table = self.query_one("#checkout-date-list", DataTable)
                date_table.add_column("序", key="index")
                date_table.add_column("日期", key="date")
                date_table.add_column("交易額", key="amount")

            detail_table = self.query_one("#checkout-detail-table", DataTable)
            detail_table.add_column("品名", key="product_name")
            detail_table.add_column("數量", key="quantity")
            detail_table.add_column("金額", key="amount")

            self._load_entities()
            entity_table.focus()

        self.watch(self.app, "work_date", self._on_work_date_changed, init=False)

    def _on_work_date_changed(self, new_value: str) -> None:
        self.query_one("#checkout-work-date", Label).update(format_work_date(new_value))
        if self._mode == "business_total":
            self._load_business_total()
        else:
            self._load_entities()

    def on_key(self, event: Key) -> None:
        if event.character == "0":
            event.prevent_default()
            self.app.pop_screen()
            return
        if event.character in ("1", "2", "3", "4"):
            event.prevent_default()
            self._switch_category(int(event.character))

    def _switch_category(self, category: int) -> None:
        if self._category == category:
            return
        self._category = category
        if self._mode == "business_total":
            self._load_business_total()
        else:
            self._load_entities()

    def _load_entities(self) -> None:
        entity_table = self.query_one("#checkout-entity-list", DataTable)
        entity_table.clear()
        self._entity_ids = []
        self._entity_names = {}
        self._entity_checkout_codes = {}
        self._selected_entity_id = None
        self._selected_date = None

        if self._mode == "print":
            self.query_one("#checkout-category-label", Label).update(
                CATEGORY_NAMES[self._category]
            )
        else:
            self.query_one("#checkout-date-list", DataTable).clear()
        self.query_one("#checkout-detail-table", DataTable).clear()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        if self._category == 4:
            cur.execute("SELECT id, name FROM supplier ORDER BY id")
            for entity_id, name in cur.fetchall():
                display_name = name or str(entity_id)
                self._entity_ids.append(entity_id)
                self._entity_names[entity_id] = display_name
                if self._mode == "print":
                    entity_table.add_row(display_name, "", key=f"supplier_{entity_id}")
                else:
                    entity_table.add_row(display_name, key=f"supplier_{entity_id}")
        else:
            cur.execute(
                "SELECT id, name, checkout_code "
                "FROM customer WHERE market = ? "
                "ORDER BY id",
                (self._category,),
            )
            for entity_id, name, checkout_code in cur.fetchall():
                display_name = name or str(entity_id)
                code = checkout_code if checkout_code is not None else 0
                self._entity_ids.append(entity_id)
                self._entity_names[entity_id] = display_name
                self._entity_checkout_codes[entity_id] = code
                if self._mode == "print":
                    entity_table.add_row(
                        display_name,
                        CHECKOUT_CODES.get(code, str(code)),
                        key=f"customer_{entity_id}",
                    )
                else:
                    entity_table.add_row(display_name, key=f"customer_{entity_id}")

        conn.close()

    def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        if event.data_table.id == "checkout-entity-list":
            if event.cursor_row >= len(self._entity_ids):
                return
            self._selected_entity_id = self._entity_ids[event.cursor_row]
            if self._mode == "print":
                self._load_print_preview()
            else:
                self._load_dates()
            return

        if event.data_table.id == "checkout-date-list":
            if event.cursor_row >= len(self._date_rows):
                return
            self._selected_date = self._date_rows[event.cursor_row]
            self._load_detail()

    def _load_dates(self) -> None:
        date_table = self.query_one("#checkout-date-list", DataTable)
        date_table.clear()
        self._date_rows = []
        self._selected_date = None
        self.query_one("#checkout-detail-table", DataTable).clear()

        if self._selected_entity_id is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        if self._category == 4:
            cur.execute(
                "SELECT po.order_date, SUM(po.quantity * COALESCE(p.purchase_price, 0)) "
                "FROM purchase_order po "
                "JOIN product p ON p.id = po.product_id "
                "WHERE po.supplier_id = ? AND po.order_date IS NOT NULL "
                "GROUP BY po.order_date "
                "ORDER BY po.order_date DESC",
                (self._selected_entity_id,),
            )
        else:
            cur.execute(
                "SELECT o.order_date, SUM(o.quantity * COALESCE(o.sale_price, p.sale_price, 0)) "
                "FROM order_table o "
                "JOIN product p ON p.id = o.product_id "
                "WHERE o.customer_id = ? AND o.order_date IS NOT NULL "
                "GROUP BY o.order_date "
                "ORDER BY o.order_date DESC",
                (self._selected_entity_id,),
            )
        rows = cur.fetchall()
        conn.close()

        for index, (order_date, amount) in enumerate(rows, start=1):
            self._date_rows.append(order_date)
            date_table.add_row(
                f"{index}.",
                self._format_history_date(order_date),
                format_number(amount or 0),
                key=f"date_{index}",
            )

        if not rows:
            date_table.add_row("", "(無交易)", "")

    def _load_detail(self) -> None:
        detail_table = self.query_one("#checkout-detail-table", DataTable)
        detail_table.clear()

        if self._selected_entity_id is None or self._selected_date is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        if self._category == 4:
            cur.execute(
                "SELECT p.short_name, SUM(po.quantity), "
                "       SUM(po.quantity * COALESCE(p.purchase_price, 0)) "
                "FROM purchase_order po "
                "JOIN product p ON p.id = po.product_id "
                "WHERE po.supplier_id = ? AND po.order_date = ? "
                "GROUP BY po.product_id "
                "ORDER BY MIN(po.id)",
                (self._selected_entity_id, self._selected_date),
            )
        else:
            cur.execute(
                "SELECT p.short_name, SUM(o.quantity), "
                "       SUM(o.quantity * COALESCE(o.sale_price, p.sale_price, 0)) "
                "FROM order_table o "
                "JOIN product p ON p.id = o.product_id "
                "WHERE o.customer_id = ? AND o.order_date = ? "
                "GROUP BY o.product_id "
                "ORDER BY MIN(o.id)",
                (self._selected_entity_id, self._selected_date),
            )
        rows = cur.fetchall()
        conn.close()

        for product_name, quantity, amount in rows:
            detail_table.add_row(
                product_name or "",
                format_number(quantity),
                format_number(amount or 0),
            )
        detail_table.add_row("== 檔案結束 ==", "", "")

    def _load_business_total(self) -> None:
        table = self.query_one("#checkout-business-total-table", DataTable)
        table.clear()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for market_id, market_name in MARKETS:
            cur.execute(
                "SELECT COUNT(DISTINCT o.customer_id || '-' || o.order_date), "
                "       COALESCE(SUM(o.quantity * COALESCE(o.sale_price, p.sale_price, 0)), 0) "
                "FROM order_table o "
                "JOIN customer c ON c.id = o.customer_id "
                "JOIN product p ON p.id = o.product_id "
                "WHERE c.market = ? AND o.order_date = ?",
                (market_id, self.app.work_date),
            )
            transaction_count, amount = cur.fetchone()
            table.add_row(
                market_name,
                self.app.work_date,
                format_number(transaction_count or 0),
                format_number(amount or 0),
            )

        cur.execute(
            "SELECT COUNT(DISTINCT o.customer_id || '-' || o.order_date), "
            "       COALESCE(SUM(o.quantity * COALESCE(o.sale_price, p.sale_price, 0)), 0) "
            "FROM order_table o "
            "JOIN product p ON p.id = o.product_id "
            "WHERE o.order_date = ?",
            (self.app.work_date,),
        )
        transaction_count, amount = cur.fetchone()
        table.add_row(
            "合計",
            self.app.work_date,
            format_number(transaction_count or 0),
            format_number(amount or 0),
        )
        conn.close()

    def _load_print_preview(self) -> None:
        detail_table = self.query_one("#checkout-detail-table", DataTable)
        detail_table.clear()

        if self._selected_entity_id is None:
            return

        if self._category == 4:
            detail_table.add_row("廠商列印", "", "待確認")
            return

        checkout_code = self._entity_checkout_codes.get(self._selected_entity_id, 0)
        date_range = self._get_date_range(checkout_code, self.app.work_date)
        if date_range is None:
            detail_table.add_row("不印", "", "")
            return

        start_date, end_date = date_range

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT p.short_name, SUM(o.quantity), "
            "       SUM(o.quantity * COALESCE(o.sale_price, p.sale_price, 0)) "
            "FROM order_table o "
            "JOIN product p ON p.id = o.product_id "
            "WHERE o.customer_id = ? AND o.order_date >= ? AND o.order_date <= ? "
            "GROUP BY o.product_id "
            "ORDER BY MIN(o.id)",
            (self._selected_entity_id, start_date, end_date),
        )
        rows = cur.fetchall()
        conn.close()

        total = 0
        for product_name, quantity, amount in rows:
            amount = amount or 0
            total += amount
            detail_table.add_row(
                product_name or "",
                format_number(quantity),
                format_number(amount),
            )

        if rows:
            detail_table.add_row("", "合計", format_number(total))
        else:
            detail_table.add_row("(無結帳資料)", "", "")

    @staticmethod
    def _get_date_range(checkout_code: int, work_date_str: str) -> tuple[str, str] | None:
        if checkout_code == 0:
            return None

        wd = date.fromisoformat(work_date_str)
        if checkout_code in (1, 2, 3, 4):
            return work_date_str, work_date_str

        if checkout_code == 5:
            if wd.day <= 15:
                start = wd.replace(day=1)
                end = wd.replace(day=15)
            else:
                start = wd.replace(day=16)
                last_day = calendar.monthrange(wd.year, wd.month)[1]
                end = wd.replace(day=last_day)
            return start.isoformat(), end.isoformat()

        if checkout_code == 6:
            start = wd.replace(day=1)
            last_day = calendar.monthrange(wd.year, wd.month)[1]
            end = wd.replace(day=last_day)
            return start.isoformat(), end.isoformat()

        return work_date_str, work_date_str

    @staticmethod
    def _format_history_date(value: str) -> str:
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return value
        return parsed.strftime("%m-%d-%Y")

    def _footer_text(self) -> str:
        if self._mode == "business_total":
            return "0.回上系統  1.其餘市場  2.建國市場  3.南部市場  4.廠商"
        if self._mode == "print":
            return "0.回上系統  1.其餘市場  2.建國市場  3.南部市場  4.廠商"
        return "0.回上系統  1.其餘市場  2.建國市場  3.南部市場  4.廠商"

    def action_focus_next_pane(self) -> None:
        focused = self.app.focused
        if self._mode == "sales_detail":
            if focused is self.query_one("#checkout-entity-list", DataTable):
                self.query_one("#checkout-date-list", DataTable).focus()
            elif focused is self.query_one("#checkout-date-list", DataTable):
                self.query_one("#checkout-detail-table", DataTable).focus()
        elif self._mode == "print":
            if focused is self.query_one("#checkout-entity-list", DataTable):
                self.query_one("#checkout-detail-table", DataTable).focus()

    def action_focus_previous_pane(self) -> None:
        focused = self.app.focused
        if self._mode == "sales_detail":
            if focused is self.query_one("#checkout-detail-table", DataTable):
                self.query_one("#checkout-date-list", DataTable).focus()
            elif focused is self.query_one("#checkout-date-list", DataTable):
                self.query_one("#checkout-entity-list", DataTable).focus()
        elif self._mode == "print":
            if focused is self.query_one("#checkout-detail-table", DataTable):
                self.query_one("#checkout-entity-list", DataTable).focus()

    def action_go_back_or_toggle(self) -> None:
        if self._mode == "sales_detail":
            focused = self.app.focused
            if focused is self.query_one("#checkout-detail-table", DataTable):
                self.query_one("#checkout-date-list", DataTable).focus()
                return
            if focused is self.query_one("#checkout-date-list", DataTable):
                self.query_one("#checkout-entity-list", DataTable).focus()
                return
        elif self._mode == "print":
            focused = self.app.focused
            if focused is self.query_one("#checkout-detail-table", DataTable):
                self.query_one("#checkout-entity-list", DataTable).focus()
                return
        self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen

        self.app.push_screen(QuitScreen())
