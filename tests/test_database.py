import sqlite3
import threading
from pathlib import Path

import pytest

from database import connection, db


@pytest.fixture
def temp_db(tmp_path: Path, monkeypatch, request):
    def _clear() -> None:
        conn = getattr(connection._local, "conn", None)
        if conn is not None:
            conn.close()
            del connection._local.conn

    _clear()
    db_path = tmp_path / "data" / "test.db"
    monkeypatch.setattr(connection, "DB_PATH", db_path)
    db.init_db()
    yield db_path
    _clear()


def test_tables_created(temp_db: Path) -> None:
    rows = connection.get_connection().execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    names = [name for (name,) in rows]
    assert names == ["schedules", "users", "watchlist"]
    assert temp_db.parent.is_dir()


def test_init_db_is_idempotent(temp_db: Path) -> None:
    db.init_db()
    db.init_db()
    db.add_watch("ou_1", "000001", "华夏成长")
    assert db.list_watch("ou_1") == [("000001", "华夏成长")]


def test_add_user(temp_db: Path) -> None:
    assert db.add_user("ou_1") is True
    assert db.add_user("ou_1") is False


def test_add_watch_returns_true_then_false(temp_db: Path) -> None:
    assert db.add_watch("ou_1", "000001", "华夏成长") is True
    assert db.add_watch("ou_1", "000001", "华夏成长") is False
    assert db.list_watch("ou_1") == [("000001", "华夏成长")]


def test_watch_keeps_insert_order(temp_db: Path) -> None:
    for code, name in [("000003", "丙"), ("000001", "甲"), ("000002", "乙")]:
        db.add_watch("ou_1", code, name)
    assert db.list_watch("ou_1") == [("000003", "丙"), ("000001", "甲"), ("000002", "乙")]


def test_remove_watch(temp_db: Path) -> None:
    db.add_watch("ou_1", "000001", "华夏成长")
    assert db.remove_watch("ou_1", "000001") is True
    assert db.remove_watch("ou_1", "000001") is False
    assert db.list_watch("ou_1") == []


def test_watch_isolated_between_users(temp_db: Path) -> None:
    db.add_watch("ou_1", "000001", "甲")
    db.add_watch("ou_2", "000002", "乙")
    assert db.list_watch("ou_1") == [("000001", "甲")]
    assert db.list_watch("ou_2") == [("000002", "乙")]
    assert db.remove_watch("ou_2", "000001") is False


def test_schedules_sorted_and_idempotent(temp_db: Path) -> None:
    assert db.add_schedule("ou_1", "21:00") is True
    assert db.add_schedule("ou_1", "09:30") is True
    assert db.add_schedule("ou_1", "09:30") is False
    assert db.list_user_schedules("ou_1") == ["09:30", "21:00"]


def test_remove_schedule(temp_db: Path) -> None:
    db.add_schedule("ou_1", "09:30")
    assert db.remove_schedule("ou_1", "09:30") is True
    assert db.remove_schedule("ou_1", "09:30") is False
    assert db.list_user_schedules("ou_1") == []


def test_list_all_schedules(temp_db: Path) -> None:
    db.add_schedule("ou_2", "21:00")
    db.add_schedule("ou_1", "21:00")
    db.add_schedule("ou_1", "09:30")
    assert db.list_all_schedules() == [
        ("ou_1", "09:30"),
        ("ou_1", "21:00"),
        ("ou_2", "21:00"),
    ]


def test_foreign_keys_enabled(temp_db: Path) -> None:
    conn = connection.get_connection()
    assert conn.execute("PRAGMA foreign_keys").fetchone() == (1,)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO watchlist (user_id, code, name) VALUES ('ghost', '000001', '甲')"
        )
    conn.rollback()


def test_connection_is_per_thread(temp_db: Path) -> None:
    main_conn = connection.get_connection()
    assert connection.get_connection() is main_conn

    same_as_main: list[bool] = []

    def use_in_thread() -> None:
        thread_conn = connection.get_connection()
        same_as_main.append(thread_conn is main_conn)
        thread_conn.close()

    thread = threading.Thread(target=use_in_thread)
    thread.start()
    thread.join()

    assert same_as_main == [False]
