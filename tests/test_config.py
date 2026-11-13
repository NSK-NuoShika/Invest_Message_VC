import importlib
from pathlib import Path

import pytest

from config.settings import get_setting

BASE_ENV = {
    "PROGRAM_NAME": "演示",
    "PORT": "9001",
    "LARKBOT_URL": "http://127.0.0.1:8000",
    "HEARTBEAT_SECONDS": "10",
}


def _env(overrides: dict[str, str] | None = None, omit: tuple[str, ...] = ()) -> str:
    values = {key: value for key, value in BASE_ENV.items() if key not in omit}
    values.update(overrides or {})
    return "".join(f"{key}={value}\n" for key, value in values.items())


@pytest.fixture
def build_settings(tmp_path: Path):
    """在临时目录写入 .env，直接调用内部构造函数，避免重载模块带来的副作用。"""

    def _build(content: str | None):
        module = importlib.import_module("config.settings")
        if content is None:
            env_path = tmp_path / "missing.env"
        else:
            env_path = tmp_path / ".env"
            env_path.write_text(content, encoding="utf-8")
        original_path = module.ENV_PATH
        module.ENV_PATH = env_path
        try:
            return module._build()
        finally:
            module.ENV_PATH = original_path

    return _build


def test_defaults_without_env(build_settings) -> None:
    settings = build_settings(None)
    assert settings.program_name == "基金"
    assert settings.port == 9000
    assert settings.larkbot_url == "http://127.0.0.1:8000"
    assert settings.heartbeat_seconds == 30


def test_singleton_is_shared() -> None:
    module = importlib.import_module("config.settings")
    assert module.get_setting() is module.settings
    assert get_setting() is module.settings


def test_reads_custom_values(build_settings) -> None:
    settings = build_settings(_env())
    assert settings.program_name == "演示"
    assert settings.port == 9001
    assert settings.larkbot_url == "http://127.0.0.1:8000"
    assert settings.heartbeat_seconds == 10


def test_larkbot_url_trailing_slash_removed(build_settings) -> None:
    settings = build_settings(_env({"LARKBOT_URL": "http://127.0.0.1:8000///"}))
    assert settings.larkbot_url == "http://127.0.0.1:8000"


@pytest.mark.parametrize("value", ["abc", "0", "65536", "-1", "12.5"])
def test_invalid_port_exits(build_settings, value: str) -> None:
    with pytest.raises(SystemExit):
        build_settings(_env({"PORT": value}))


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_invalid_heartbeat_exits(build_settings, value: str) -> None:
    with pytest.raises(SystemExit):
        build_settings(_env({"HEARTBEAT_SECONDS": value}))


def test_empty_program_name_exits(build_settings) -> None:
    with pytest.raises(SystemExit):
        build_settings(_env({"PROGRAM_NAME": ""}))


def test_blank_program_name_exits(build_settings) -> None:
    with pytest.raises(SystemExit):
        build_settings(_env({"PROGRAM_NAME": "   "}))


def test_empty_env_file_exits(build_settings) -> None:
    with pytest.raises(SystemExit):
        build_settings("")


@pytest.mark.parametrize(
    "key", ["PROGRAM_NAME", "PORT", "LARKBOT_URL", "HEARTBEAT_SECONDS"]
)
def test_missing_key_exits(build_settings, key: str) -> None:
    with pytest.raises(SystemExit):
        build_settings(_env(omit=(key,)))


@pytest.mark.parametrize("value", ["", "   ", "///"])
def test_empty_larkbot_url_exits(build_settings, value: str) -> None:
    with pytest.raises(SystemExit):
        build_settings(_env({"LARKBOT_URL": value}))
