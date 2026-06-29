from __future__ import annotations

import sqlite3
import os

from textual.app import ComposeResult
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Label, Input, OptionList
from textual.widgets.option_list import Option
from textual.containers import Horizontal
from textual.binding import Binding
from textual.coordinate import Coordinate

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")

COLS_PER_GROUP = 3  # product name + buy quantity + return quantity
NUM_GROUPS = 2  # 2 groups per row

# Column definitions: (key, label) repeated for each group
COLUMNS: list[tuple[str, str]] = []
for i in range(NUM_GROUPS):
    COLUMNS.append((f"prod_{i}", "名稱"))
    COLUMNS.append((f"buy_{i}", "進量"))
    COLUMNS.append((f"ret_{i}", "退量"))


class PurchaseScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back_or_cancel", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
        Binding("f1", "add_product", "新增產品", show=True),
        Binding("delete", "delete_product", "刪除產品", show=True),
    ]

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title
        self._editing: Coordinate | None = None
        self._editing_is_return: bool = False
        self._selected_supplier_id: int | None = None
        self._supplier_ids: list[int] = []  # row index -> supplier id
        # Maps (row_index, group_index) -> product_id from supplier_freq_product
        self._cell_product_map: dict[tuple[int, int], int] = {}
        # All products: id -> short_name
        self._product_names: dict[int, str] = {}
        # All products list for add dialog
        self._all_products: list[tuple[str, int]] = []  # (name, id)
        # Product IDs shown in current add dialog
        self._add_option_ids: list[int] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="purchase-title")
        with Horizontal(id="purchase-container"):
            yield DataTable(id="supplier-list", cursor_type="row")
            yield DataTable(id="purchase-table", cursor_type="cell")
        yield Footer()

    def on_mount(self) -> None:
        self._load_products()
        self._load_suppliers()
        self.watch(self.app, "work_date", self._on_work_date_changed, init=False)
        table = self.query_one("#purchase-table", DataTable)
        for col_key, col_label in COLUMNS:
            table.add_column(col_label, key=col_key)

    def _on_work_date_changed(self, new_value: str) -> None:
        self._load_suppliers()

    def _load_products(self) -> None:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, short_name FROM product ORDER BY id")
        self._product_names = {}
        self._all_products = []
        for row in cur.fetchall():
            pid, name = row
            self._product_names[pid] = name or ""
            self._all_products.append((name or str(pid), pid))
        conn.close()

    def _load_suppliers(self) -> None:
        sup_table = self.query_one("#supplier-list", DataTable)
        sup_table.clear(columns=True)
        sup_table.add_column("廠商名稱", key="sup_name")
        sup_table.add_column("訂單數目", key="order_count")
        self._supplier_ids = []
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT s.id, s.name, COUNT(p.id) as order_count "
            "FROM supplier s "
            "LEFT JOIN purchase_order p ON p.supplier_id = s.id AND p.order_date = ? "
            "GROUP BY s.id "
            "ORDER BY s.id",
            (self.app.work_date,),
        )
        for row in cur.fetchall():
            sid, name, count = row
            self._supplier_ids.append(sid)
            count_str = str(count) if count > 0 else ""
            sup_table.add_row(name or str(sid), count_str, key=f"sup_{sid}")
        conn.close()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "supplier-list":
            return
        if event.cursor_row < len(self._supplier_ids):
            self._selected_supplier_id = self._supplier_ids[event.cursor_row]
            self._load_purchases()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "supplier-list":
            return
        table = self.query_one("#purchase-table", DataTable)
        table.focus()
        if table.row_count > 0:
            table.move_cursor(row=0, column=0)

    def _load_purchases(self) -> None:
        table = self.query_one("#purchase-table", DataTable)
        table.clear()
        self._cell_product_map.clear()

        if self._selected_supplier_id is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Get supplier's frequent products + any extra purchases not in freq list
        cur.execute(
            "SELECT product_id, buy_qty, ret_qty FROM ("
            "  SELECT sfp.product_id,"
            "    (SELECT quantity FROM purchase_order WHERE supplier_id = sfp.supplier_id"
            "       AND product_id = sfp.product_id AND order_date = ? AND is_return = 0) as buy_qty,"
            "    (SELECT quantity FROM purchase_order WHERE supplier_id = sfp.supplier_id"
            "       AND product_id = sfp.product_id AND order_date = ? AND is_return = 1) as ret_qty"
            "  FROM supplier_freq_product sfp"
            "  WHERE sfp.supplier_id = ?"
            "  UNION"
            "  SELECT p.product_id,"
            "    (SELECT quantity FROM purchase_order WHERE supplier_id = p.supplier_id"
            "       AND product_id = p.product_id AND order_date = ? AND is_return = 0) as buy_qty,"
            "    (SELECT quantity FROM purchase_order WHERE supplier_id = p.supplier_id"
            "       AND product_id = p.product_id AND order_date = ? AND is_return = 1) as ret_qty"
            "  FROM purchase_order p"
            "  WHERE p.supplier_id = ? AND p.order_date = ?"
            "    AND p.product_id NOT IN ("
            "      SELECT product_id FROM supplier_freq_product WHERE supplier_id = ?"
            "    )"
            ") ORDER BY product_id",
            (
                self.app.work_date, self.app.work_date, self._selected_supplier_id,
                self.app.work_date, self.app.work_date,
                self._selected_supplier_id, self.app.work_date, self._selected_supplier_id,
            ),
        )
        items = cur.fetchall()
        conn.close()

        # Fill rows, 2 products per row
        row_idx = 0
        for i in range(0, len(items), NUM_GROUPS):
            row_values = []
            for g in range(NUM_GROUPS):
                if i + g < len(items):
                    pid, buy_qty, ret_qty = items[i + g]
                    self._cell_product_map[(row_idx, g)] = pid
                    row_values.append(self._product_names.get(pid, str(pid)))
                    row_values.append(str(buy_qty) if buy_qty else "")
                    row_values.append(str(ret_qty) if ret_qty else "")
                else:
                    row_values.append("")
                    row_values.append("")
                    row_values.append("")
            table.add_row(*row_values, key=f"row_{row_idx}")
            row_idx += 1

    def _refresh_supplier_order_count(self) -> None:
        if self._selected_supplier_id is None:
            return
        sup_table = self.query_one("#supplier-list", DataTable)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(id) FROM purchase_order "
            "WHERE supplier_id = ? AND order_date = ?",
            (self._selected_supplier_id, self.app.work_date),
        )
        count = cur.fetchone()[0]
        conn.close()
        count_str = str(count) if count > 0 else ""
        row_key = f"sup_{self._selected_supplier_id}"
        sup_table.update_cell(row_key, "order_count", count_str, update_width=True)

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        if event.data_table.id != "purchase-table":
            return
        if self._editing is not None:
            return
        if self._selected_supplier_id is None:
            return
        col_key = COLUMNS[event.coordinate.column][0]
        # Only buy/ret cells are editable (not product name)
        if not (col_key.startswith("buy_") or col_key.startswith("ret_")):
            return
        # Only edit if there's a product in this group
        group_idx = event.coordinate.column // COLS_PER_GROUP
        if (event.coordinate.row, group_idx) not in self._cell_product_map:
            return
        is_return = col_key.startswith("ret_")
        self._start_edit_qty(event.coordinate, event.value, is_return)

    def _start_edit_qty(self, coord: Coordinate, current_value: object, is_return: bool) -> None:
        self._editing = coord
        self._editing_is_return = is_return
        table = self.query_one("#purchase-table", DataTable)
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
        self._finish_edit_qty(self._editing, event.value, self._editing_is_return)

    def _finish_edit_qty(self, coord: Coordinate, new_value: str, is_return: bool) -> None:
        table = self.query_one("#purchase-table", DataTable)
        row_idx = coord.row
        group_idx = coord.column // COLS_PER_GROUP
        product_id = self._cell_product_map.get((row_idx, group_idx))

        if product_id is not None and self._selected_supplier_id is not None:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            qty = int(new_value) if new_value.strip() else 0
            if qty > 0:
                cur.execute(
                    "SELECT id FROM purchase_order "
                    "WHERE supplier_id = ? AND product_id = ? AND order_date = ? AND is_return = ?",
                    (self._selected_supplier_id, product_id, self.app.work_date, int(is_return)),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        "UPDATE purchase_order SET quantity = ? WHERE id = ?",
                        (qty, existing[0]),
                    )
                else:
                    cur.execute(
                        "INSERT INTO purchase_order (supplier_id, product_id, quantity, is_return, order_date) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (self._selected_supplier_id, product_id, qty, int(is_return), self.app.work_date),
                    )
            else:
                cur.execute(
                    "DELETE FROM purchase_order "
                    "WHERE supplier_id = ? AND product_id = ? AND order_date = ? AND is_return = ?",
                    (self._selected_supplier_id, product_id, self.app.work_date, int(is_return)),
                )
                new_value = ""
            conn.commit()
            conn.close()

        cell_key = table.coordinate_to_cell_key(coord)
        table.update_cell(cell_key.row_key, cell_key.column_key, new_value, update_width=True)
        self._refresh_supplier_order_count()
        self._dismiss_editor(table)

    def _dismiss_editor(self, table: DataTable) -> None:
        editor = self.query_one("#cell-editor")
        editor.remove()
        self._editing = None
        self._editing_is_return = False
        table.display = True
        table.focus()

    def _focus_is_on_table(self) -> bool:
        focused = self.app.focused
        table = self.query_one("#purchase-table", DataTable)
        return focused is table

    def action_go_back_or_cancel(self) -> None:
        if self._editing is not None:
            table = self.query_one("#purchase-table", DataTable)
            self._dismiss_editor(table)
        elif self._focus_is_on_table():
            self.query_one("#supplier-list", DataTable).focus()
        else:
            self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen
        self.app.push_screen(QuitScreen())

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if self._editing is not None:
            return
        product_id = self._add_option_ids[event.option_index]
        self._finish_add_product(product_id)

    def _finish_add_product(self, product_id: int) -> None:
        if self._selected_supplier_id is None:
            return
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO supplier_freq_product (supplier_id, product_id) VALUES (?, ?)",
            (self._selected_supplier_id, product_id),
        )
        conn.commit()
        conn.close()
        self._dismiss_add_dialog()
        self._load_purchases()

    def _dismiss_add_dialog(self) -> None:
        try:
            editor = self.query_one("#add-product-dialog")
            editor.remove()
        except Exception:
            pass
        table = self.query_one("#purchase-table", DataTable)
        table.display = True
        table.focus()

    def action_add_product(self) -> None:
        if self._selected_supplier_id is None:
            return
        if self._editing is not None:
            return

        existing_pids = set(self._cell_product_map.values())
        available = [(name, pid) for name, pid in self._all_products if pid not in existing_pids]
        if not available:
            return

        self._add_option_ids = [pid for _name, pid in available]
        table = self.query_one("#purchase-table", DataTable)
        table.display = False

        ol = OptionList(
            *[Option(name, id=str(pid)) for name, pid in available],
            id="add-product-dialog",
        )
        self.mount(ol)
        ol.highlighted = 0
        ol.focus()

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            try:
                self.query_one("#add-product-dialog")
                event.prevent_default()
                self._dismiss_add_dialog()
            except Exception:
                pass

    def action_delete_product(self) -> None:
        if self._selected_supplier_id is None:
            return
        if self._editing is not None:
            return
        if not self._focus_is_on_table():
            return

        table = self.query_one("#purchase-table", DataTable)
        coord = table.cursor_coordinate
        group_idx = coord.column // COLS_PER_GROUP
        product_id = self._cell_product_map.get((coord.row, group_idx))

        if product_id is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM supplier_freq_product WHERE supplier_id = ? AND product_id = ?",
            (self._selected_supplier_id, product_id),
        )
        cur.execute(
            "DELETE FROM purchase_order "
            "WHERE supplier_id = ? AND product_id = ? AND order_date = ?",
            (self._selected_supplier_id, product_id, self.app.work_date),
        )
        conn.commit()
        conn.close()

        self._refresh_supplier_order_count()
        self._load_purchases()
