import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
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
            id SERIAL PRIMARY KEY,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            balance BIGINT DEFAULT 0,
            created_at TIMESTAMP NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            price BIGINT NOT NULL,
            active BOOLEAN DEFAULT TRUE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            package_id INTEGER REFERENCES packages(id),
            user_number TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP NOT NULL
        )
        """)

        cur.execute("SELECT COUNT(*) FROM packages")
        if cur.fetchone()["count"] == 0:
            cur.executemany(
                "INSERT INTO packages(name, price, active) VALUES (%s,%s,TRUE)",
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

def create_user(phone, password_hash):
    with get_conn() as c:
        c.cursor().execute(
            "INSERT INTO users(phone,password_hash,balance,created_at) VALUES (%s,%s,0,%s)",
            (phone, password_hash, datetime.utcnow()),
        )

def get_user_by_phone(phone):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE phone=%s", (phone,))
        return cur.fetchone()

def get_user_by_id(uid):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
        return cur.fetchone()

def add_balance(phone, amt):
    with get_conn() as c:
        c.cursor().execute(
            "UPDATE users SET balance = balance + %s WHERE phone=%s",
            (amt, phone),
        )

def deduct_balance(phone, amt):
    with get_conn() as c:
        c.cursor().execute(
            "UPDATE users SET balance = balance - %s WHERE phone=%s",
            (amt, phone),
        )

def list_packages(active_only=True):
    with get_conn() as c:
        cur = c.cursor()
        if active_only:
            cur.execute("SELECT * FROM packages WHERE active=TRUE ORDER BY price")
        else:
            cur.execute("SELECT * FROM packages ORDER BY price")
        return cur.fetchall()

def create_order(user_id, package_id, user_number):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO orders(user_id,package_id,user_number,status,created_at)
               VALUES (%s,%s,%s,'pending',%s) RETURNING id""",
            (user_id, package_id, user_number, datetime.utcnow()),
        )
        return cur.fetchone()["id"]
