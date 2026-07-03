from __future__ import annotations

import sqlite3
import os


from textual.app import ComposeResult
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Label, Input, OptionList
from textual.widgets.option_list import Option
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.coordinate import Coordinate

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")

MARKET_NAMES = {
    1: "1. 其餘市場",
    2: "2. 建國市場",
    3: "3. 南部市場",
}

COLS_PER_GROUP = 2  # product + quantity
NUM_GROUPS = 3  # 3 groups per row

# Column definitions: (key, label) repeated for each group
QUANTITY_COLUMNS: list[tuple[str, str]] = []
for i in range(NUM_GROUPS):
    QUANTITY_COLUMNS.append((f"prod_{i}", "名稱"))
    QUANTITY_COLUMNS.append((f"qty_{i}", "數量"))

PRICE_COLUMNS = [
    ("product", "名稱"),
    ("purchase_price", "進價"),
    ("sale_price", "售價"),
]


class OrderScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back_or_cancel", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
        Binding("f1", "add_product", "新增產品", show=True),
        Binding("f2", "calculation_check", "計算檢查", show=False),
        Binding("f3", "toggle_price_mode", "售價模式", show=True),
        Binding("f9", "delete_product", "刪除產品", show=True),
        Binding("delete", "delete_product", "刪除產品", show=False),
        Binding("tab", "toggle_focus", "左右切換", show=True),
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
        # Maps row_index -> product_id in price mode
        self._price_product_map: dict[int, int] = {}
        # All products: id -> short_name
        self._product_names: dict[int, str] = {}
        # All products list for add dialog
        self._all_products: list[tuple[str, int]] = []  # (name, id)
        # Product IDs shown in current add dialog
        self._add_option_ids: list[int] = []
        self._mode = "quantity"
        self._editing_mode: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="order-title")
        with Horizontal(id="order-container"):
            yield DataTable(id="customer-list", cursor_type="row")
            with Vertical(id="order-middle"):
                yield Label(
                    "Tab : 左右切換\nEnter : 選定\nEsc : 跳出",
                    id="order-prompt",
                )
                yield DataTable(id="order-table", cursor_type="cell")
            yield DataTable(id="order-total-table", cursor_type="none")
        yield Footer()

    def on_mount(self) -> None:
        self._load_products()
        table = self.query_one("#order-table", DataTable)
        self._configure_order_columns(table)
        total_table = self.query_one("#order-total-table", DataTable)
        total_table.add_column("產品", key="product_name")
        total_table.add_column("總數", key="quantity")
        self._load_customers()
        self.watch(self.app, "work_date", self._on_work_date_changed, init=False)

    def _configure_order_columns(self, table: DataTable) -> None:
        table.clear(columns=True)
        columns = PRICE_COLUMNS if self._mode == "price" else QUANTITY_COLUMNS
        for col_key, col_label in columns:
            table.add_column(col_label, key=col_key)
        table.cursor_type = "cell"

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
        self._selected_customer_id = None
        order_table = self.query_one("#order-table", DataTable)
        order_table.clear()
        self._cell_product_map.clear()
        self._price_product_map.clear()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT c.id, c.name, COUNT(o.id) as order_count "
            "FROM customer c "
            "LEFT JOIN order_draft o ON o.customer_id = c.id "
            "WHERE c.market = ? "
            "GROUP BY c.id "
            "ORDER BY c.id",
            (self._market,),
        )
        for row in cur.fetchall():
            cid, name, count = row
            self._customer_ids.append(cid)
            count_str = str(count) if count > 0 else ""
            cust_table.add_row(name or str(cid), count_str, key=f"cust_{cid}")
        conn.close()
        self._load_product_totals()
        self._show_initial_view()

    def on_data_table_row_selected(
        self, event: DataTable.RowSelected
    ) -> None:
        if event.data_table.id != "customer-list":
            return
        if event.cursor_row >= len(self._customer_ids):
            return
        self._selected_customer_id = self._customer_ids[event.cursor_row]
        self._mode = "quantity"
        self._update_title()
        table = self.query_one("#order-table", DataTable)
        self._configure_order_columns(table)
        self._show_order_detail()
        self._load_orders()
        table = self.query_one("#order-table", DataTable)
        table.focus()
        if table.row_count > 0:
            table.move_cursor(row=0, column=0)

    def _show_initial_view(self) -> None:
        self._selected_customer_id = None
        self._cell_product_map.clear()
        self._price_product_map.clear()
        self.query_one("#order-prompt", Label).display = True
        table = self.query_one("#order-table", DataTable)
        table.display = False
        table.clear()
        self.query_one("#order-total-table", DataTable).display = True
        self._mode = "quantity"
        self._update_title()

    def _show_order_detail(self) -> None:
        self.query_one("#order-prompt", Label).display = False
        self.query_one("#order-table", DataTable).display = True
        self.query_one("#order-total-table", DataTable).display = False

    def _load_product_totals(self) -> None:
        total_table = self.query_one("#order-total-table", DataTable)
        total_table.clear()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT p.short_name, SUM(o.quantity) AS quantity "
            "FROM order_draft o "
            "JOIN customer c ON c.id = o.customer_id "
            "JOIN product p ON p.id = o.product_id "
            "WHERE c.market = ? AND o.is_return = 0 "
            "GROUP BY o.product_id "
            "ORDER BY p.id",
            (self._market,),
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            total_table.add_row("(無訂單)", "")
            return

        for name, quantity in rows:
            total_table.add_row(name or "", self._format_number(quantity))

    def _load_orders(self) -> None:
        """Load customer_freq_product list with quantities from order_draft."""
        if self._mode == "price":
            self._load_price_rows()
            return

        table = self.query_one("#order-table", DataTable)
        table.clear()
        self._cell_product_map.clear()
        self._price_product_map.clear()

        if self._selected_customer_id is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Get customer's frequent products + any extra orders not in freq list
        cur.execute(
            "SELECT product_id, quantity FROM ("
            "  SELECT cfp.product_id, o.quantity"
            "  FROM customer_freq_product cfp"
            "  LEFT JOIN order_draft o ON o.customer_id = cfp.customer_id"
            "    AND o.product_id = cfp.product_id"
            "    AND o.is_return = 0"
            "  WHERE cfp.customer_id = ?"
            "  UNION"
            "  SELECT o.product_id, o.quantity"
            "  FROM order_draft o"
            "  WHERE o.customer_id = ? AND o.is_return = 0"
            "    AND o.product_id NOT IN ("
            "      SELECT product_id FROM customer_freq_product WHERE customer_id = ?"
            "    )"
            ") ORDER BY product_id",
            (
                self._selected_customer_id,
                self._selected_customer_id,
                self._selected_customer_id,
            ),
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

    def _load_price_rows(self) -> None:
        """Load customer products with purchase price reference and editable sale price."""
        table = self.query_one("#order-table", DataTable)
        table.clear()
        self._cell_product_map.clear()
        self._price_product_map.clear()

        if self._selected_customer_id is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT i.product_id, p.short_name, p.purchase_price, "
            "       COALESCE(cp.sale_price, p.sale_price) AS sale_price "
            "FROM ("
            "  SELECT product_id FROM customer_freq_product WHERE customer_id = ?"
            "  UNION"
            "  SELECT product_id FROM order_draft WHERE customer_id = ? AND is_return = 0"
            ") i "
            "JOIN product p ON p.id = i.product_id "
            "LEFT JOIN customer_product cp "
            "  ON cp.customer_id = ? AND cp.product_id = i.product_id "
            "ORDER BY i.product_id",
            (
                self._selected_customer_id,
                self._selected_customer_id,
                self._selected_customer_id,
            ),
        )
        for row_idx, (product_id, name, purchase_price, sale_price) in enumerate(
            cur.fetchall()
        ):
            self._price_product_map[row_idx] = product_id
            table.add_row(
                name or str(product_id),
                self._format_number(purchase_price),
                self._format_number(sale_price),
                key=f"row_{row_idx}",
            )
        conn.close()

    def _refresh_customer_order_count(self) -> None:
        if self._selected_customer_id is None:
            return
        cust_table = self.query_one("#customer-list", DataTable)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(id) FROM order_draft "
            "WHERE customer_id = ? AND is_return = 0",
            (self._selected_customer_id,),
        )
        count = cur.fetchone()[0]
        conn.close()
        count_str = str(count) if count > 0 else ""
        row_key = f"cust_{self._selected_customer_id}"
        cust_table.update_cell(row_key, "order_count", count_str, update_width=True)
        self._load_product_totals()

    def on_data_table_cell_selected(
        self, event: DataTable.CellSelected
    ) -> None:
        if event.data_table.id != "order-table":
            return
        if self._editing is not None:
            return
        if self._selected_customer_id is None:
            return
        columns = PRICE_COLUMNS if self._mode == "price" else QUANTITY_COLUMNS
        col_key = columns[event.coordinate.column][0]
        if self._mode == "price":
            if col_key != "sale_price":
                return
            if event.coordinate.row not in self._price_product_map:
                return
            self._start_edit_price(event.coordinate, event.value)
            return

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
        self._editing_mode = "quantity"
        table = self.query_one("#order-table", DataTable)
        table.display = False
        edit_input = Input(
            value=str(current_value) if current_value else "",
            id="cell-editor",
        )
        self.mount(edit_input)
        edit_input.focus()

    def _start_edit_price(self, coord: Coordinate, current_value: object) -> None:
        self._editing = coord
        self._editing_mode = "price"
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
        if self._editing_mode == "price":
            self._finish_edit_price(self._editing, event.value)
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
                    "SELECT id FROM order_draft "
                    "WHERE customer_id = ? AND product_id = ? AND is_return = 0",
                    (self._selected_customer_id, product_id),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        "UPDATE order_draft "
                        "SET quantity = ?, updated_at = CURRENT_TIMESTAMP "
                        "WHERE id = ?",
                        (qty, existing[0]),
                    )
                else:
                    cur.execute(
                        "INSERT INTO order_draft (customer_id, product_id, quantity, is_return) "
                        "VALUES (?, ?, ?, 0)",
                        (self._selected_customer_id, product_id, qty),
                    )
            else:
                # Quantity is 0 or empty: delete the order if it exists
                cur.execute(
                    "DELETE FROM order_draft "
                    "WHERE customer_id = ? AND product_id = ? AND is_return = 0",
                    (self._selected_customer_id, product_id),
                )
                new_value = ""
            conn.commit()
            conn.close()

        cell_key = table.coordinate_to_cell_key(coord)
        table.update_cell(cell_key.row_key, cell_key.column_key, new_value, update_width=True)
        self._refresh_customer_order_count()
        self._dismiss_editor(table)

    def _finish_edit_price(self, coord: Coordinate, new_value: str) -> None:
        table = self.query_one("#order-table", DataTable)
        product_id = self._price_product_map.get(coord.row)

        if product_id is not None and self._selected_customer_id is not None:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            try:
                parsed_value = self._parse_number(new_value)
            except ValueError:
                conn.close()
                self._dismiss_editor(table)
                return
            if parsed_value is None:
                cur.execute(
                    "DELETE FROM customer_product "
                    "WHERE customer_id = ? AND product_id = ?",
                    (self._selected_customer_id, product_id),
                )
                cur.execute("SELECT sale_price FROM product WHERE id = ?", (product_id,))
                default_row = cur.fetchone()
                display_value = self._format_number(default_row[0] if default_row else "")
            else:
                cur.execute(
                    "INSERT INTO customer_product (customer_id, product_id, sale_price) "
                    "VALUES (?, ?, ?) "
                    "ON CONFLICT(customer_id, product_id) "
                    "DO UPDATE SET sale_price = excluded.sale_price",
                    (self._selected_customer_id, product_id, parsed_value),
                )
                display_value = self._format_number(parsed_value)
            conn.commit()
            conn.close()
        else:
            display_value = new_value

        cell_key = table.coordinate_to_cell_key(coord)
        table.update_cell(
            cell_key.row_key,
            cell_key.column_key,
            display_value,
            update_width=True,
        )
        self._dismiss_editor(table)

    def _dismiss_editor(self, table: DataTable) -> None:
        editor = self.query_one("#cell-editor")
        editor.remove()
        self._editing = None
        self._editing_mode = None
        table.display = True
        table.focus()

    def _focus_is_on_table(self) -> bool:
        focused = self.app.focused
        table = self.query_one("#order-table", DataTable)
        return focused is table

    def _focus_is_on_product_totals(self) -> bool:
        focused = self.app.focused
        table = self.query_one("#order-total-table", DataTable)
        return focused is table

    def _detail_active(self) -> bool:
        return self._selected_customer_id is not None

    def action_toggle_price_mode(self) -> None:
        if self._editing is not None:
            return
        if self._add_dialog_open():
            return
        if not self._detail_active():
            return
        self._mode = "price" if self._mode == "quantity" else "quantity"
        table = self.query_one("#order-table", DataTable)
        self._configure_order_columns(table)
        self._update_title()
        self._load_orders()
        table.focus()
        if table.row_count > 0:
            table.move_cursor(row=0, column=0)

    def action_toggle_focus(self) -> None:
        if self._editing is not None:
            return
        if self._add_dialog_open():
            return
        if self._focus_is_on_table():
            self.query_one("#customer-list", DataTable).focus()
            return
        if self._focus_is_on_product_totals():
            self.query_one("#customer-list", DataTable).focus()
            return
        if not self._detail_active():
            self.query_one("#order-total-table", DataTable).focus()
            return
        table = self.query_one("#order-table", DataTable)
        table.focus()
        if table.row_count > 0:
            table.move_cursor(row=0, column=0)

    def action_go_back_or_cancel(self) -> None:
        if self._editing is not None:
            table = self.query_one("#order-table", DataTable)
            self._dismiss_editor(table)
        elif self._focus_is_on_table():
            self._show_initial_view()
            self.query_one("#customer-list", DataTable).focus()
        elif self._focus_is_on_product_totals():
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
        existing_pids = self._visible_product_ids()

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

    def action_calculation_check(self) -> None:
        self.app.notify("計算檢查尚未實作", severity="warning")

    def on_key(self, event: Key) -> None:
        # Handle Escape on add-product dialog
        if event.key == "escape":
            try:
                self.query_one("#add-product-dialog")
                event.prevent_default()
                self._dismiss_add_dialog()
            except Exception:
                pass
            return

        if self._editing is not None or self._add_dialog_open():
            return
        if event.character in ("1", "2", "3"):
            event.prevent_default()
            self._switch_market(int(event.character))
            return
        if event.character == "4":
            event.prevent_default()
            from screens.total_check_screen import TotalCheckScreen

            self.app.push_screen(TotalCheckScreen(title="4. 總數核對"))
            return

    def _add_dialog_open(self) -> bool:
        try:
            self.query_one("#add-product-dialog")
            return True
        except Exception:
            return False

    def _switch_market(self, market: int) -> None:
        self._market = market
        self._title = MARKET_NAMES[market]
        self._update_title()
        self._load_customers()
        self.query_one("#customer-list", DataTable).focus()

    def _update_title(self) -> None:
        suffix = " - 售價模式" if self._mode == "price" else ""
        self.query_one("#order-title", Label).update(f"{self._title}{suffix}")

    def _visible_product_ids(self) -> set[int]:
        if self._mode == "price":
            return set(self._price_product_map.values())
        return set(self._cell_product_map.values())

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
        if self._mode == "price":
            product_id = self._price_product_map.get(coord.row)
        else:
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
        # Also remove any associated draft order.
        cur.execute(
            "DELETE FROM order_draft "
            "WHERE customer_id = ? AND product_id = ? AND is_return = 0",
            (self._selected_customer_id, product_id),
        )
        cur.execute(
            "DELETE FROM customer_product WHERE customer_id = ? AND product_id = ?",
            (self._selected_customer_id, product_id),
        )
        conn.commit()
        conn.close()

        self._refresh_customer_order_count()
        self._load_orders()

    @staticmethod
    def _parse_number(value: str) -> int | float | None:
        stripped = value.strip()
        if not stripped:
            return None
        number = float(stripped)
        return int(number) if number.is_integer() else number

    @staticmethod
    def _format_number(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
