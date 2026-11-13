"""写 log/larkbot.log，记录与上游 LarkBot 的全部往来。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TextIO

from log import _LOCK

_LOG_DIR = Path(__file__).resolve().parents[2] / "log"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_STREAM: TextIO = (_LOG_DIR / "larkbot.log").open("a", encoding="utf-8", newline="\n")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _status(http_status: int | str, code: int | str) -> list[str]:
    """正常与业务报错时两个状态码各占一列；超时合并为一列 TIMEOUT。"""

    if isinstance(http_status, str):
        return [http_status]
    if isinstance(code, str):
        return [code]
    return [str(http_status), str(code)]


def _write(fields: list[str]) -> None:
    line = " ".join(fields)
    with _LOCK:
        _STREAM.write(line + "\n")
        _STREAM.flush()


def receive(url: str, user_id: str, http_status: int | str, code: int | str) -> None:
    """上游派发到本程序。"""

    _write([_now(), "RECEIVE", url, user_id, *_status(http_status, code)])


def send(url: str, kind: str, user_id: str, http_status: int | str, code: int | str) -> None:
    """本程序向上游发送文字或文件。kind 只取 TEXT 或 FILE。"""

    _write([_now(), "SEND", url, kind, user_id, *_status(http_status, code)])


def register(
    url: str,
    program: str,
    cmd: str,
    path: str,
    program_url: str,
    http_status: int | str,
    code: int | str,
) -> None:
    """向上游注册一个接口。"""

    _write([_now(), "REGISTER", url, program, cmd, path, program_url, *_status(http_status, code)])


def heartbeat(url: str, http_status: int | str, code: int | str) -> None:
    """向上游发送心跳。"""

    _write([_now(), "HEARTBEAT", url, *_status(http_status, code)])
