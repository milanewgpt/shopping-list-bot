"""SQLite storage for shopping list items."""

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from bot.config import DB_PATH, logger

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    raw_text    TEXT    NOT NULL,
    normalized  TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_items_user ON items (user_id);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(_CREATE_TABLE)
        conn.execute(_CREATE_INDEX)
    logger.info("Database initialized at %s", DB_PATH)


def get_existing_normalized(user_id: int) -> set[str]:
    """Return set of normalized item names already in the user's list."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT normalized FROM items WHERE user_id = ?", (user_id,)
        ).fetchall()
    return {r["normalized"] for r in rows}


def add_item(
    user_id: int, raw_text: str, normalized: str, category: str
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO items (user_id, raw_text, normalized, category, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, raw_text, normalized, category, now),
        )


def get_items_by_category(user_id: int) -> dict[str, list[str]]:
    """Return {category: [raw_text, ...]} for the given user."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT raw_text, category FROM items WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
    result: dict[str, list[str]] = {}
    for r in rows:
        result.setdefault(r["category"], []).append(r["raw_text"])
    return result


def remove_by_category(user_id: int, category: str) -> list[tuple[str, str, str]]:
    """Delete all items in a category. Return list of (raw_text, normalized, category)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT raw_text, normalized, category FROM items "
            "WHERE user_id = ? AND category = ?",
            (user_id, category),
        ).fetchall()
        conn.execute(
            "DELETE FROM items WHERE user_id = ? AND category = ?",
            (user_id, category),
        )
    return [(r["raw_text"], r["normalized"], r["category"]) for r in rows]


def remove_items(user_id: int, normalized_names: list[str]) -> list[tuple[str, str, str]]:
    """Delete specific items by normalized name. Return list of (raw_text, normalized, category)."""
    if not normalized_names:
        return []
    removed: list[tuple[str, str, str]] = []
    with _connect() as conn:
        for name in normalized_names:
            rows = conn.execute(
                "SELECT raw_text, normalized, category FROM items "
                "WHERE user_id = ? AND normalized = ?",
                (user_id, name),
            ).fetchall()
            if rows:
                conn.execute(
                    "DELETE FROM items WHERE user_id = ? AND normalized = ?",
                    (user_id, name),
                )
                removed.extend(
                    (r["raw_text"], r["normalized"], r["category"]) for r in rows
                )
    return removed


def clear_items(user_id: int) -> list[tuple[str, str, str]]:
    """Delete all items for the user. Return list of (raw_text, normalized, category)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT raw_text, normalized, category FROM items WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        conn.execute("DELETE FROM items WHERE user_id = ?", (user_id,))
    return [(r["raw_text"], r["normalized"], r["category"]) for r in rows]


def restore_items(user_id: int, items: list[tuple[str, str, str]]) -> int:
    """Re-insert previously deleted items. Return count of restored rows."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        for raw_text, normalized, category in items:
            conn.execute(
                "INSERT INTO items (user_id, raw_text, normalized, category, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, raw_text, normalized, category, now),
            )
    return len(items)
