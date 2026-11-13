"""建表与三张表的增删改查。"""

from __future__ import annotations

import sqlite3

from src.database.connection import get_connection

_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY
)
"""

_CREATE_WATCHLIST = """
CREATE TABLE IF NOT EXISTS watchlist (
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    code    TEXT NOT NULL,
    name    TEXT NOT NULL,
    PRIMARY KEY (user_id, code)
)
"""

_CREATE_SCHEDULES = """
CREATE TABLE IF NOT EXISTS schedules (
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    hhmm    TEXT NOT NULL,
    PRIMARY KEY (user_id, hhmm)
)
"""

_ENSURE_USER = "INSERT OR IGNORE INTO users (user_id) VALUES (?)"


def init_db() -> None:
    """建立三张表。"""

    connection = get_connection()
    with connection:
        connection.execute(_CREATE_USERS)
        connection.execute(_CREATE_WATCHLIST)
        connection.execute(_CREATE_SCHEDULES)


def add_user(user_id: str) -> bool:
    """登记用户。True 表示新增，False 表示已存在。"""

    connection = get_connection()
    with connection:
        cursor = connection.execute(_ENSURE_USER, (user_id,))
    return cursor.rowcount > 0


def list_watch(user_id: str) -> list[tuple[str, str]]:
    """按添加顺序返回该用户的自选，元素为 (代码, 名称)。"""

    connection = get_connection()
    rows = connection.execute(
        "SELECT code, name FROM watchlist WHERE user_id = ? ORDER BY rowid",
        (user_id,),
    ).fetchall()
    return [(code, name) for code, name in rows]


def add_watch(user_id: str, code: str, name: str) -> bool:
    """新增自选。True 表示新增，False 表示已存在。"""

    connection = get_connection()
    try:
        with connection:
            connection.execute(_ENSURE_USER, (user_id,))
            connection.execute(
                "INSERT INTO watchlist (user_id, code, name) VALUES (?, ?, ?)",
                (user_id, code, name),
            )
    except sqlite3.IntegrityError:
        return False
    return True


def remove_watch(user_id: str, code: str) -> bool:
    """删除自选。True 表示已删除，False 表示不存在。"""

    connection = get_connection()
    with connection:
        cursor = connection.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND code = ?",
            (user_id, code),
        )
    return cursor.rowcount > 0


def list_user_schedules(user_id: str) -> list[str]:
    """按时间升序返回该用户的时间点。"""

    connection = get_connection()
    rows = connection.execute(
        "SELECT hhmm FROM schedules WHERE user_id = ? ORDER BY hhmm",
        (user_id,),
    ).fetchall()
    return [hhmm for (hhmm,) in rows]


def add_schedule(user_id: str, hhmm: str) -> bool:
    """新增定时。True 表示新增，False 表示已存在。"""

    connection = get_connection()
    try:
        with connection:
            connection.execute(_ENSURE_USER, (user_id,))
            connection.execute(
                "INSERT INTO schedules (user_id, hhmm) VALUES (?, ?)",
                (user_id, hhmm),
            )
    except sqlite3.IntegrityError:
        return False
    return True


def remove_schedule(user_id: str, hhmm: str) -> bool:
    """删除定时。True 表示已删除，False 表示不存在。"""

    connection = get_connection()
    with connection:
        cursor = connection.execute(
            "DELETE FROM schedules WHERE user_id = ? AND hhmm = ?",
            (user_id, hhmm),
        )
    return cursor.rowcount > 0


def list_all_schedules() -> list[tuple[str, str]]:
    """返回全部定时记录，元素为 (用户 id, 时间点)。"""

    connection = get_connection()
    rows = connection.execute(
        "SELECT user_id, hhmm FROM schedules ORDER BY user_id, hhmm"
    ).fetchall()
    return [(user_id, hhmm) for user_id, hhmm in rows]
