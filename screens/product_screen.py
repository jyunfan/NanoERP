from __future__ import annotations

import sqlite3
import os

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Label, Input
from textual.binding import Binding
from textual.coordinate import Coordinate

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")

COLUMNS = [
    ("id", "ID"),
    ("car_number", "車次"),
    ("detailed_name", "詳細名稱"),
    ("short_name", "簡稱"),
    ("purchase_price", "進價"),
    ("sale_price", "售價"),
    ("safety_stock", "安存量"),
    ("return_unit", "銷退單位"),
    ("frequent", "常用"),
]


class ProductScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back_or_cancel", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
        Binding("f1", "add_row", "新增", show=True),
    ]

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title
        self._editing: Coordinate | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="product-title")
        yield DataTable(id="product-table", cursor_type="cell")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#product-table", DataTable)
        for col_key, col_label in COLUMNS:
            table.add_column(col_label, key=col_key)
        self._load_data()

    def _load_data(self) -> None:
        table = self.query_one("#product-table", DataTable)
        table.clear()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, car_number, detailed_name, short_name, "
            "purchase_price, sale_price, safety_stock, return_unit, frequent "
            "FROM product ORDER BY id"
        )
        for row in cur.fetchall():
            values = [v if v is not None else "" for v in row[:-1]]
            values.append("V" if row[-1] else "")
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

        if col_key == "frequent":
            self._toggle_frequent(coord, current_value)
            return

        self._editing = coord
        table = self.query_one("#product-table", DataTable)
        table.display = False

        edit_input = Input(
            value=str(current_value) if current_value else "",
            id="cell-editor",
        )
        self.mount(edit_input)
        edit_input.focus()

    def _toggle_frequent(self, coord: Coordinate, current_value: object) -> None:
        table = self.query_one("#product-table", DataTable)
        cell_key = table.coordinate_to_cell_key(coord)
        row_key = cell_key.row_key
        product_id = int(row_key.value)

        new_db_value = 0 if current_value == "V" else 1
        new_display = "" if current_value == "V" else "V"

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "UPDATE product SET frequent = ? WHERE id = ?",
            (new_db_value, product_id),
        )
        conn.commit()
        conn.close()

        table.update_cell(row_key, cell_key.column_key, new_display, update_width=True)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._editing is None:
            return
        self._finish_edit(self._editing, event.value)

    def _finish_edit(self, coord: Coordinate, new_value: str) -> None:
        table = self.query_one("#product-table", DataTable)
        cell_key = table.coordinate_to_cell_key(coord)
        row_key = cell_key.row_key
        col_key_str = cell_key.column_key.value

        product_id = int(row_key.value)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            f"UPDATE product SET {col_key_str} = ? WHERE id = ?",
            (new_value, product_id),
        )
        conn.commit()
        conn.close()

        table.update_cell(row_key, cell_key.column_key, new_value, update_width=True)
        self._dismiss_editor(table)

    def _dismiss_editor(self, table: DataTable) -> None:
        editor = self.query_one("#cell-editor")
        editor.remove()
        self._editing = None
        table.display = True
        table.focus()

    def action_go_back_or_cancel(self) -> None:
        if self._editing is not None:
            table = self.query_one("#product-table", DataTable)
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
            "INSERT INTO product (car_number, detailed_name, short_name, "
            "purchase_price, sale_price, safety_stock, return_unit, frequent) "
            "VALUES (NULL, '', '', NULL, NULL, NULL, '', 0)"
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()

        table = self.query_one("#product-table", DataTable)
        table.add_row(new_id, "", "", "", "", "", "", "", key=str(new_id))
        table.move_cursor(row=table.row_count - 1, column=0)
