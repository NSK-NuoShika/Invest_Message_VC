"""启动时的注册与常驻心跳线程。"""

from __future__ import annotations

import threading
import time

import requests

from config.settings import get_setting
from log import larkbot_log

PROGRAM_URL = f"http://127.0.0.1:{get_setting().port}"
LARKBOT_REGISTER_URL = f"{get_setting().larkbot_url}/register"
LARKBOT_HEARTBEAT_URL = f"{get_setting().larkbot_url}/heartbeat"

_TIMEOUT = 5.0
_INTERFACES: tuple[tuple[str, str], ...] = (
    ("帮助", "/help"),
    ("查询", "/query"),
    ("自选", "/watchlist"),
    ("定时", "/schedule"),
)


def _business_code(response: requests.Response) -> int:
    try:
        payload = response.json()
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        return int(payload.get("code", 0))
    except (TypeError, ValueError):
        return 0


def _post(url: str, payload: dict[str, object]) -> tuple[int | str, int | str]:
    """返回 (HTTP 状态, 业务码)；超时返回 ("TIMEOUT", "TIMEOUT")。"""
    try:
        response = requests.post(url, json=payload, timeout=_TIMEOUT)
    except requests.Timeout:
        return "TIMEOUT", "TIMEOUT"
    except requests.RequestException:
        return 0, 0
    return response.status_code, _business_code(response)


def register_all() -> None:
    """同步注册四个接口。"""
    setting = get_setting()

    for cmd, path in _INTERFACES:
        status, code = _post(
            LARKBOT_REGISTER_URL,
            {
                "program": setting.program_name,
                "base_url": PROGRAM_URL,
                "cmd": cmd,
                "path": path,
            },
        )

        larkbot_log.register(LARKBOT_REGISTER_URL, setting.program_name, cmd, path, PROGRAM_URL, status, code)


def _beat_once() -> None:
    setting = get_setting()
    status, code = _post(LARKBOT_HEARTBEAT_URL, {"program": setting.program_name})
    larkbot_log.heartbeat(LARKBOT_HEARTBEAT_URL, status, code)
    if status != 200 or code != 0:
        time.sleep(3)
        register_all()


def _heartbeat_loop() -> None:
    while True:
        time.sleep(get_setting().heartbeat_seconds)
        try:
            _beat_once()
        except Exception:
            continue


def start_heartbeat() -> threading.Thread:
    """启动常驻心跳 daemon 线程。"""
    thread = threading.Thread(target=_heartbeat_loop, name="larkbot-heartbeat", daemon=True)
    thread.start()
    return thread
