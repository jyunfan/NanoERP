import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "db.sql")


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
            return_unit TEXT
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
            posted BOOLEAN DEFAULT 0,
            FOREIGN KEY (customer_id) REFERENCES customer(id),
            FOREIGN KEY (product_id) REFERENCES product(id)
        )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_database()
    print(f"Database created at {DB_PATH}")
