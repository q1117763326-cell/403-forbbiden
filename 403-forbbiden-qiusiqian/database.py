import hashlib
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path


DB_PATH = Path(__file__).resolve().with_name("campus_market.db")

logger = logging.getLogger(__name__)

SAMPLE_ITEMS = [
    ("高数教材（九成新）", "教材资料", 20.0, "小林", "九成新，笔记不多。"),
    ("宿舍台灯，可调亮度", "生活用品", 15.0, "阿明", "功能正常，搬宿舍闲置。"),
    ("闲置篮球一个", "运动户外", 35.0, "同学", "保存良好。"),
    ("无线鼠标，功能正常", "数码产品", 25.0, "小周", "含接收器，正常使用。"),
]

CONTACT_MAX_LENGTH = 40
_CONTACT_LINK_PREFIXES = ("http://", "https://", "mailto:")
_CONTACT_BLOCKED_PREFIXES = ("javascript:", "data:")

# Per-email limits, and a global cap that protects the shared SMTP account.
VERIFICATION_WINDOWS = ((60, 1), (3600, 5), (86400, 10))
VERIFICATION_GLOBAL_WINDOW = 3600
VERIFICATION_GLOBAL_LIMIT = 100

_schema_ready = False
_schema_lock = threading.Lock()
_verification_lock = threading.Lock()


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
        connection = sqlite3.connect(DB_PATH, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")

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


def normalize_contact(value):
    """Return a trimmed, safe contact value or raise ValueError."""
    contact = "" if value is None else str(value).strip()
    if len(contact) > CONTACT_MAX_LENGTH:
        raise ValueError(f"联系方式不能超过 {CONTACT_MAX_LENGTH} 个字符。")
    if contact.lower().startswith(_CONTACT_BLOCKED_PREFIXES):
        raise ValueError("联系方式格式无效，请填写链接或微信号。")
    return contact


def is_contact_link(contact):
    """Only http(s) and mailto contacts are rendered as clickable links."""
    return str(contact or "").strip().lower().startswith(_CONTACT_LINK_PREFIXES)


def _ensure_product_columns(connection):
    """Add new product columns to databases created by older releases."""
    if using_postgres():
        connection.execute(
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS contact TEXT NOT NULL DEFAULT ''"
        )
        connection.execute(
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'available'"
        )
        return

    existing_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(products)").fetchall()
    }
    if "contact" not in existing_columns:
        connection.execute(
            "ALTER TABLE products ADD COLUMN contact TEXT NOT NULL DEFAULT ''"
        )
    if "status" not in existing_columns:
        connection.execute(
            "ALTER TABLE products ADD COLUMN status TEXT NOT NULL DEFAULT 'available'"
        )


