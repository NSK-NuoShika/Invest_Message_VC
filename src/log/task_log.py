"""写 log/task.log，记录基金取数与 PDF 生成。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TextIO

from src.log import _LOCK

_LOG_DIR = Path(__file__).resolve().parents[2] / "log"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_STREAM: TextIO = (_LOG_DIR / "task.log").open("a", encoding="utf-8", newline="\n")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _write(fields: list[str]) -> None:
    line = " ".join(fields)
    with _LOCK:
        _STREAM.write(line + "\n")
        _STREAM.flush()


def fetch(code: str, elapsed_ms: int, result: str) -> None:
    """一次基金取数的结果。result 只取 OK 或 FAIL。"""

    _write([_now(), "FETCH", code, str(elapsed_ms), result])


def pdf(byte_size: int, elapsed_ms: int, result: str) -> None:
    """一次 PDF 生成的结果。result 只取 OK 或 FAIL。"""

    _write([_now(), "PDF", str(byte_size), str(elapsed_ms), result])
