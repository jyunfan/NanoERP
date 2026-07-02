import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "db.sql")


def _table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cur.fetchone() is not None


def _column_exists(cur: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    cur.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cur.fetchall())


def _add_column_if_missing(
    cur: sqlite3.Cursor,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    if not _column_exists(cur, table_name, column_name):
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")


def _create_indexes(cur: sqlite3.Cursor) -> None:
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_draft_customer
        ON order_draft (customer_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_table_date_customer
        ON order_table (order_date, customer_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_posting_batch_date
        ON posting_batch (work_date)
    """)


def _rebuild_order_table_without_posted(cur: sqlite3.Cursor) -> None:
    if not _table_exists(cur, "order_table"):
        return
    if not _column_exists(cur, "order_table", "posted"):
        return

    cur.execute("""
        CREATE TABLE order_table_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            order_date DATE,
            is_return BOOLEAN,
            posting_batch_id INTEGER,
            purchase_price INTEGER,
            sale_price INTEGER,
            posted_at TEXT,
            FOREIGN KEY (customer_id) REFERENCES customer(id),
            FOREIGN KEY (product_id) REFERENCES product(id),
            FOREIGN KEY (posting_batch_id) REFERENCES posting_batch(id)
        )
    """)
    cur.execute("""
        INSERT INTO order_table_new (
            id, customer_id, product_id, quantity, order_date, is_return,
            posting_batch_id, purchase_price, sale_price, posted_at
        )
        SELECT
            id, customer_id, product_id, quantity, order_date, is_return,
            posting_batch_id, purchase_price, sale_price,
            COALESCE(
                posted_at,
                CASE WHEN order_date IS NOT NULL THEN CURRENT_TIMESTAMP ELSE NULL END
            )
        FROM order_table
    """)
    cur.execute("DROP TABLE order_table")
    cur.execute("ALTER TABLE order_table_new RENAME TO order_table")


def create_database():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer (
            id INTEGER PRIMARY KEY,
            car_number INTEGER,
            name TEXT,
            checkout_code INTEGER,
            phone1 TEXT,
            phone2 TEXT,
            market INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS product (
            id INTEGER PRIMARY KEY,
            car_number INTEGER,
            detailed_name TEXT,
            short_name TEXT,
            purchase_price INTEGER,
            sale_price INTEGER,
            safety_stock INTEGER,
            return_unit TEXT,
            frequent BOOLEAN DEFAULT 0
        )
    """)

    try:
        cur.execute("ALTER TABLE product ADD COLUMN frequent BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS supplier (
            id INTEGER PRIMARY KEY,
            name TEXT,
            phone1 TEXT,
            phone2 TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            order_date DATE,
            is_return BOOLEAN,
            posting_batch_id INTEGER,
            purchase_price INTEGER,
            sale_price INTEGER,
            posted_at TEXT,
            FOREIGN KEY (customer_id) REFERENCES customer(id),
            FOREIGN KEY (product_id) REFERENCES product(id),
            FOREIGN KEY (posting_batch_id) REFERENCES posting_batch(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_draft (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            is_return BOOLEAN NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(customer_id, product_id, is_return),
            FOREIGN KEY (customer_id) REFERENCES customer(id),
            FOREIGN KEY (product_id) REFERENCES product(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS posting_batch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'posted',
            note TEXT,
            posted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_product (
            customer_id INTEGER,
            product_id INTEGER,
            sale_price INTEGER,
            PRIMARY KEY (customer_id, product_id),
            FOREIGN KEY (customer_id) REFERENCES customer(id),
            FOREIGN KEY (product_id) REFERENCES product(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_freq_product (
            customer_id INTEGER,
            product_id INTEGER,
            PRIMARY KEY (customer_id, product_id),
            FOREIGN KEY (customer_id) REFERENCES customer(id),
            FOREIGN KEY (product_id) REFERENCES product(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_print_setting (
            report_type TEXT NOT NULL,
            customer_id INTEGER NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT 0,
            PRIMARY KEY (report_type, customer_id),
            FOREIGN KEY (customer_id) REFERENCES customer(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS supplier_freq_product (
            supplier_id INTEGER,
            product_id INTEGER,
            PRIMARY KEY (supplier_id, product_id),
            FOREIGN KEY (supplier_id) REFERENCES supplier(id),
            FOREIGN KEY (product_id) REFERENCES product(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS purchase_order (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            is_return BOOLEAN DEFAULT 0,
            order_date DATE,
            FOREIGN KEY (supplier_id) REFERENCES supplier(id),
            FOREIGN KEY (product_id) REFERENCES product(id)
        )
    """)

    # Existing databases may have been created before these columns/tables
    # existed. Keep this migration idempotent so app startup can call it safely.
    if _table_exists(cur, "order_table"):
        _add_column_if_missing(
            cur, "order_table", "posting_batch_id", "posting_batch_id INTEGER"
        )
        _add_column_if_missing(
            cur, "order_table", "purchase_price", "purchase_price INTEGER"
        )
        _add_column_if_missing(cur, "order_table", "sale_price", "sale_price INTEGER")
        _add_column_if_missing(cur, "order_table", "posted_at", "posted_at TEXT")

    cur.execute("DROP INDEX IF EXISTS idx_posting_batch_detail")
    cur.execute("DROP TABLE IF EXISTS posting")
    _rebuild_order_table_without_posted(cur)

    _create_indexes(cur)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_database()
    print(f"Database created at {DB_PATH}")
