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

COLS_PER_GROUP = 2  # product + quantity
NUM_GROUPS = 3  # 3 groups per row

# Column definitions: (key, label) repeated for each group
COLUMNS: list[tuple[str, str]] = []
for i in range(NUM_GROUPS):
    COLUMNS.append((f"prod_{i}", f"名稱"))
    COLUMNS.append((f"qty_{i}", "數量"))


class OrderScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back_or_cancel", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
        Binding("f1", "add_product", "新增產品", show=True),
        Binding("delete", "delete_product", "刪除產品", show=True),
    ]

    def __init__(self, market: int, title: str) -> None:
        super().__init__()
        self._market = market
        self._title = title
        self._editing: Coordinate | None = None
        self._selected_customer_id: int | None = None
        self._customer_ids: list[int] = []  # row index -> customer id
        # Maps (row_index, group_index) -> product_id from customer_freq_product
        self._cell_product_map: dict[tuple[int, int], int] = {}
        # All products: id -> short_name
        self._product_names: dict[int, str] = {}
        # All products list for add dialog
        self._all_products: list[tuple[str, int]] = []  # (name, id)
        # Product IDs shown in current add dialog
        self._add_option_ids: list[int] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="order-title")
        with Horizontal(id="order-container"):
            yield DataTable(id="customer-list", cursor_type="row")
            yield DataTable(id="order-table", cursor_type="cell")
        yield Footer()

    def on_mount(self) -> None:
        self._load_products()
        self._load_customers()
        self.watch(self.app, "work_date", self._on_work_date_changed, init=False)
        table = self.query_one("#order-table", DataTable)
        for col_key, col_label in COLUMNS:
            table.add_column(col_label, key=col_key)

    def _on_work_date_changed(self, new_value: str) -> None:
        self._load_customers()

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

    def _load_customers(self) -> None:
        cust_table = self.query_one("#customer-list", DataTable)
        cust_table.clear(columns=True)
        cust_table.add_column("客戶名稱", key="cust_name")
        cust_table.add_column("訂單數目", key="order_count")
        self._customer_ids = []
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT c.id, c.name, COUNT(o.id) as order_count "
            "FROM customer c "
            "LEFT JOIN order_table o ON o.customer_id = c.id AND o.order_date = ? AND o.posted = 0 "
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
        if event.data_table.id != "customer-list":
            return
        if event.cursor_row < len(self._customer_ids):
            self._selected_customer_id = self._customer_ids[event.cursor_row]
            self._load_orders()

    def on_data_table_row_selected(
        self, event: DataTable.RowSelected
    ) -> None:
        if event.data_table.id != "customer-list":
            return
        table = self.query_one("#order-table", DataTable)
        table.focus()
        if table.row_count > 0:
            table.move_cursor(row=0, column=0)

    def _load_orders(self) -> None:
        """Load customer_freq_product list with quantities from order_table."""
        table = self.query_one("#order-table", DataTable)
        table.clear()
        self._cell_product_map.clear()

        if self._selected_customer_id is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Get customer's frequent products with their order quantities for today
        cur.execute(
            "SELECT cfp.product_id, o.quantity "
            "FROM customer_freq_product cfp "
            "LEFT JOIN order_table o ON o.customer_id = cfp.customer_id "
            "  AND o.product_id = cfp.product_id "
            "  AND o.order_date = ? AND o.posted = 0 "
            "WHERE cfp.customer_id = ? "
            "ORDER BY cfp.product_id",
            (self.app.work_date, self._selected_customer_id),
        )
        items = cur.fetchall()
        conn.close()

        # Fill rows, 3 products per row
        row_idx = 0
        for i in range(0, len(items), NUM_GROUPS):
            row_values = []
            for g in range(NUM_GROUPS):
                if i + g < len(items):
                    pid, qty = items[i + g]
                    self._cell_product_map[(row_idx, g)] = pid
                    row_values.append(self._product_names.get(pid, str(pid)))
                    row_values.append(str(qty) if qty else "")
                else:
                    row_values.append("")
                    row_values.append("")
            table.add_row(*row_values, key=f"row_{row_idx}")
            row_idx += 1

    def _refresh_customer_order_count(self) -> None:
        if self._selected_customer_id is None:
            return
        cust_table = self.query_one("#customer-list", DataTable)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(id) FROM order_table "
            "WHERE customer_id = ? AND order_date = ? AND posted = 0",
            (self._selected_customer_id, self.app.work_date),
        )
        count = cur.fetchone()[0]
        conn.close()
        count_str = str(count) if count > 0 else ""
        row_key = f"cust_{self._selected_customer_id}"
        cust_table.update_cell(row_key, "order_count", count_str, update_width=True)

    def on_data_table_cell_selected(
        self, event: DataTable.CellSelected
    ) -> None:
        if event.data_table.id != "order-table":
            return
        if self._editing is not None:
            return
        if self._selected_customer_id is None:
            return
        col_key = COLUMNS[event.coordinate.column][0]
        # Only quantity cells are editable
        if not col_key.startswith("qty_"):
            return
        # Only edit if there's a product in this group
        group_idx = event.coordinate.column // COLS_PER_GROUP
        if (event.coordinate.row, group_idx) not in self._cell_product_map:
            return
        self._start_edit_qty(event.coordinate, event.value)

    def _start_edit_qty(self, coord: Coordinate, current_value: object) -> None:
        self._editing = coord
        table = self.query_one("#order-table", DataTable)
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
        self._finish_edit_qty(self._editing, event.value)

    def _finish_edit_qty(self, coord: Coordinate, new_value: str) -> None:
        table = self.query_one("#order-table", DataTable)
        row_idx = coord.row
        group_idx = coord.column // COLS_PER_GROUP
        product_id = self._cell_product_map.get((row_idx, group_idx))

        if product_id is not None and self._selected_customer_id is not None:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            qty = int(new_value) if new_value.strip() else 0
            if qty > 0:
                # Upsert: update if exists, insert if not
                cur.execute(
                    "SELECT id FROM order_table "
                    "WHERE customer_id = ? AND product_id = ? AND order_date = ? AND posted = 0",
                    (self._selected_customer_id, product_id, self.app.work_date),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        "UPDATE order_table SET quantity = ? WHERE id = ?",
                        (qty, existing[0]),
                    )
                else:
                    cur.execute(
                        "INSERT INTO order_table (customer_id, product_id, quantity, order_date, is_return, posted) "
                        "VALUES (?, ?, ?, ?, 0, 0)",
                        (self._selected_customer_id, product_id, qty, self.app.work_date),
                    )
            else:
                # Quantity is 0 or empty: delete the order if it exists
                cur.execute(
                    "DELETE FROM order_table "
                    "WHERE customer_id = ? AND product_id = ? AND order_date = ? AND posted = 0",
                    (self._selected_customer_id, product_id, self.app.work_date),
                )
                new_value = ""
            conn.commit()
            conn.close()

        cell_key = table.coordinate_to_cell_key(coord)
        table.update_cell(cell_key.row_key, cell_key.column_key, new_value, update_width=True)
        self._refresh_customer_order_count()
        self._dismiss_editor(table)

    def _dismiss_editor(self, table: DataTable) -> None:
        editor = self.query_one("#cell-editor")
        editor.remove()
        self._editing = None
        table.display = True
        table.focus()

    def _focus_is_on_table(self) -> bool:
        focused = self.app.focused
        table = self.query_one("#order-table", DataTable)
        return focused is table

    def action_go_back_or_cancel(self) -> None:
        if self._editing is not None:
            table = self.query_one("#order-table", DataTable)
            self._dismiss_editor(table)
        elif self._focus_is_on_table():
            self.query_one("#customer-list", DataTable).focus()
        else:
            self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen
        self.app.push_screen(QuitScreen())

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if self._editing is not None:
            return
        # This is the add-product dialog
        product_id = self._add_option_ids[event.option_index]
        self._finish_add_product(product_id)

    def _finish_add_product(self, product_id: int) -> None:
        if self._selected_customer_id is None:
            return
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO customer_freq_product (customer_id, product_id) VALUES (?, ?)",
            (self._selected_customer_id, product_id),
        )
        conn.commit()
        conn.close()
        self._dismiss_add_dialog()
        self._load_orders()

    def _dismiss_add_dialog(self) -> None:
        try:
            editor = self.query_one("#add-product-dialog")
            editor.remove()
        except Exception:
            pass
        table = self.query_one("#order-table", DataTable)
        table.display = True
        table.focus()

    def action_add_product(self) -> None:
        """F1: Add a new product to customer_freq_product."""
        if self._selected_customer_id is None:
            return
        if self._editing is not None:
            return

        # Get current freq product IDs for this customer
        existing_pids = set(self._cell_product_map.values())

        # Filter out already-added products
        available = [(name, pid) for name, pid in self._all_products if pid not in existing_pids]
        if not available:
            return

        self._add_option_ids = [pid for _name, pid in available]
        table = self.query_one("#order-table", DataTable)
        table.display = False

        ol = OptionList(
            *[Option(name, id=str(pid)) for name, pid in available],
            id="add-product-dialog",
        )
        self.mount(ol)
        ol.highlighted = 0
        ol.focus()

    def on_key(self, event: Key) -> None:
        # Handle Escape on add-product dialog
        if event.key == "escape":
            try:
                self.query_one("#add-product-dialog")
                event.prevent_default()
                self._dismiss_add_dialog()
            except Exception:
                pass

    def action_delete_product(self) -> None:
        """DEL: Remove product from customer_freq_product."""
        if self._selected_customer_id is None:
            return
        if self._editing is not None:
            return
        if not self._focus_is_on_table():
            return

        table = self.query_one("#order-table", DataTable)
        coord = table.cursor_coordinate
        group_idx = coord.column // COLS_PER_GROUP
        product_id = self._cell_product_map.get((coord.row, group_idx))

        if product_id is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Remove from customer_freq_product
        cur.execute(
            "DELETE FROM customer_freq_product WHERE customer_id = ? AND product_id = ?",
            (self._selected_customer_id, product_id),
        )
        # Also remove any associated order for today
        cur.execute(
            "DELETE FROM order_table "
            "WHERE customer_id = ? AND product_id = ? AND order_date = ? AND posted = 0",
            (self._selected_customer_id, product_id, self.app.work_date),
        )
        conn.commit()
        conn.close()

        self._refresh_customer_order_count()
        self._load_orders()
