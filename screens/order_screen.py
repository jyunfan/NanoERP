from __future__ import annotations

import sqlite3
import os


from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Label, Input, Select
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
        Binding("f1", "add_order", "新增", show=True),
    ]

    def __init__(self, market: int, title: str) -> None:
        super().__init__()
        self._market = market
        self._title = title
        self._editing: Coordinate | None = None
        self._selected_customer_id: int | None = None
        self._customer_ids: list[int] = []  # row index -> customer id
        # Maps (row_index, group_index) -> order_table.id or None
        self._cell_order_map: dict[tuple[int, int], int] = {}
        # product_id stored per cell for display: (row_index, group_index) -> product_id
        self._cell_product_map: dict[tuple[int, int], int] = {}
        self._product_options: list[tuple[str, int]] = []  # (name, id)
        self._product_names: dict[int, str] = {}  # id -> short_name

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
        self._product_options = []
        self._product_names = {}
        for row in cur.fetchall():
            pid, name = row
            self._product_names[pid] = name or ""
            self._product_options.append((name or str(pid), pid))
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
        table = self.query_one("#order-table", DataTable)
        table.clear()
        self._cell_order_map.clear()
        self._cell_product_map.clear()

        if self._selected_customer_id is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, product_id, quantity FROM order_table "
            "WHERE customer_id = ? AND order_date = ? AND posted = 0 "
            "ORDER BY id",
            (self._selected_customer_id, self.app.work_date),
        )
        orders = cur.fetchall()
        conn.close()

        # Fill rows, 3 orders per row
        row_idx = 0
        for i in range(0, len(orders), NUM_GROUPS):
            row_values = []
            for g in range(NUM_GROUPS):
                if i + g < len(orders):
                    oid, pid, qty = orders[i + g]
                    self._cell_order_map[(row_idx, g)] = oid
                    self._cell_product_map[(row_idx, g)] = pid
                    row_values.append(self._product_names.get(pid, str(pid)))
                    row_values.append(str(qty) if qty is not None else "")
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
        self._start_edit(event.coordinate, event.value)

    def _start_edit(self, coord: Coordinate, current_value: object) -> None:
        col_key = COLUMNS[coord.column][0]
        self._editing = coord
        table = self.query_one("#order-table", DataTable)
        table.display = False

        if col_key.startswith("prod_"):
            # Product selector
            options = [(name, pid) for name, pid in self._product_options]
            select = Select(
                options,
                prompt="選擇產品",
                id="cell-editor",
            )
            self.mount(select)
            select.focus()
        else:
            # Quantity input
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

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._editing is None:
            return
        if event.value is not Select.BLANK:
            self._finish_edit_product(self._editing, int(event.value))

    def _get_group_index(self, col_index: int) -> int:
        return col_index // COLS_PER_GROUP

    def _finish_edit_product(self, coord: Coordinate, product_id: int) -> None:
        table = self.query_one("#order-table", DataTable)
        row_idx = coord.row
        group_idx = self._get_group_index(coord.column)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        order_id = self._cell_order_map.get((row_idx, group_idx))
        if order_id is not None:
            cur.execute(
                "UPDATE order_table SET product_id = ? WHERE id = ?",
                (product_id, order_id),
            )
        else:
            cur.execute(
                "INSERT INTO order_table (customer_id, product_id, quantity, order_date, is_return, posted) "
                "VALUES (?, ?, 0, ?, 0, 0)",
                (self._selected_customer_id, product_id, self.app.work_date),
            )
            order_id = cur.lastrowid
            self._cell_order_map[(row_idx, group_idx)] = order_id

        conn.commit()
        conn.close()

        self._cell_product_map[(row_idx, group_idx)] = product_id
        product_name = self._product_names.get(product_id, str(product_id))

        cell_key = table.coordinate_to_cell_key(coord)
        table.update_cell(cell_key.row_key, cell_key.column_key, product_name, update_width=True)

        self._refresh_customer_order_count()
        self._dismiss_editor(table)

    def _finish_edit_qty(self, coord: Coordinate, new_value: str) -> None:
        table = self.query_one("#order-table", DataTable)
        row_idx = coord.row
        group_idx = self._get_group_index(coord.column)

        order_id = self._cell_order_map.get((row_idx, group_idx))
        if order_id is not None:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                "UPDATE order_table SET quantity = ? WHERE id = ?",
                (new_value, order_id),
            )
            conn.commit()
            conn.close()

        cell_key = table.coordinate_to_cell_key(coord)
        table.update_cell(cell_key.row_key, cell_key.column_key, new_value, update_width=True)

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

    def action_add_order(self) -> None:
        if self._selected_customer_id is None:
            return
        if self._editing is not None:
            return

        table = self.query_one("#order-table", DataTable)

        # Find first empty slot
        target_row = None
        target_col = 0
        row_count = table.row_count
        for r in range(row_count):
            for g in range(NUM_GROUPS):
                if (r, g) not in self._cell_order_map:
                    target_row = r
                    target_col = g * COLS_PER_GROUP
                    break
            if target_row is not None:
                break

        # No empty slot found, add a new row
        if target_row is None:
            target_row = row_count
            table.add_row(*[""] * len(COLUMNS), key=f"row_{target_row}")
            target_col = 0

        table.focus()
        table.move_cursor(row=target_row, column=target_col)
        coord = Coordinate(target_row, target_col)
        self._start_edit(coord, "")
