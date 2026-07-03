#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sqlite3
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = Path("/tmp/nanoerp_test_cases.db")

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import create_db  # noqa: E402


POSTED_DATES = ("2026-06-30", "2026-07-01", "2026-07-02")
DRAFT_WORK_DATE = "2026-07-03"

CUSTOMERS = (
    (1, 0, "陳先生", 6, "1234567890", "09233666888", 1),
    (2, 1, "梁先生", 5, "", "", 1),
    (3, 0, "許小姐", 6, "045832643", "", 2),
    (4, 1, "林先生", 2, "", "", 1),
    (5, 1, "王先生", 6, "", "", 1),
    (6, 1, "蔡小姐", 5, "", "", 1),
    (7, 0, "曾先生", 6, "", "", 2),
    (8, 0, "呂小姐", 5, "", "", 2),
    (9, 0, "彭先生", 2, "", "", 2),
    (10, 0, "記小姐", 2, "", "", 2),
)

PRODUCTS = (
    (1, 0, "大黑", "大黑", 60, 70, "", "", 0),
    (2, 0, "印干", "印干", 30, 40, None, "", 0),
    (3, 0, "干片", "干片", 20, 30, None, "", 0),
    (4, 0, "五香干", "五香干", 30, 40, None, "", 0),
    (5, 0, "白干", "白干", 30, 40, None, "", 0),
    (6, 0, "白干絲", "白干絲", 20, 35, None, "", 0),
    (7, 0, "黃干絲", "黃干絲", 20, 35, None, "", 0),
    (8, 0, "大米", "大米", 25, 38, None, "", 0),
    (9, 0, "小米", "小米", 30, 41, None, "", 0),
    (10, 0, "皮結", "皮結", 28, 40, None, "", 0),
    (11, 0, "西瓜", "西瓜", 50, 70, None, "", 0),
    (12, 0, "炸豆皮", "炸豆皮", 35, 50, None, "", 0),
)

SUPPLIERS = (
    (1, "大成", "", ""),
    (2, "永鮮", "", ""),
)

CUSTOMER_FREQ_PRODUCTS = (
    (1, 1), (1, 4), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10), (1, 11),
    (2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10), (2, 11),
    (3, 1), (3, 3), (3, 4), (3, 11),
    (4, 5), (4, 10),
    (5, 8), (5, 9),
    (6, 6), (6, 7),
    (7, 3), (7, 4),
    (8, 1), (8, 12),
    (9, 10), (9, 11),
    (10, 2), (10, 12),
)

CUSTOMER_PRODUCT_PRICES = (
    (1, 1, 75),
    (1, 4, 41),
    (3, 11, 72),
    (8, 12, 55),
)

SUPPLIER_FREQ_PRODUCTS = (
    (1, 2), (1, 3), (1, 4), (1, 6), (1, 7),
    (2, 1), (2, 8), (2, 11), (2, 12),
)

POSTED_ORDERS = (
    ("2026-06-30", 1, 1, 10, 0),
    ("2026-06-30", 1, 4, 3, 0),
    ("2026-06-30", 1, 1, 1, 1),
    ("2026-06-30", 2, 2, 8, 0),
    ("2026-06-30", 2, 7, 5, 0),
    ("2026-06-30", 3, 11, 4, 0),
    ("2026-06-30", 4, 5, 6, 0),
    ("2026-06-30", 4, 10, 2, 1),
    ("2026-07-01", 5, 8, 7, 0),
    ("2026-07-01", 5, 9, 4, 0),
    ("2026-07-01", 6, 6, 9, 0),
    ("2026-07-01", 6, 7, 2, 0),
    ("2026-07-01", 7, 3, 6, 0),
    ("2026-07-01", 7, 4, 3, 0),
    ("2026-07-01", 8, 12, 5, 0),
    ("2026-07-01", 8, 1, 2, 1),
    ("2026-07-02", 9, 10, 8, 0),
    ("2026-07-02", 9, 11, 2, 0),
    ("2026-07-02", 10, 12, 3, 0),
    ("2026-07-02", 10, 2, 7, 0),
    ("2026-07-02", 1, 8, 5, 0),
    ("2026-07-02", 2, 5, 4, 0),
    ("2026-07-02", 3, 1, 6, 0),
    ("2026-07-02", 3, 11, 1, 1),
)

