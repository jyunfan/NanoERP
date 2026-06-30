from __future__ import annotations

import os
import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Label

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")

COLUMNS = [
    ("id", "ID"),
    ("name", "名稱"),
    ("phone1", "電話1"),
    ("phone2", "電話2"),
]


class SupplierScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back_or_cancel", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
        Binding("f1", "add_row", "新增", show=True),
        Binding("alt+f9", "delete_row", "刪除", show=True),
    ]

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title
        self._editing: Coordinate | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="supplier-title")
        yield DataTable(id="supplier-table", cursor_type="cell")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#supplier-table", DataTable)
        for col_key, col_label in COLUMNS:
            table.add_column(col_label, key=col_key)
        self._load_data()

    def _load_data(self) -> None:
        table = self.query_one("#supplier-table", DataTable)
        table.clear()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, name, phone1, phone2 FROM supplier ORDER BY id")
        for row in cur.fetchall():
            table.add_row(
                *(value if value is not None else "" for value in row),
                key=str(row[0]),
            )
        conn.close()

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        if self._editing is not None:
            return
        self._start_edit(event.coordinate, event.value)

    def _start_edit(self, coord: Coordinate, current_value: object) -> None:
        col_key, _ = COLUMNS[coord.column]
        if col_key == "id":
            return

        self._editing = coord
        table = self.query_one("#supplier-table", DataTable)
        table.display = False

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

    def _finish_edit(self, coord: Coordinate, new_value: str) -> None:
        table = self.query_one("#supplier-table", DataTable)
        cell_key = table.coordinate_to_cell_key(coord)
        supplier_id = int(cell_key.row_key.value)
        col_key = cell_key.column_key.value

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(f"UPDATE supplier SET {col_key} = ? WHERE id = ?", (new_value, supplier_id))
        conn.commit()
        conn.close()

        table.update_cell(cell_key.row_key, cell_key.column_key, new_value, update_width=True)
        self._dismiss_editor(table)

    def _dismiss_editor(self, table: DataTable) -> None:
        editor = self.query_one("#cell-editor")
        editor.remove()
        self._editing = None
        table.display = True
        table.focus()

    def action_go_back_or_cancel(self) -> None:
        if self._editing is not None:
            table = self.query_one("#supplier-table", DataTable)
            self._dismiss_editor(table)
        else:
            self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen

        self.app.push_screen(QuitScreen())

    def action_add_row(self) -> None:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO supplier (name, phone1, phone2) VALUES ('', '', '')")
        new_id = cur.lastrowid
        conn.commit()
        conn.close()

        table = self.query_one("#supplier-table", DataTable)
        table.add_row(new_id, "", "", "", key=str(new_id))
        table.move_cursor(row=table.row_count - 1, column=0)

    def action_delete_row(self) -> None:
        if self._editing is not None:
            return
        table = self.query_one("#supplier-table", DataTable)
        if table.row_count == 0:
            return

        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        supplier_id = int(row_key.value)

        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()
        cur.execute("DELETE FROM supplier_freq_product WHERE supplier_id = ?", (supplier_id,))
        cur.execute("DELETE FROM purchase_order WHERE supplier_id = ?", (supplier_id,))
        cur.execute("DELETE FROM supplier WHERE id = ?", (supplier_id,))
        conn.commit()
        conn.close()

        self._load_data()
        if table.row_count > 0:
            table.move_cursor(row=min(table.cursor_row, table.row_count - 1), column=0)