def init_db():
    if using_postgres():
        create_products = """
            CREATE TABLE IF NOT EXISTS products (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price DOUBLE PRECISION NOT NULL CHECK(price >= 0),
                seller TEXT NOT NULL,
                seller_email TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                contact TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'available',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """
        create_verification_log = """
            CREATE TABLE IF NOT EXISTS verification_log (
                id BIGSERIAL PRIMARY KEY,
                email_hash TEXT NOT NULL,
                created_at BIGINT NOT NULL
            )
        """
    else:
        create_products = """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL CHECK(price >= 0),
                seller TEXT NOT NULL,
                seller_email TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                contact TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'available',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
        create_verification_log = """
            CREATE TABLE IF NOT EXISTS verification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """

    with connect() as connection:
        connection.execute(create_products)
        connection.execute(create_verification_log)
        _ensure_product_columns(connection)
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_products_status ON products (status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_verification_log_email_created "
            "ON verification_log (email_hash, created_at)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_verification_log_created "
            "ON verification_log (created_at)"
        )
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


def ensure_schema():
    """Create the schema once per process so deep links work on a cold start."""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        try:
            init_db()
        except Exception:
            logger.exception("Failed to initialize the database schema")
            raise
        _schema_ready = True


def list_items(include_sold=False, viewer_email=None, limit=200):
    """List products, hiding sold items and capping the rendered result set.

    seller_email is never selected. It is only compared in SQL to expose a
    boolean is_mine flag for the current viewer. Pass limit=None for no cap.
    """
    ensure_schema()
    where_clause = "" if include_sold else "WHERE status = 'available'"
    viewer = str(viewer_email).strip() if viewer_email else None
    params = [viewer]
    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT ?"
        params.append(max(0, int(limit)))
    try:
        with connect() as connection:
            rows = connection.execute(
                _query(f"""
                SELECT id, name, category, price, seller, description, contact, status,
                       (seller_email = ?) AS is_mine
                FROM products
                {where_clause}
                ORDER BY id DESC
                {limit_clause}
                """),
                tuple(params),
            ).fetchall()
            items = []
            for row in rows:
                item = dict(row)
                item["is_mine"] = bool(item.get("is_mine"))
                items.append(item)
            return items
    except Exception:
        logger.exception("Failed to list products")
        raise


def create_item(name, category, price, seller, seller_email, description, contact=""):
    ensure_schema()
    contact = normalize_contact(contact)
    try:
        with connect() as connection:
            connection.execute(
                _query("""
                INSERT INTO products (name, category, price, seller, seller_email, description, contact)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """),
                (name, category, price, seller, seller_email, description, contact),
            )
    except Exception:
        logger.exception("Failed to create a product")
        raise


def mark_item_sold(item_id, seller_email):
    """Mark an available item sold only when the viewer owns it."""
    ensure_schema()
    owner_email = str(seller_email or "").strip()
    if not owner_email:
        return False
    try:
        with connect() as connection:
            cursor = connection.execute(
                _query(
                    "UPDATE products SET status = 'sold' "
                    "WHERE id = ? AND seller_email = ? AND status = 'available'"
                ),
                (item_id, owner_email),
            )
            return cursor.rowcount > 0
    except Exception:
        logger.exception("Failed to mark a product as sold")
        raise


def get_item_stats():
    """Return totals for About/statistics without exposing seller_email."""
    ensure_schema()
    try:
        with connect() as connection:
            row = connection.execute("""
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END), 0) AS available,
                       COUNT(DISTINCT category) AS categories
                FROM products
            """).fetchone()
            return {
                "total": int(row["total"]),
                "available": int(row["available"]),
                "categories": int(row["categories"]),
            }
    except Exception:
        logger.exception("Failed to load product statistics")
        raise


def _email_digest(email):
    """Hash the address so the rate-limit log never stores a plaintext email."""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def check_and_log_verification(email):
    """Return False when a verification-code request exceeds the server limits.

    A request is recorded even if the later SMTP delivery fails, so repeated
    failures cannot be used to keep sending mail.
    """
    digest = _email_digest(email)
    now = int(time.time())

    try:
        with _verification_lock:
            with connect() as connection:
                for window, limit in VERIFICATION_WINDOWS:
                    count = connection.execute(
                        _query(
                            "SELECT COUNT(*) AS request_count FROM verification_log "
                            "WHERE email_hash = ? AND created_at > ?"
                        ),
                        (digest, now - window),
                    ).fetchone()["request_count"]
                    if count >= limit:
                        return False

                global_count = connection.execute(
                    _query(
                        "SELECT COUNT(*) AS request_count FROM verification_log "
                        "WHERE created_at > ?"
                    ),
                    (now - VERIFICATION_GLOBAL_WINDOW,),
                ).fetchone()["request_count"]
                if global_count >= VERIFICATION_GLOBAL_LIMIT:
                    return False

                connection.execute(
                    _query(
                        "INSERT INTO verification_log (email_hash, created_at) VALUES (?, ?)"
                    ),
                    (digest, now),
                )
                return True
    except Exception:
        logger.exception("Failed to check or record the verification rate limit")
        return False