DRAFT_ORDERS = (
    (1, 6, 4, 0),
    (2, 4, 5, 0),
    (3, 11, 2, 0),
    (4, 10, 1, 1),
    (7, 3, 5, 0),
    (8, 12, 6, 0),
    (9, 10, 2, 0),
    (10, 2, 3, 0),
)

PURCHASE_ORDERS = (
    (1, 2, 30, 0, "2026-06-30"),
    (1, 3, 2, 1, "2026-06-30"),
    (2, 11, 12, 0, "2026-06-30"),
    (1, 4, 25, 0, "2026-07-01"),
    (2, 12, 15, 0, "2026-07-01"),
    (2, 1, 1, 1, "2026-07-01"),
    (1, 6, 20, 0, "2026-07-02"),
    (1, 7, 3, 1, "2026-07-02"),
    (2, 8, 18, 0, "2026-07-02"),
    (1, 2, 10, 0, "2026-07-03"),
    (2, 11, 5, 0, "2026-07-03"),
)


def rebuild_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    original_db_path = create_db.DB_PATH
    create_db.DB_PATH = str(db_path)
    try:
        create_db.create_database()
    finally:
        create_db.DB_PATH = original_db_path

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        cur = conn.cursor()
        _clear_tables(cur)
        _insert_master_data(cur)
        _insert_test_data(cur)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _clear_tables(cur: sqlite3.Cursor) -> None:
    for table in (
        "purchase_order",
        "order_draft",
        "order_table",
        "posting_batch",
        "supplier_freq_product",
        "customer_freq_product",
        "customer_product",
        "customer_print_setting",
        "supplier",
        "product",
        "customer",
    ):
        cur.execute(f"DELETE FROM {table}")
    cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('purchase_order', 'order_draft', 'order_table', 'posting_batch')")


def _insert_master_data(cur: sqlite3.Cursor) -> None:
    cur.executemany(
        "INSERT INTO customer (id, car_number, name, checkout_code, phone1, phone2, market) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        CUSTOMERS,
    )
    cur.executemany(
        "INSERT INTO product (id, car_number, detailed_name, short_name, purchase_price, sale_price, safety_stock, return_unit, frequent) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        PRODUCTS,
    )
    cur.executemany(
        "INSERT INTO supplier (id, name, phone1, phone2) VALUES (?, ?, ?, ?)",
        SUPPLIERS,
    )
    cur.executemany(
        "INSERT INTO customer_freq_product (customer_id, product_id) VALUES (?, ?)",
        CUSTOMER_FREQ_PRODUCTS,
    )
    cur.executemany(
        "INSERT INTO customer_product (customer_id, product_id, sale_price) VALUES (?, ?, ?)",
        CUSTOMER_PRODUCT_PRICES,
    )
    cur.executemany(
        "INSERT INTO supplier_freq_product (supplier_id, product_id) VALUES (?, ?)",
        SUPPLIER_FREQ_PRODUCTS,
    )


def _insert_test_data(cur: sqlite3.Cursor) -> None:
    batches: dict[str, int] = {}
    for posted_date in POSTED_DATES:
        cur.execute(
            "INSERT INTO posting_batch (work_date, status, note, posted_at) "
            "VALUES (?, 'posted', 'customer order posting', ?)",
            (posted_date, f"{posted_date} 09:00:00"),
        )
        batches[posted_date] = int(cur.lastrowid)

    for order_date, customer_id, product_id, quantity, is_return in POSTED_ORDERS:
        purchase_price, sale_price = _prices_for(cur, customer_id, product_id)
        cur.execute(
            "INSERT INTO order_table ("
            "customer_id, product_id, quantity, order_date, is_return, "
            "posting_batch_id, purchase_price, sale_price, posted_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                customer_id,
                product_id,
                quantity,
                order_date,
                is_return,
                batches[order_date],
                purchase_price,
                sale_price,
                f"{order_date} 09:05:00",
            ),
        )

    draft_time = f"{DRAFT_WORK_DATE} 08:30:00"
    cur.executemany(
        "INSERT INTO order_draft (customer_id, product_id, quantity, is_return, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [(*row, draft_time, draft_time) for row in DRAFT_ORDERS],
    )

    cur.executemany(
        "INSERT INTO purchase_order (supplier_id, product_id, quantity, is_return, order_date) "
        "VALUES (?, ?, ?, ?, ?)",
        PURCHASE_ORDERS,
    )


