from __future__ import annotations

import os
import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label

from constants import CHECKOUT_CODES
from screens.ui4_common import MARKETS, format_work_date

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sql")


class PrintSettingsScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "返回", show=True),
        Binding("q", "request_quit", "離開", show=True),
        Binding("0", "toggle_current", "更改開關", show=False),
        Binding("alt+f1", "select_checkout_1", "出貨", show=False),
        Binding("alt+f2", "select_checkout_2", "日", show=False),
        Binding("alt+f3", "select_checkout_3", "週", show=False),
        Binding("alt+f4", "select_checkout_4", "旬", show=False),
        Binding("alt+f5", "select_checkout_5", "半月", show=False),
        Binding("alt+f6", "select_checkout_6", "月", show=False),
        Binding("ctrl+home", "disable_market", "本市場全部不印", show=False),
        Binding("ctrl+end", "restore_default", "本市場恢復內定", show=False),
    ]

    def __init__(self, title: str, report_type: str = "daily_account") -> None:
        super().__init__()
        self._title = title
        self._report_type = report_type
        self._market = 1
        self._customer_ids: list[int] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(self._title, id="print-settings-title")
        with Horizontal(id="print-settings-container"):
            yield DataTable(id="print-settings-table", cursor_type="row")
            with Vertical(id="print-settings-help"):
                yield Label(
                    "Esc: 回跳\n"
                    "0: 更改開關\n"
                    "●: 印\n"
                    "○: 不印\n\n"
                    "Alt_組合鍵（以結帳期選定）\n"
                    "F1: 出貨\n"
                    "F2: 日\n"
                    "F3: 週\n"
                    "F4: 旬\n"
                    "F5: 半月\n"
                    "F6: 月\n\n"
                    "Ctrl_組合鍵\n"
                    "Home: 本市場全部不印\n"
                    "End: 本市場恢復內定\n\n"
                    "內定值\n"
                    "出貨單: F1 ~ F6\n"
                    "日帳單: 僅 F2",
                    id="print-settings-help-text",
                )
        yield Label(format_work_date(self.app.work_date), id="print-settings-work-date")
        yield Label(
            "0.回上系統  1.其餘市場  2.建國市場  3.南部市場",
            id="print-settings-footer-options",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#print-settings-table", DataTable)
        table.add_column("客戶清單", key="customer")
        table.add_column("交易數", key="transaction_count")
        table.add_column("列印", key="enabled")
        self._load_customers()
        table.focus()
        self.watch(self.app, "work_date", self._on_work_date_changed, init=False)

    def _on_work_date_changed(self, new_value: str) -> None:
        self.query_one("#print-settings-work-date", Label).update(
            format_work_date(new_value)
        )
        self._load_customers()

    def on_key(self, event: Key) -> None:
        if event.character in ("1", "2", "3"):
            event.prevent_default()
            self._switch_market(int(event.character))

    def _switch_market(self, market: int) -> None:
        self._market = market
        self._load_customers()
        self.query_one("#print-settings-table", DataTable).focus()

    def _load_customers(self) -> None:
        table = self.query_one("#print-settings-table", DataTable)
        table.clear()
        self._customer_ids = []

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT c.id, c.name, c.checkout_code, COUNT(o.id), ps.enabled "
            "FROM customer c "
            "LEFT JOIN order_table o "
            "  ON o.customer_id = c.id AND o.order_date = ? "
            "LEFT JOIN customer_print_setting ps "
            "  ON ps.customer_id = c.id AND ps.report_type = ? "
            "WHERE c.market = ? "
            "GROUP BY c.id "
            "ORDER BY c.id",
            (self.app.work_date, self._report_type, self._market),
        )
        for customer_id, name, checkout_code, count, enabled in cur.fetchall():
            if enabled is None:
                enabled = int(self._default_enabled(checkout_code))
            self._customer_ids.append(customer_id)
            table.add_row(
                name or str(customer_id),
                f"{count}.",
                "●" if enabled else "○",
                key=f"customer_{customer_id}",
            )
        conn.close()

    def action_toggle_current(self) -> None:
        table = self.query_one("#print-settings-table", DataTable)
        if table.cursor_row >= len(self._customer_ids):
            return
        customer_id = self._customer_ids[table.cursor_row]

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        current = self._effective_enabled(cur, customer_id)
        self._save_setting(cur, customer_id, not current)
        conn.commit()
        conn.close()
        self._load_customers()
        if table.row_count:
            table.move_cursor(row=min(table.cursor_row, table.row_count - 1))

    def action_select_checkout_1(self) -> None:
        self._select_checkout_code(1)

    def action_select_checkout_2(self) -> None:
        self._select_checkout_code(2)

    def action_select_checkout_3(self) -> None:
        self._select_checkout_code(3)

    def action_select_checkout_4(self) -> None:
        self._select_checkout_code(4)

    def action_select_checkout_5(self) -> None:
        self._select_checkout_code(5)

    def action_select_checkout_6(self) -> None:
        self._select_checkout_code(6)

    def _select_checkout_code(self, checkout_code: int) -> None:
        if checkout_code not in CHECKOUT_CODES:
            return
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, checkout_code FROM customer WHERE market = ? ORDER BY id",
            (self._market,),
        )
        for customer_id, customer_checkout_code in cur.fetchall():
            self._save_setting(
                cur,
                customer_id,
                int(customer_checkout_code or 0) == checkout_code,
            )
        conn.commit()
        conn.close()
        self._load_customers()

    def action_disable_market(self) -> None:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id FROM customer WHERE market = ?", (self._market,))
        for (customer_id,) in cur.fetchall():
            self._save_setting(cur, customer_id, False)
        conn.commit()
        conn.close()
        self._load_customers()

    def action_restore_default(self) -> None:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, checkout_code FROM customer WHERE market = ?",
            (self._market,),
        )
        for customer_id, checkout_code in cur.fetchall():
            self._save_setting(cur, customer_id, self._default_enabled(checkout_code))
        conn.commit()
        conn.close()
        self._load_customers()

    def _effective_enabled(self, cur: sqlite3.Cursor, customer_id: int) -> bool:
        cur.execute(
            "SELECT c.checkout_code, ps.enabled "
            "FROM customer c "
            "LEFT JOIN customer_print_setting ps "
            "  ON ps.customer_id = c.id AND ps.report_type = ? "
            "WHERE c.id = ?",
            (self._report_type, customer_id),
        )
        row = cur.fetchone()
        if row is None:
            return False
        checkout_code, enabled = row
        if enabled is None:
            return self._default_enabled(checkout_code)
        return bool(enabled)

    def _save_setting(
        self, cur: sqlite3.Cursor, customer_id: int, enabled: bool
    ) -> None:
        cur.execute(
            "INSERT INTO customer_print_setting (report_type, customer_id, enabled) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(report_type, customer_id) "
            "DO UPDATE SET enabled = excluded.enabled",
            (self._report_type, customer_id, int(enabled)),
        )

    def _default_enabled(self, checkout_code: int | None) -> bool:
        code = int(checkout_code or 0)
        if self._report_type == "shipping":
            return code in (1, 2, 3, 4, 5, 6)
        return code == 2

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_request_quit(self) -> None:
        from screens.quit_dialog import QuitScreen

        self.app.push_screen(QuitScreen())
