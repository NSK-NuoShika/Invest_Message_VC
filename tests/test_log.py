import re
import threading
from datetime import datetime
from pathlib import Path

from src.log import _LOCK, larkbot_log, schedule_log, task_log

LOG_DIR = Path(__file__).resolve().parents[1] / "log"

TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


def _reset(path: Path) -> None:
    path.write_text("", encoding="utf-8")


def _lines(path: Path) -> list[list[str]]:
    raw = path.read_text(encoding="utf-8").splitlines()
    return [line.split(" ") for line in raw if line]


def _assert_timestamp(fields: list[str]) -> None:
    assert TIMESTAMP_RE.match(fields[0])
    datetime.strptime(fields[0], "%Y-%m-%dT%H:%M:%S")


def test_three_modules_share_one_lock() -> None:
    assert larkbot_log._LOCK is _LOCK
    assert schedule_log._LOCK is _LOCK
    assert task_log._LOCK is _LOCK


def test_receive() -> None:
    path = LOG_DIR / "larkbot.log"
    _reset(path)
    larkbot_log.receive("http://127.0.0.1:9001/query", "ou_1", 200, 0)
    fields = _lines(path)
    assert len(fields) == 1
    row = fields[0]
    assert len(row) == 6
    _assert_timestamp(row)
    assert row[1:] == ["RECEIVE", "http://127.0.0.1:9001/query", "ou_1", "200", "0"]


def test_send() -> None:
    path = LOG_DIR / "larkbot.log"
    _reset(path)
    larkbot_log.send("http://127.0.0.1:8000/send/file", "FILE", "ou_1", 200, 0)
    row = _lines(path)[0]
    assert len(row) == 7
    assert row[1:] == ["SEND", "http://127.0.0.1:8000/send/file", "FILE", "ou_1", "200", "0"]


def test_send_timeout_has_single_status() -> None:
    path = LOG_DIR / "larkbot.log"
    _reset(path)
    larkbot_log.send("http://127.0.0.1:8000/send/text", "TEXT", "ou_1", "TIMEOUT", "TIMEOUT")
    row = _lines(path)[0]
    assert len(row) == 6
    assert row[-1] == "TIMEOUT"
    assert row[-2] == "ou_1"


def test_register() -> None:
    path = LOG_DIR / "larkbot.log"
    _reset(path)
    larkbot_log.register(
        "http://127.0.0.1:8000/register",
        "基金",
        "查询",
        "/query",
        "http://127.0.0.1:9001",
        200,
        0,
    )
    row = _lines(path)[0]
    assert len(row) == 9
    assert row[1:] == [
        "REGISTER",
        "http://127.0.0.1:8000/register",
        "基金",
        "查询",
        "/query",
        "http://127.0.0.1:9001",
        "200",
        "0",
    ]


def test_heartbeat() -> None:
    path = LOG_DIR / "larkbot.log"
    _reset(path)
    larkbot_log.heartbeat("http://127.0.0.1:8000/heartbeat", 200, 0)
    row = _lines(path)[0]
    assert len(row) == 5
    assert row[1:] == ["HEARTBEAT", "http://127.0.0.1:8000/heartbeat", "200", "0"]


def test_schedule_log() -> None:
    path = LOG_DIR / "schedule.log"
    _reset(path)
    schedule_log.add("ou_1", "09:30")
    schedule_log.delete("ou_1", "09:30")
    schedule_log.trigger("ou_2", "21:00")
    rows = _lines(path)
    assert [row[1:] for row in rows] == [
        ["ADD", "ou_1", "09:30"],
        ["DEL", "ou_1", "09:30"],
        ["TRIGGER", "ou_2", "21:00"],
    ]
    for row in rows:
        assert len(row) == 4
        _assert_timestamp(row)


def test_task_log() -> None:
    path = LOG_DIR / "task.log"
    _reset(path)
    task_log.fetch("000001", 717, "OK")
    task_log.pdf(42593, 250, "FAIL")
    rows = _lines(path)
    assert [row[1:] for row in rows] == [
        ["FETCH", "000001", "717", "OK"],
        ["PDF", "42593", "250", "FAIL"],
    ]
    for row in rows:
        assert len(row) == 5
        _assert_timestamp(row)


def test_concurrent_writes_do_not_interleave() -> None:
    larkbot_path = LOG_DIR / "larkbot.log"
    schedule_path = LOG_DIR / "schedule.log"
    task_path = LOG_DIR / "task.log"
    for path in (larkbot_path, schedule_path, task_path):
        _reset(path)

    rounds = 40
    threads_count = 6

    def worker(index: int) -> None:
        for _ in range(rounds):
            larkbot_log.heartbeat("http://127.0.0.1:8000/heartbeat", 200, 0)
            schedule_log.trigger(f"ou_{index}", "09:30")
            task_log.fetch("000001", 1, "OK")

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(threads_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    heartbeat_rows = _lines(larkbot_path)
    schedule_rows = _lines(schedule_path)
    task_rows = _lines(task_path)
    assert len(heartbeat_rows) == rounds * threads_count
    assert len(schedule_rows) == rounds * threads_count
    assert len(task_rows) == rounds * threads_count
    for row in heartbeat_rows:
        assert len(row) == 5
        assert row[1] == "HEARTBEAT"
    for row in schedule_rows:
        assert len(row) == 4
        assert row[1] == "TRIGGER"
    for row in task_rows:
        assert len(row) == 5
        assert row[1] == "FETCH"