def _prices_for(cur: sqlite3.Cursor, customer_id: int, product_id: int) -> tuple[int, int]:
    cur.execute(
        "SELECT p.purchase_price, COALESCE(cp.sale_price, p.sale_price) "
        "FROM product p "
        "LEFT JOIN customer_product cp ON cp.customer_id = ? AND cp.product_id = p.id "
        "WHERE p.id = ?",
        (customer_id, product_id),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"missing price data for customer={customer_id}, product={product_id}")
    return int(row[0]), int(row[1])


def verify_database(db_path: Path) -> list[str]:
    failures: list[str] = []
    if not db_path.exists():
        return [f"database does not exist: {db_path}"]

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        _expect_equal(failures, "customer count", _count(cur, "customer"), len(CUSTOMERS))
        _expect_equal(failures, "product count", _count(cur, "product"), len(PRODUCTS))
        _expect_equal(failures, "supplier count", _count(cur, "supplier"), len(SUPPLIERS))
        _expect_equal(failures, "posted order row count", _count(cur, "order_table"), len(POSTED_ORDERS))
        _expect_equal(failures, "draft order row count", _count(cur, "order_draft"), len(DRAFT_ORDERS))
        _expect_equal(failures, "posting batch count", _count(cur, "posting_batch"), len(POSTED_DATES))
        _expect_equal(failures, "purchase order row count", _count(cur, "purchase_order"), len(PURCHASE_ORDERS))

        _verify_master_names(cur, failures)
        _verify_posting_batches(cur, failures)
        _verify_posted_orders(cur, failures)
        _verify_drafts(cur, failures)
        _verify_purchase_orders(cur, failures)
        _verify_coverage(cur, failures)
    finally:
        conn.close()
    return failures


