from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "school_bot.db"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                class_name TEXT
            )
            """
        )
        conn.commit()


def save_user(user_id: int, username: str | None, first_name: str | None) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (user_id, username, first_name),
        )
        conn.commit()


def save_class(user_id: int, class_name: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, class_name)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                class_name = excluded.class_name
            """,
            (user_id, class_name),
        )
        conn.commit()


def get_class(user_id: int) -> str | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT class_name FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return row[0] if row and row[0] else None
