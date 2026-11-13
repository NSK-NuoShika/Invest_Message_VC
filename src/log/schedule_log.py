"""写 log/schedule.log，记录定时任务的设置与触发。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TextIO

from src.log import _LOCK

_LOG_DIR = Path(__file__).resolve().parents[2] / "log"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_STREAM: TextIO = (_LOG_DIR / "schedule.log").open("a", encoding="utf-8", newline="\n")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _write(event: str, user_id: str, hhmm: str) -> None:
    line = " ".join([_now(), event, user_id, hhmm])
    with _LOCK:
        _STREAM.write(line + "\n")
        _STREAM.flush()


def add(user_id: str, hhmm: str) -> None:
    """用户新增定时任务。"""

    _write("ADD", user_id, hhmm)


def delete(user_id: str, hhmm: str) -> None:
    """用户删除定时任务。"""

    _write("DEL", user_id, hhmm)


def trigger(user_id: str, hhmm: str) -> None:
    """定时任务到点触发。"""

    _write("TRIGGER", user_id, hhmm)
