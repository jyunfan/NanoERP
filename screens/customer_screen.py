from __future__ import annotations

import sqlite3
import os

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Label, Input, Select
from textual.binding import Binding
from textual.coordinate import Coordinate

from constants import CHECKOUT_CODES, CHECKOUT_CODE_OPTIONS
from screens.ui4_common import format_work_date

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")

COLUMNS = [
    ("id", "ID"),
    ("car_number", "車次"),
    ("name", "名稱"),
    ("checkout_code", "結帳代碼"),
    ("phone1", "電話1"),
    ("phone2", "電話2"),
]

MARKET_NAMES = {
    1: "1. 其餘市場",
    2: "2. 建國市場",
    3: "3. 南部市場",
}


class CustomerScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back_or_cancel", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
        Binding("f1", "add_row", "新增", show=True),
        Binding("f3", "move_row", "移位", show=False),
        Binding("f5", "print_detail", "明細列印", show=False),
        Binding("f6", "print_phone", "電話列印", show=False),
        Binding("f9", "delete_row", "刪除", show=True),
    ]

    def __init__(self, market: int, title: str) -> None:
        super().__init__()
        self._market = market
        self._title = title
        self._editing: Coordinate | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="customer-title")
        with Horizontal(id="customer-container"):
            yield DataTable(id="customer-table", cursor_type="cell")
            with Vertical(id="customer-help-panel"):
                yield Label(
                    "結帳代碼\n"
                    "0: 不印\n"
                    "1: 出貨\n"
                    "2: 日\n"
                    "3: 週\n"
                    "4: 旬\n"
                    "5: 半月\n"
                    "6: 月",
                    id="customer-checkout-help",
                )
                yield Label(
                    "功能鍵\n"
                    "F1: 增加\n"
                    "F3: 移位\n"
                    "F5: 明細列印\n"
                    "F6: 電話列印\n"
                    "F9: 刪除\n"
                    "0: 更改\n"
                    "Esc: 回跳",
                    id="customer-key-help",
                )
        yield Label(format_work_date(self.app.work_date), id="customer-work-date")
        yield Label(
            "0.回主系統  1.其餘市場  2.建國市場  3.南部市場  4.廠商",
            id="customer-footer-options",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#customer-table", DataTable)
        for col_key, col_label in COLUMNS:
            table.add_column(col_label, key=col_key)
        self._load_data()
        self.watch(self.app, "work_date", self._on_work_date_changed, init=False)

    def _on_work_date_changed(self, new_value: str) -> None:
        self.query_one("#customer-work-date", Label).update(format_work_date(new_value))

    def _load_data(self) -> None:
        table = self.query_one("#customer-table", DataTable)
        table.clear()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, car_number, name, checkout_code, phone1, phone2 "
            "FROM customer WHERE market = ? ORDER BY id",
            (self._market,),
        )
        for row in cur.fetchall():
            values = []
            for i, v in enumerate(row):
                col_key = COLUMNS[i][0]
                if col_key == "checkout_code" and v is not None:
                    values.append(CHECKOUT_CODES.get(v, str(v)))
                else:
                    values.append(v if v is not None else "")
            table.add_row(*values, key=str(row[0]))
        conn.close()

    def on_data_table_cell_selected(
        self, event: DataTable.CellSelected
    ) -> None:
        if self._editing is not None:
            return
        self._start_edit(event.coordinate, event.value)

    def _start_edit(self, coord: Coordinate, current_value: object) -> None:
        col_key, _ = COLUMNS[coord.column]
        if col_key == "id":
            return

        self._editing = coord
        table = self.query_one("#customer-table", DataTable)
        table.display = False

        if col_key == "checkout_code":
            select = Select(
                CHECKOUT_CODE_OPTIONS,
                prompt="選擇結帳代碼",
                id="cell-editor",
            )
            self.mount(select)
            select.focus()
        else:
            edit_input = Input(
                value=str(current_value) if current_value else "",
                id="cell-editor",
            )
            self.mount(edit_input)
            edit_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._editing is None:
            return
        self._finish_edit(self._editing, event.value)

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._editing is None:
            return
        if event.value is not Select.BLANK:
            self._finish_edit(self._editing, str(event.value))

    def _finish_edit(self, coord: Coordinate, new_value: str) -> None:
        table = self.query_one("#customer-table", DataTable)
        cell_key = table.coordinate_to_cell_key(coord)
        row_key = cell_key.row_key
        col_key_str = cell_key.column_key.value

        # Update DB
        customer_id = int(row_key.value)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            f"UPDATE customer SET {col_key_str} = ? WHERE id = ?",
            (new_value, customer_id),
        )
        conn.commit()
        conn.close()

        # Update table display
        if col_key_str == "checkout_code":
            display_value = CHECKOUT_CODES.get(int(new_value), new_value)
        else:
            display_value = new_value
        table.update_cell(row_key, cell_key.column_key, display_value, update_width=True)

        self._dismiss_editor(table)

    def _dismiss_editor(self, table: DataTable) -> None:
        editor = self.query_one("#cell-editor")
        editor.remove()
        self._editing = None
        table.display = True
        table.focus()

    def action_go_back_or_cancel(self) -> None:
        if self._editing is not None:
            table = self.query_one("#customer-table", DataTable)
            self._dismiss_editor(table)
        else:
            self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen
        self.app.push_screen(QuitScreen())

    def action_add_row(self) -> None:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO customer (car_number, name, checkout_code, phone1, phone2, market) "
            "VALUES (NULL, '', NULL, '', '', ?)",
            (self._market,),
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()

        table = self.query_one("#customer-table", DataTable)
        table.add_row(new_id, "", "", "", "", "", key=str(new_id))
        table.move_cursor(row=table.row_count - 1, column=0)

    def action_move_row(self) -> None:
        self._notify_placeholder("移位")

    def action_print_detail(self) -> None:
        self._notify_placeholder("明細列印")

    def action_print_phone(self) -> None:
        self._notify_placeholder("電話列印")

    def _notify_placeholder(self, feature: str) -> None:
        self.app.notify(f"{feature}尚未實作", severity="warning")

    def on_key(self, event: Key) -> None:
        if self._editing is not None:
            return
        if event.character == "0":
            event.prevent_default()
            self._go_to_root_menu()
            return
        if event.character in ("1", "2", "3"):
            event.prevent_default()
            self._switch_market(int(event.character))
            return
        if event.character == "4":
            event.prevent_default()
            from screens.supplier_screen import SupplierScreen

            self.app.switch_screen(SupplierScreen(title="4. 廠商"))
            return

    def _switch_market(self, market: int) -> None:
        self._market = market
        self._title = MARKET_NAMES[market]
        self.query_one("#customer-title", Label).update(self._title)
        self._load_data()

    def _go_to_root_menu(self) -> None:
        while len(self.app.screen_stack) > 2:
            self.app.pop_screen()

    def action_delete_row(self) -> None:
        if self._editing is not None:
            return
        table = self.query_one("#customer-table", DataTable)
        if table.row_count == 0:
            return

        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        customer_id = int(row_key.value)

        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()
        cur.execute("DELETE FROM customer_freq_product WHERE customer_id = ?", (customer_id,))
        cur.execute("DELETE FROM customer_product WHERE customer_id = ?", (customer_id,))
        cur.execute("DELETE FROM order_draft WHERE customer_id = ?", (customer_id,))
        cur.execute("DELETE FROM order_table WHERE customer_id = ?", (customer_id,))
        cur.execute("DELETE FROM customer WHERE id = ?", (customer_id,))
        conn.commit()
        conn.close()

        self._load_data()
        if table.row_count > 0:
            table.move_cursor(row=min(table.cursor_row, table.row_count - 1), column=0)
