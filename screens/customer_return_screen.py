from __future__ import annotations

import os
import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Label

from screens.ui4_common import MARKETS, format_number, format_work_date

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")


class CustomerReturnScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back_or_cancel", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
        Binding("tab", "toggle_focus", "切換", show=True),
        Binding("enter", "edit_return_quantity", "輸入退量", show=True),
    ]

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title
        self._market = 1
        self._customer_ids: list[int] = []
        self._product_ids: list[int] = []
        self._customer_names: dict[int, str] = {}
        self._product_names: dict[int, str] = {}
        self._selected_customer_id: int | None = None
        self._selected_product_id: int | None = None
        self._editing = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="customer-return-title")
        with Horizontal(id="customer-return-container"):
            yield DataTable(id="return-customer-list", cursor_type="row")
            yield DataTable(id="return-product-list", cursor_type="row")
            with Vertical(id="return-detail-pane"):
                yield DataTable(id="return-detail-table", cursor_type="none")
                yield Label("", id="return-status")
        yield Label(format_work_date(self.app.work_date), id="customer-return-work-date")
        yield Label(
            "0.回上系統  1.其餘市場  2.建國市場  3.南部市場",
            id="customer-return-footer-options",
        )
        yield Footer()

    def on_mount(self) -> None:
        customer_table = self.query_one("#return-customer-list", DataTable)
        customer_table.add_column("客戶選擇", key="name")
        customer_table.add_column("退貨", key="count")

        product_table = self.query_one("#return-product-list", DataTable)
        product_table.add_column("品名選擇", key="name")

        detail_table = self.query_one("#return-detail-table", DataTable)
        detail_table.add_column("客戶", key="customer")
        detail_table.add_column("品名", key="product")
        detail_table.add_column("退價", key="price")
        detail_table.add_column("退量", key="quantity")
        detail_table.add_column("金額", key="amount")

        self._load_customers()
        self._load_products()
        self._load_return_details()
        self._update_status()
        customer_table.focus()
        self.watch(self.app, "work_date", self._on_work_date_changed, init=False)

    def _on_work_date_changed(self, new_value: str) -> None:
        self.query_one("#customer-return-work-date", Label).update(
            format_work_date(new_value)
        )

    def on_key(self, event: Key) -> None:
        if self._editing:
            return
        if event.character in ("1", "2", "3"):
            event.prevent_default()
            self._switch_market(int(event.character))

    def _switch_market(self, market: int) -> None:
        self._market = market
        self._selected_customer_id = None
        self._selected_product_id = None
        self._load_customers()
        self._load_return_details()
        self._update_status()
        self.query_one("#return-customer-list", DataTable).focus()

    def _load_customers(self) -> None:
        table = self.query_one("#return-customer-list", DataTable)
        table.clear()
        self._customer_ids = []
        self._customer_names = {}

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT c.id, c.name, COUNT(d.id) "
            "FROM customer c "
            "LEFT JOIN order_draft d "
            "  ON d.customer_id = c.id AND d.is_return = 1 "
            "WHERE c.market = ? "
            "GROUP BY c.id "
            "ORDER BY c.id",
            (self._market,),
        )
        for customer_id, name, return_count in cur.fetchall():
            display_name = name or str(customer_id)
            self._customer_ids.append(customer_id)
            self._customer_names[customer_id] = display_name
            table.add_row(
                display_name,
                str(return_count) if return_count else "",
                key=f"customer_{customer_id}",
            )
        conn.close()
        if self._selected_customer_id not in self._customer_ids:
            self._selected_customer_id = self._customer_ids[0] if self._customer_ids else None

    def _load_products(self) -> None:
        table = self.query_one("#return-product-list", DataTable)
        table.clear()
        self._product_ids = []
        self._product_names = {}

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, short_name FROM product ORDER BY id")
        for product_id, name in cur.fetchall():
            display_name = name or str(product_id)
            self._product_ids.append(product_id)
            self._product_names[product_id] = display_name
            table.add_row(display_name, key=f"product_{product_id}")
        conn.close()
        if self._selected_product_id not in self._product_ids:
            self._selected_product_id = self._product_ids[0] if self._product_ids else None

    def _load_return_details(self) -> None:
        table = self.query_one("#return-detail-table", DataTable)
        table.clear()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT c.name, p.short_name, "
            "       COALESCE(cp.sale_price, p.sale_price), d.quantity "
            "FROM order_draft d "
            "JOIN customer c ON c.id = d.customer_id "
            "JOIN product p ON p.id = d.product_id "
            "LEFT JOIN customer_product cp "
            "  ON cp.customer_id = d.customer_id AND cp.product_id = d.product_id "
            "WHERE c.market = ? AND d.is_return = 1 "
            "ORDER BY c.id, p.id",
            (self._market,),
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            table.add_row("== 檔案結束 ==", "", "", "", "")
            return

        for customer_name, product_name, price, quantity in rows:
            amount = (price or 0) * (quantity or 0)
            table.add_row(
                customer_name or "",
                product_name or "",
                format_number(price),
                format_number(quantity),
                format_number(amount),
            )
        table.add_row("== 檔案結束 ==", "", "", "", "")

    def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        if event.data_table.id == "return-customer-list":
            if event.cursor_row < len(self._customer_ids):
                self._selected_customer_id = self._customer_ids[event.cursor_row]
                self._update_status()
            return
        if event.data_table.id == "return-product-list":
            if event.cursor_row < len(self._product_ids):
                self._selected_product_id = self._product_ids[event.cursor_row]
                self._update_status()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "return-customer-list":
            self.query_one("#return-product-list", DataTable).focus()
            return
        if event.data_table.id == "return-product-list":
            self.action_edit_return_quantity()

    def action_toggle_focus(self) -> None:
        focused = self.app.focused
        customer_table = self.query_one("#return-customer-list", DataTable)
        product_table = self.query_one("#return-product-list", DataTable)
        detail_table = self.query_one("#return-detail-table", DataTable)
        if focused is customer_table:
            product_table.focus()
        elif focused is product_table:
            detail_table.focus()
        else:
            customer_table.focus()

    def action_edit_return_quantity(self) -> None:
        if self._editing:
            return
        if self._selected_customer_id is None or self._selected_product_id is None:
            return

        self._editing = True
        current_quantity = self._current_quantity()
        editor = Input(
            value=format_number(current_quantity),
            placeholder="輸入退量，空白或 0 表示刪除",
            id="return-quantity-editor",
        )
        self.mount(editor)
        editor.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "return-quantity-editor":
            return
        self._finish_edit(event.value)

    def _finish_edit(self, value: str) -> None:
        if self._selected_customer_id is None or self._selected_product_id is None:
            self._dismiss_editor()
            return

        stripped = value.strip()
        try:
            quantity = int(stripped) if stripped else 0
        except ValueError:
            self._dismiss_editor()
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        if quantity > 0:
            cur.execute(
                "INSERT INTO order_draft "
                "(customer_id, product_id, quantity, is_return) "
                "VALUES (?, ?, ?, 1) "
                "ON CONFLICT(customer_id, product_id, is_return) "
                "DO UPDATE SET quantity = excluded.quantity, "
                "updated_at = CURRENT_TIMESTAMP",
                (self._selected_customer_id, self._selected_product_id, quantity),
            )
        else:
            cur.execute(
                "DELETE FROM order_draft "
                "WHERE customer_id = ? AND product_id = ? AND is_return = 1",
                (self._selected_customer_id, self._selected_product_id),
            )
        conn.commit()
        conn.close()

        self._dismiss_editor()
        self._load_customers()
        self._load_return_details()
        self._update_status()
        self.query_one("#return-product-list", DataTable).focus()

    def _dismiss_editor(self) -> None:
        try:
            self.query_one("#return-quantity-editor").remove()
        except Exception:
            pass
        self._editing = False

    def _current_quantity(self) -> int:
        if self._selected_customer_id is None or self._selected_product_id is None:
            return 0
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT quantity FROM order_draft "
            "WHERE customer_id = ? AND product_id = ? AND is_return = 1",
            (self._selected_customer_id, self._selected_product_id),
        )
        row = cur.fetchone()
        conn.close()
        return int(row[0]) if row else 0

    def _current_price(self) -> int | float:
        if self._selected_customer_id is None or self._selected_product_id is None:
            return 0
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(cp.sale_price, p.sale_price, 0) "
            "FROM product p "
            "LEFT JOIN customer_product cp "
            "  ON cp.customer_id = ? AND cp.product_id = p.id "
            "WHERE p.id = ?",
            (self._selected_customer_id, self._selected_product_id),
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row else 0

    def _update_status(self) -> None:
        customer_name = ""
        product_name = ""
        if self._selected_customer_id is not None:
            customer_name = self._customer_names.get(self._selected_customer_id, "")
        if self._selected_product_id is not None:
            product_name = self._product_names.get(self._selected_product_id, "")
        price = self._current_price()
        quantity = self._current_quantity()
        amount = (price or 0) * (quantity or 0)
        self.query_one("#return-status", Label).update(
            "客戶: "
            f"{customer_name}    品名: {product_name}    "
            f"退價: {format_number(price)}    退量: {format_number(quantity)}    "
            f"金額: {format_number(amount)}"
        )

    def action_go_back_or_cancel(self) -> None:
        if self._editing:
            self._dismiss_editor()
            return
        self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen

        self.app.push_screen(QuitScreen())