def _count(cur: sqlite3.Cursor, table: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return int(cur.fetchone()[0])


def _expect_equal(failures: list[str], label: str, actual: object, expected: object) -> None:
    if actual != expected:
        failures.append(f"{label}: expected {expected!r}, got {actual!r}")


def _verify_master_names(cur: sqlite3.Cursor, failures: list[str]) -> None:
    cur.execute("SELECT id, name FROM customer ORDER BY id")
    _expect_equal(failures, "customer names", tuple(cur.fetchall()), tuple((row[0], row[2]) for row in CUSTOMERS))
    cur.execute("SELECT id, short_name FROM product ORDER BY id")
    _expect_equal(failures, "product names", tuple(cur.fetchall()), tuple((row[0], row[3]) for row in PRODUCTS))
    cur.execute("SELECT id, name FROM supplier ORDER BY id")
    _expect_equal(failures, "supplier names", tuple(cur.fetchall()), tuple((row[0], row[1]) for row in SUPPLIERS))


def _verify_posting_batches(cur: sqlite3.Cursor, failures: list[str]) -> None:
    cur.execute("SELECT work_date, status, note FROM posting_batch ORDER BY work_date")
    expected = tuple((posted_date, "posted", "customer order posting") for posted_date in POSTED_DATES)
    _expect_equal(failures, "posting batches", tuple(cur.fetchall()), expected)

    cur.execute(
        "SELECT o.order_date, COUNT(DISTINCT o.posting_batch_id) "
        "FROM order_table o "
        "GROUP BY o.order_date "
        "ORDER BY o.order_date"
    )
    expected_batch_links = tuple((posted_date, 1) for posted_date in POSTED_DATES)
    _expect_equal(failures, "one posting batch per posted date", tuple(cur.fetchall()), expected_batch_links)


def _verify_posted_orders(cur: sqlite3.Cursor, failures: list[str]) -> None:
    cur.execute(
        "SELECT order_date, customer_id, product_id, quantity, COALESCE(is_return, 0) "
        "FROM order_table "
        "ORDER BY order_date, id"
    )
    actual = Counter(tuple(row) for row in cur.fetchall())
    expected = Counter(POSTED_ORDERS)
    _expect_equal(failures, "posted order details", actual, expected)

    cur.execute("SELECT COUNT(*) FROM order_table WHERE order_date = ?", (DRAFT_WORK_DATE,))
    _expect_equal(failures, "draft day is not posted", int(cur.fetchone()[0]), 0)

    cur.execute(
        "SELECT COUNT(*) "
        "FROM order_table o "
        "JOIN product p ON p.id = o.product_id "
        "LEFT JOIN customer_product cp ON cp.customer_id = o.customer_id AND cp.product_id = o.product_id "
        "WHERE o.posting_batch_id IS NULL "
        "   OR o.purchase_price IS NULL "
        "   OR o.sale_price IS NULL "
        "   OR o.posted_at IS NULL "
        "   OR o.purchase_price != p.purchase_price "
        "   OR o.sale_price != COALESCE(cp.sale_price, p.sale_price)"
    )
    _expect_equal(failures, "posted order price snapshots", int(cur.fetchone()[0]), 0)


def _verify_drafts(cur: sqlite3.Cursor, failures: list[str]) -> None:
    cur.execute(
        "SELECT customer_id, product_id, quantity, COALESCE(is_return, 0) "
        "FROM order_draft "
        "ORDER BY customer_id, product_id, is_return"
    )
    actual = Counter(tuple(row) for row in cur.fetchall())
    expected = Counter(DRAFT_ORDERS)
    _expect_equal(failures, "draft order details", actual, expected)

    cur.execute(
        "SELECT COUNT(*) FROM order_draft "
        "WHERE date(created_at) = ? AND date(updated_at) = ?",
        (DRAFT_WORK_DATE, DRAFT_WORK_DATE),
    )
    _expect_equal(failures, "draft timestamps", int(cur.fetchone()[0]), len(DRAFT_ORDERS))


def _verify_purchase_orders(cur: sqlite3.Cursor, failures: list[str]) -> None:
    cur.execute(
        "SELECT supplier_id, product_id, quantity, COALESCE(is_return, 0), order_date "
        "FROM purchase_order "
        "ORDER BY order_date, supplier_id, product_id, is_return"
    )
    actual = Counter(tuple(row) for row in cur.fetchall())
    expected = Counter(PURCHASE_ORDERS)
    _expect_equal(failures, "purchase order details", actual, expected)

    cur.execute("SELECT COUNT(DISTINCT supplier_id) FROM purchase_order")
    _expect_equal(failures, "purchase orders use both suppliers", int(cur.fetchone()[0]), len(SUPPLIERS))


def _verify_coverage(cur: sqlite3.Cursor, failures: list[str]) -> None:
    cur.execute("SELECT COUNT(DISTINCT customer_id) FROM order_table")
    _expect_equal(failures, "posted orders cover all customers", int(cur.fetchone()[0]), len(CUSTOMERS))

    cur.execute(
        "SELECT COUNT(DISTINCT product_id) FROM ("
        "  SELECT product_id FROM order_table "
        "  UNION ALL "
        "  SELECT product_id FROM order_draft "
        "  UNION ALL "
        "  SELECT product_id FROM purchase_order"
        ")"
    )
    _expect_equal(failures, "test cases cover all products", int(cur.fetchone()[0]), len(PRODUCTS))

    cur.execute("SELECT COUNT(*) FROM order_table WHERE COALESCE(is_return, 0) = 1")
    if int(cur.fetchone()[0]) < 3:
        failures.append("posted orders should include at least 3 return rows")

    cur.execute("SELECT COUNT(*) FROM order_draft WHERE COALESCE(is_return, 0) = 1")
    _expect_equal(failures, "draft orders include one return row", int(cur.fetchone()[0]), 1)


def print_summary(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        print(f"Database: {db_path}")
        for table in ("customer", "product", "supplier", "posting_batch", "order_table", "order_draft", "purchase_order"):
            print(f"{table}: {_count(cur, table)}")
        cur.execute(
            "SELECT order_date, COUNT(*), COUNT(DISTINCT customer_id), SUM(quantity) "
            "FROM order_table GROUP BY order_date ORDER BY order_date"
        )
        for order_date, rows, customers, quantity in cur.fetchall():
            print(f"posted {order_date}: rows={rows}, customers={customers}, quantity={quantity}")
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT customer_id), SUM(quantity) FROM order_draft")
        rows, customers, quantity = cur.fetchone()
        print(f"draft {DRAFT_WORK_DATE}: rows={rows}, customers={customers}, quantity={quantity}")
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild and verify NanoERP test cases with 3 posted days and 1 draft day."
    )
    parser.add_argument(
        "command",
        choices=("rebuild", "verify", "run"),
        help="rebuild fixture data, verify an existing database, or do both",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"database path (default: {DEFAULT_DB_PATH})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = args.db.expanduser().resolve()

    if args.command in ("rebuild", "run"):
        rebuild_database(db_path)
        print_summary(db_path)

    if args.command in ("verify", "run"):
        failures = verify_database(db_path)
        if failures:
            print("FAIL")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
