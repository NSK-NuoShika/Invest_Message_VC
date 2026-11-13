"""建立并配置数据库连接。"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "invest_message.db"

_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """返回当前线程的数据库连接，每线程一条。"""

    connection: sqlite3.Connection | None = getattr(_local, "conn", None)
    if connection is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(DB_PATH, timeout=5.0)
        connection.execute("PRAGMA foreign_keys = ON")
        _local.conn = connection
    return connection
