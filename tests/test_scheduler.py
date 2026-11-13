from pathlib import Path

import pytest

from src.scheduler import jobs, rebuild

SCHEDULE_LOG = Path(__file__).resolve().parents[1] / "log" / "schedule.log"


def _reset_log() -> None:
    SCHEDULE_LOG.write_text("", encoding="utf-8")


def _log_rows() -> list[list[str]]:
    lines = SCHEDULE_LOG.read_text(encoding="utf-8").splitlines()
    return [line.split(" ") for line in lines if line]


@pytest.fixture(autouse=True)
def clean_scheduler():
    jobs._scheduler.remove_all_jobs()
    jobs._on_trigger = None
    yield
    jobs._scheduler.remove_all_jobs()
    jobs._on_trigger = None


def test_add_creates_daily_job() -> None:
    jobs.add("ou_1", "09:30")
    job = jobs._scheduler.get_job("ou_1@09:30")
    assert job is not None
    assert job.name == "ou_1@09:30"
    assert job.func is jobs._fire
    assert job.args == ("ou_1", "09:30")
    assert "hour='9'" in str(job.trigger)
    assert "minute='30'" in str(job.trigger)


def test_add_is_idempotent() -> None:
    assert jobs.add("ou_1", "09:30") is True
    assert jobs.add("ou_1", "09:30") is False
    assert len(jobs._scheduler.get_jobs()) == 1


def test_remove_deletes_job() -> None:
    jobs.add("ou_1", "09:30")
    assert jobs.remove("ou_1", "09:30") is True
    assert jobs._scheduler.get_job("ou_1@09:30") is None


def test_remove_unknown_returns_false() -> None:
    assert jobs.remove("ou_1", "09:30") is False


def test_fire_logs_trigger_before_callback() -> None:
    _reset_log()
    seen: list[str] = []

    def callback(user_id: str) -> None:
        rows = _log_rows()
        assert rows == [rows[0]]
        assert rows[0][1:] == ["TRIGGER", "ou_1", "09:30"]
        seen.append(user_id)

    jobs._on_trigger = callback
    jobs._fire("ou_1", "09:30")
    assert seen == ["ou_1"]


def test_fire_without_callback_only_logs() -> None:
    _reset_log()
    jobs._fire("ou_1", "09:30")
    assert _log_rows()[0][1:] == ["TRIGGER", "ou_1", "09:30"]


def test_start_injects_callback_and_starts_once(monkeypatch) -> None:
    started: list[bool] = []
    monkeypatch.setattr(jobs._scheduler, "start", lambda: started.append(True))
    callback = lambda user_id: None  # noqa: E731

    jobs.start(callback)

    assert started == [True]
    assert jobs._on_trigger is callback


def test_rebuild_adds_every_schedule(monkeypatch) -> None:
    monkeypatch.setattr(
        rebuild.db,
        "list_all_schedules",
        lambda: [("ou_1", "09:30"), ("ou_2", "21:00")],
    )
    rebuild.rebuild()
    assert {job.id for job in jobs._scheduler.get_jobs()} == {
        "ou_1@09:30",
        "ou_2@21:00",
    }


def test_rebuild_with_empty_database_adds_nothing(monkeypatch) -> None:
    monkeypatch.setattr(rebuild.db, "list_all_schedules", lambda: [])
    rebuild.rebuild()
    assert jobs._scheduler.get_jobs() == []
