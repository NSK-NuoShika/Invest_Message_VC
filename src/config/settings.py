"""全局配置。"""

from __future__ import annotations

from dataclasses import dataclass
from os.path import isfile
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_PROGRAM_NAME = "基金"
DEFAULT_PORT = 9000
DEFAULT_LARKBOT_URL = "http://127.0.0.1:8000"
DEFAULT_HEARTBEAT_SECONDS = 30


@dataclass(frozen=True)
class Settings:
    """程序配置。"""

    program_name: str = DEFAULT_PROGRAM_NAME
    port: int = DEFAULT_PORT
    larkbot_url: str = DEFAULT_LARKBOT_URL
    heartbeat_seconds: int = DEFAULT_HEARTBEAT_SECONDS


def _fail(message: str) -> SystemExit:
    return SystemExit(f"配置错误：{message}")


def _read_int(name: str, raw: str | None) -> int:
    if raw is None or not raw.strip():
        raise _fail(f"{name} 为空")
    try:
        return int(raw.strip())
    except ValueError:
        raise _fail(f"{name} 必须是整数，当前为 {raw!r}") from None


def _build() -> Settings:
    if not isfile(ENV_PATH):
        return Settings()

    values = dotenv_values(ENV_PATH)

    program_name = (values.get("PROGRAM_NAME") or "").strip()
    if not program_name:
        raise _fail("PROGRAM_NAME 为空")

    port = _read_int("PORT", values.get("PORT"))
    if not 1 <= port <= 65535:
        raise _fail(f"PORT 必须在 1..65535 之间，当前为 {port}")

    larkbot_url = (values.get("LARKBOT_URL") or "").strip().rstrip("/")
    if not larkbot_url:
        raise _fail("LARKBOT_URL 为空")

    heartbeat_seconds = _read_int("HEARTBEAT_SECONDS", values.get("HEARTBEAT_SECONDS"))
    if heartbeat_seconds <= 0:
        raise _fail(f"HEARTBEAT_SECONDS 必须大于 0，当前为 {heartbeat_seconds}")

    return Settings(
        program_name=program_name,
        port=port,
        larkbot_url=larkbot_url,
        heartbeat_seconds=heartbeat_seconds,
    )


settings: Settings = _build()


def get_setting() -> Settings:
    """返回全局的配置对象。"""

    return settings
