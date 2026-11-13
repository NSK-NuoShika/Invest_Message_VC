"""发送文字与文件两类消息。"""

from __future__ import annotations

import base64

import requests

from src.config.settings import get_setting
from src.log import larkbot_log

DEFAULT_TEXT_URL = f"{get_setting().larkbot_url}/send/text"
DEFAULT_FILE_URL = f"{get_setting().larkbot_url}/send/file"

_TIMEOUT = 5.0


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


def send_text(user_id: str, content: str) -> bool:
    """发送文字消息。"""
    setting = get_setting()
    status, code = _post(
        DEFAULT_TEXT_URL,
        {"program": setting.program_name, "target": user_id, "content": content},
    )
    larkbot_log.send(DEFAULT_TEXT_URL, "TEXT", user_id, status, code)
    return status == 200


def send_file(user_id: str, filename: str, content: bytes) -> bool:
    """发送文件消息。"""
    setting = get_setting()

    encoded = base64.b64encode(content).decode("ascii")
    status, business_code = _post(
        DEFAULT_FILE_URL,
        {
            "program": setting.program_name,
            "target": user_id,
            "file_name": filename,
            "content_base64": encoded,
        },
    )

    larkbot_log.send(DEFAULT_FILE_URL, "FILE", user_id, status, business_code)
    return status == 200
