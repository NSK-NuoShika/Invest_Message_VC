import threading
import time
from pathlib import Path

import pytest

from src.command import api
from src.service import route

LARKBOT_LOG = Path(__file__).resolve().parents[1] / "log" / "larkbot.log"


@pytest.fixture
def client():
    return api.create_app().test_client()


@pytest.fixture(autouse=True)
def reset_log():
    LARKBOT_LOG.write_text("", encoding="utf-8")


def _log_rows() -> list[list[str]]:
    lines = LARKBOT_LOG.read_text(encoding="utf-8").splitlines()
    return [line.split(" ") for line in lines if line]


def _wait(predicate, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_help_returns_ok_and_dispatches(client, monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(route, "route_help", lambda user_id: calls.append(user_id))

    response = client.post("/help", json={"sender": "ou_1", "args": []})

    assert response.status_code == 200
    assert response.get_json() == {"code": 0, "message": "ok", "data": None}
    assert _wait(lambda: calls == ["ou_1"])


@pytest.mark.parametrize(
    ("path", "method_name"),
    [("/query", "route_query"), ("/watchlist", "route_watchlist"), ("/schedule", "route_schedule")],
)
def test_routes_dispatch_with_args(client, monkeypatch, path: str, method_name: str) -> None:
    calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        route, method_name, lambda user_id, args: calls.append((user_id, args))
    )

    response = client.post(path, json={"sender": "ou_1", "args": ["7天", "1年"]})

    assert response.status_code == 200
    assert _wait(lambda: calls == [("ou_1", ["7天", "1年"])])


def test_invalid_request_bodies_return_400(client, monkeypatch) -> None:
    for name in ("route_help", "route_query", "route_watchlist", "route_schedule"):
        monkeypatch.setattr(route, name, lambda *args: pytest.fail("不应分派"))

    responses = [
        client.post("/help", data="not-json", content_type="text/plain"),
        client.post("/help", json={"args": []}),
        client.post("/help", json={"sender": 1, "args": []}),
        client.post("/help", json={"sender": "", "args": []}),
        client.post("/help", json={"sender": "ou_1"}),
        client.post("/help", json={"sender": "ou_1", "args": "7天"}),
        client.post("/help", json={"sender": "ou_1", "args": ["7天", 1]}),
    ]

    assert all(response.status_code == 400 for response in responses)
    for response in responses:
        body = response.get_json()
        assert body["code"] == 0
        assert body["data"] is None
        assert body["message"]


def test_valid_request_logs_receive(client, monkeypatch) -> None:
    monkeypatch.setattr(route, "route_query", lambda user_id, args: None)

    client.post("/query", json={"sender": "ou_1", "args": ["今天"]})

    rows = _log_rows()
    assert len(rows) == 1
    row = rows[0]
    assert len(row) == 6
    assert row[1] == "RECEIVE"
    assert row[2].endswith("/query")
    assert row[3:] == ["ou_1", "200", "0"]


def test_invalid_request_logs_receive(client) -> None:
    client.post("/help", json={"args": []})

    row = _log_rows()[0]
    assert len(row) == 6
    assert row[3:] == ["-", "400", "0"]


def test_response_returns_before_handler_finishes(client, monkeypatch) -> None:
    started = threading.Event()
    release = threading.Event()

    def slow(user_id: str, args: list[str]) -> None:
        started.set()
        release.wait(2)

    monkeypatch.setattr(route, "route_query", slow)

    response = client.post("/query", json={"sender": "ou_1", "args": ["今天"]})

    assert response.status_code == 200
    assert started.wait(2)
    release.set()


def test_handler_exception_does_not_break_request(client, monkeypatch) -> None:
    def raising(user_id: str, args: list[str]) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(route, "route_query", raising)
    response = client.post("/query", json={"sender": "ou_1", "args": ["今天"]})
    assert response.status_code == 200


def test_only_post_is_allowed(client) -> None:
    assert client.get("/help").status_code == 405
    assert client.post("/unknown", json={}).status_code == 404
