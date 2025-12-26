import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "app.db"

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as c:
        cur = c.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            balance INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            active INTEGER DEFAULT 1
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            package_id INTEGER NOT NULL,
            user_number TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(package_id) REFERENCES packages(id)
        )
        """)

        count = cur.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
        if count == 0:
            cur.executemany(
                "INSERT INTO packages(name, price, active) VALUES(?,?,1)",
                [
                    ("11 GB", 870000),
                    ("22 GB", 1200000),
                    ("33 GB", 1450000),
                    ("44 GB", 1860000),
                    ("55 GB", 2280000),
                ],
            )

def fmt_lbp(amount: int) -> str:
    return f"{amount:,}"

# ---------- USERS ----------
def create_user(phone: str, password_hash: str):
    with get_conn() as c:
        c.execute(
            "INSERT INTO users(phone, password_hash, balance, created_at) VALUES(?,?,0,?)",
            (phone, password_hash, datetime.utcnow().isoformat()),
        )

def get_user_by_phone(phone: str):
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()

def get_user_by_id(uid: int):
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

def add_balance(phone: str, delta: int):
    with get_conn() as c:
        c.execute("UPDATE users SET balance = balance + ? WHERE phone=?", (delta, phone))

def deduct_balance(phone: str, delta: int):
    with get_conn() as c:
        c.execute("UPDATE users SET balance = balance - ? WHERE phone=?", (delta, phone))

# ---------- PACKAGES ----------
def list_packages(active_only=True):
    with get_conn() as c:
        if active_only:
            return c.execute(
                "SELECT id,name,price FROM packages WHERE active=1 ORDER BY price"
            ).fetchall()
        return c.execute(
            "SELECT id,name,price,active FROM packages ORDER BY price"
        ).fetchall()

def get_package(pid: int):
    with get_conn() as c:
        return c.execute("SELECT * FROM packages WHERE id=?", (pid,)).fetchone()

# ---------- ORDERS ----------
def create_order(user_id: int, package_id: int, user_number: str) -> int:
    with get_conn() as c:
        c.execute(
            """INSERT INTO orders(user_id, package_id, user_number, status, created_at)
               VALUES (?,?,?,?,?)""",
            (user_id, package_id, user_number, "pending", datetime.utcnow().isoformat()),
        )
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def get_order(oid: int):
    with get_conn() as c:
        return c.execute(
            """SELECT o.id, o.status,
                      o.user_number,
                      u.phone, u.balance,
                      p.name AS package_name, p.price AS package_price
               FROM orders o
               JOIN users u ON u.id=o.user_id
               JOIN packages p ON p.id=o.package_id
               WHERE o.id=?""",
            (oid,),
        ).fetchone()

def update_order_status(oid: int, status: str):
    with get_conn() as c:
        c.execute("UPDATE orders SET status=? WHERE id=?", (status, oid))

def list_user_orders(user_id: int, limit=20):
    with get_conn() as c:
        return c.execute(
            """SELECT o.id, o.status,
                      o.user_number,
                      p.name AS package_name, p.price AS package_price
               FROM orders o
               JOIN packages p ON p.id=o.package_id
               WHERE o.user_id=?
               ORDER BY o.id DESC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()
