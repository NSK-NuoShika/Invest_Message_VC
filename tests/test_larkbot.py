import base64
from pathlib import Path

import pytest
import requests

from src.config.settings import get_setting
from src.larkbot import send, worker

LARKBOT_LOG = Path(__file__).resolve().parents[1] / "log" / "larkbot.log"


def _reset_log() -> None:
    LARKBOT_LOG.write_text("", encoding="utf-8")


def _log_rows() -> list[list[str]]:
    lines = LARKBOT_LOG.read_text(encoding="utf-8").splitlines()
    return [line.split(" ") for line in lines if line]


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = (
            payload
            if payload is not None
            else {"code": 0, "message": "ok", "data": None}
        )

    def json(self) -> dict:
        return self._payload


def _install_post(
    monkeypatch,
    module,
    captured: list[tuple[str, dict, float]],
    *,
    status_code: int = 200,
    payload: dict | None = None,
) -> None:
    def post(url, json=None, timeout=None):
        captured.append((url, json, timeout))
        return _FakeResponse(status_code, payload)

    monkeypatch.setattr(module.requests, "post", post)


def test_send_text(monkeypatch) -> None:
    _reset_log()
    captured: list[tuple[str, dict, float]] = []
    _install_post(monkeypatch, send, captured)
    assert send.send_text("ou_1", "你好") is True
    assert captured == [
        (
            "http://127.0.0.1:8000/send/text",
            {"program": "基金", "target": "ou_1", "content": "你好"},
            5.0,
        )
    ]
    row = _log_rows()[0]
    assert len(row) == 7
    assert row[1:4] == ["SEND", "http://127.0.0.1:8000/send/text", "TEXT"]
    assert row[4:] == ["ou_1", "200", "0"]


def test_send_file_base64_has_no_newline(monkeypatch) -> None:
    _reset_log()
    captured: list[tuple[str, dict, float]] = []
    _install_post(monkeypatch, send, captured)
    assert send.send_file("ou_1", "报告.pdf", b"abc") is True
    url, payload, _ = captured[0]
    assert url == "http://127.0.0.1:8000/send/file"
    assert payload["file_name"] == "报告.pdf"
    assert payload["content_base64"] == base64.b64encode(b"abc").decode("ascii")
    assert "\n" not in payload["content_base64"]
    row = _log_rows()[0]
    assert row[1:4] == ["SEND", "http://127.0.0.1:8000/send/file", "FILE"]


def test_send_http_error_returns_business_code(monkeypatch) -> None:
    _reset_log()
    captured: list[tuple[str, dict, float]] = []
    _install_post(monkeypatch, send, captured, status_code=400, payload={"code": 4001})
    assert send.send_text("ou_1", "你好") is False
    assert _log_rows()[0][-2:] == ["400", "4001"]


def test_send_timeout_logs_single_status(monkeypatch) -> None:
    _reset_log()

    def post(url, json=None, timeout=None):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(send.requests, "post", post)
    assert send.send_text("ou_1", "你好") is False
    row = _log_rows()[0]
    assert len(row) == 6
    assert row[-1] == "TIMEOUT"


def test_send_connection_error_returns_zero(monkeypatch) -> None:
    _reset_log()

    def post(url, json=None, timeout=None):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(send.requests, "post", post)
    assert send.send_text("ou_1", "你好") is False
    assert _log_rows()[0][-2:] == ["0", "0"]


def test_register_all(monkeypatch) -> None:
    _reset_log()
    captured: list[tuple[str, dict, float]] = []
    _install_post(monkeypatch, worker, captured)
    worker.register_all()

    setting = get_setting()
    assert [payload["cmd"] for _, payload, _ in captured] == ["帮助", "查询", "自选", "定时"]
    assert [payload["path"] for _, payload, _ in captured] == [
        "/help",
        "/query",
        "/watchlist",
        "/schedule",
    ]
    for url, payload, timeout in captured:
        assert url == "http://127.0.0.1:8000/register"
        assert timeout == worker._TIMEOUT
        assert payload["program"] == "基金"
        assert payload["base_url"] == f"http://127.0.0.1:{setting.port}"

    rows = _log_rows()
    assert len(rows) == 4
    for row in rows:
        assert len(row) == 9
        assert row[1] == "REGISTER"


def test_register_all_timeout_still_registers_others(monkeypatch) -> None:
    _reset_log()
    calls: list[str] = []

    def post(url, json=None, timeout=None):
        calls.append(url)
        raise requests.Timeout("timed out")

    monkeypatch.setattr(worker.requests, "post", post)
    worker.register_all()
    assert len(calls) == 4
    rows = _log_rows()
    assert len(rows) == 4
    assert all(row[-1] == "TIMEOUT" and len(row) == 8 for row in rows)


def test_beat_once_success(monkeypatch) -> None:
    _reset_log()
    sleeps: list[float] = []
    monkeypatch.setattr(worker.time, "sleep", sleeps.append)
    monkeypatch.setattr(worker, "_post", lambda url, payload: (200, 0))
    monkeypatch.setattr(worker, "register_all", lambda: pytest.fail("不应重新注册"))

    worker._beat_once()

    assert sleeps == []
    row = _log_rows()[0]
    assert len(row) == 5
    assert row[1] == "HEARTBEAT"


def test_beat_once_failure_reregisters_after_three_seconds(monkeypatch) -> None:
    _reset_log()
    sleeps: list[float] = []
    monkeypatch.setattr(worker.time, "sleep", sleeps.append)
    monkeypatch.setattr(worker, "_post", lambda url, payload: (404, 0))
    registered: list[bool] = []
    monkeypatch.setattr(worker, "register_all", lambda: registered.append(True))

    worker._beat_once()

    assert sleeps == [3]
    assert registered == [True]
    assert _log_rows()[0][-2:] == ["404", "0"]


def test_start_heartbeat_returns_daemon_thread(monkeypatch) -> None:
    started: list[bool] = []
    monkeypatch.setattr(worker, "_heartbeat_loop", lambda: started.append(True))
    thread = worker.start_heartbeat()
    thread.join(2)
    assert thread.daemon is True
    assert thread.name == "larkbot-heartbeat"
    assert started == [True]
