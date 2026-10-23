import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


DB_PATH = Path(__file__).resolve().with_name("campus_market.db")

SAMPLE_ITEMS = [
    ("高数教材（九成新）", "教材资料", 20.0, "小林", "九成新，笔记不多。"),
    ("宿舍台灯，可调亮度", "生活用品", 15.0, "阿明", "功能正常，搬宿舍闲置。"),
    ("闲置篮球一个", "运动户外", 35.0, "同学", "保存良好。"),
    ("无线鼠标，功能正常", "数码产品", 25.0, "小周", "含接收器，正常使用。"),
]


def database_url():
    return os.getenv("DATABASE_URL", "").strip()


def using_postgres():
    return bool(database_url())


@contextmanager
def connect():
    url = database_url()
    if url:
        import psycopg
        from psycopg.rows import dict_row

        if "sslmode=" not in url:
            url += "&sslmode=require" if "?" in url else "?sslmode=require"
        connection = psycopg.connect(url, row_factory=dict_row, connect_timeout=10)
    else:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _query(sql):
    if using_postgres():
        return sql.replace("?", "%s")
    return sql


def init_db():
    if using_postgres():
        create_table = """
            CREATE TABLE IF NOT EXISTS products (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price DOUBLE PRECISION NOT NULL CHECK(price >= 0),
                seller TEXT NOT NULL,
                seller_email TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """
    else:
        create_table = """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL CHECK(price >= 0),
                seller TEXT NOT NULL,
                seller_email TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """

    with connect() as connection:
        connection.execute(create_table)
        count = connection.execute("SELECT COUNT(*) AS item_count FROM products").fetchone()["item_count"]
        if count == 0:
            seed_query = _query(
                "INSERT INTO products (name, category, price, seller, description) VALUES (?, ?, ?, ?, ?)"
            )
            if using_postgres():
                with connection.cursor() as cursor:
                    cursor.executemany(seed_query, SAMPLE_ITEMS)
            else:
                connection.executemany(seed_query, SAMPLE_ITEMS)


def list_items():
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, name, category, price, seller, description FROM products ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def create_item(name, category, price, seller, seller_email, description):
    with connect() as connection:
        connection.execute(
            _query("""
            INSERT INTO products (name, category, price, seller, seller_email, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """),
            (name, category, price, seller, seller_email, description),
        )
