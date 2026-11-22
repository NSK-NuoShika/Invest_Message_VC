import threading
import time
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from fund import fetcher
from model.fund import NavPoint

TASK_LOG = Path(__file__).resolve().parents[1] / "log" / "task.log"

TODAY = date(2026, 11, 11)


def _frame(rows: list[tuple[date, float, float | None]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "净值日期": [row[0] for row in rows],
            "单位净值": [row[1] for row in rows],
            "日增长率": [row[2] for row in rows],
        }
    )


def _name_frame(name: str = "测试基金") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "item": ["基金代码", "基金名称"],
            "value": ["000001", name],
        }
    )


@pytest.fixture(autouse=True)
def name_api(monkeypatch) -> Mock:
    mock = Mock(return_value=_name_frame())
    monkeypatch.setattr(fetcher.ak, "fund_individual_basic_info_xq", mock)
    return mock


def _reset_log() -> None:
    TASK_LOG.write_text("", encoding="utf-8")


def _log_rows() -> list[list[str]]:
    lines = TASK_LOG.read_text(encoding="utf-8").splitlines()
    return [line.split(" ") for line in lines if line]


def _fetch(code: str = "000001", days: int = 7):
    return fetcher.fetch(code, TODAY - timedelta(days=days), TODAY)


def test_normal_returns_filtered_sorted_points(name_api) -> None:
    _reset_log()
    frame = _frame(
        [
            (TODAY, 1.2345, 0.55),
            (TODAY - timedelta(days=10), 1.2000, -0.10),
            (TODAY - timedelta(days=1), 1.2300, 0.20),
        ]
    )
    with patch.object(fetcher.ak, "fund_open_fund_info_em", return_value=frame) as mocked:
        report = _fetch()

    mocked.assert_called_once_with(symbol="000001", indicator="单位净值走势")
    name_api.assert_called_once_with(symbol="000001")
    assert report.code == "000001"
    assert report.name == "测试基金"
    assert report.points == [
        NavPoint(date=TODAY - timedelta(days=1), nav=1.23, growth=0.20),
        NavPoint(date=TODAY, nav=1.2345, growth=0.55),
    ]


def test_name_api_failure_falls_back_to_code(monkeypatch) -> None:
    _reset_log()
    monkeypatch.setattr(
        fetcher.ak,
        "fund_individual_basic_info_xq",
        Mock(side_effect=ValueError("名称接口失败")),
    )
    with patch.object(fetcher.ak, "fund_open_fund_info_em", return_value=_frame([])):
        report = _fetch()
    assert report.name == "000001"


def test_blank_name_falls_back_to_code(monkeypatch) -> None:
    _reset_log()
    monkeypatch.setattr(
        fetcher.ak,
        "fund_individual_basic_info_xq",
        Mock(return_value=_name_frame("   ")),
    )
    with patch.object(fetcher.ak, "fund_open_fund_info_em", return_value=_frame([])):
        report = _fetch()
    assert report.name == "000001"


def test_name_is_stripped(monkeypatch) -> None:
    _reset_log()
    monkeypatch.setattr(
        fetcher.ak,
        "fund_individual_basic_info_xq",
        Mock(return_value=_name_frame("  华夏成长  ")),
    )
    with patch.object(fetcher.ak, "fund_open_fund_info_em", return_value=_frame([])):
        report = _fetch()
    assert report.name == "华夏成长"


def test_boundaries_are_inclusive() -> None:
    _reset_log()
    frame = _frame(
        [
            (TODAY - timedelta(days=8), 1.1, 0.0),
            (TODAY - timedelta(days=7), 1.2, 0.1),
            (TODAY, 1.3, 0.2),
        ]
    )
    with patch.object(fetcher.ak, "fund_open_fund_info_em", return_value=frame):
        report = _fetch()
    assert [point.date for point in report.points] == [
        TODAY - timedelta(days=7),
        TODAY,
    ]


def test_money_market_fund_returns_empty_points() -> None:
    _reset_log()
    with patch.object(fetcher.ak, "fund_open_fund_info_em", return_value=pd.DataFrame()):
        report = _fetch("000198")
    assert report.code == "000198"
    assert report.points == []


def test_missing_code_raises_and_logs_fail() -> None:
    _reset_log()
    with patch.object(
        fetcher.ak,
        "fund_open_fund_info_em",
        side_effect=ValueError("基金代码不存在"),
    ):
        with pytest.raises(ValueError):
            _fetch("999999")
    rows = _log_rows()
    assert len(rows) == 1
    assert rows[0][1:] == ["FETCH", "999999", rows[0][3], "FAIL"]
    assert rows[0][3].isdigit()


def test_empty_table_with_columns_returns_empty_points() -> None:
    _reset_log()
    frame = pd.DataFrame(columns=["净值日期", "单位净值", "日增长率"])
    with patch.object(fetcher.ak, "fund_open_fund_info_em", return_value=frame):
        report = _fetch()
    assert report.points == []


def test_nan_nav_is_skipped_and_missing_growth_is_none() -> None:
    _reset_log()
    frame = _frame(
        [
            (TODAY - timedelta(days=2), 1.1, 0.1),
            (TODAY - timedelta(days=1), float("nan"), None),
            (TODAY, 1.2, float("nan")),
        ]
    )
    with patch.object(fetcher.ak, "fund_open_fund_info_em", return_value=frame):
        report = _fetch()
    assert [point.date for point in report.points] == [TODAY - timedelta(days=2), TODAY]
    assert report.points[0].growth == pytest.approx(0.1)
    assert report.points[1].growth is None


def test_success_logs_ok() -> None:
    _reset_log()
    with patch.object(fetcher.ak, "fund_open_fund_info_em", return_value=_frame([])):
        _fetch("161725")
    rows = _log_rows()
    assert len(rows) == 1
    assert rows[0][1:] == ["FETCH", "161725", rows[0][3], "OK"]


def test_concurrent_fetches_are_serialized() -> None:
    """同一时刻只允许一个线程进入 akshare，避免并发创建 V8 isolate。"""

    _reset_log()
    depth = 0
    peak = 0
    guard = threading.Lock()

    def fake(symbol: str, indicator: str) -> pd.DataFrame:
        nonlocal depth, peak
        with guard:
            depth += 1
            peak = max(peak, depth)
        time.sleep(0.05)
        with guard:
            depth -= 1
        return _frame([])

    with patch.object(fetcher.ak, "fund_open_fund_info_em", side_effect=fake):
        threads = [threading.Thread(target=_fetch) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert peak == 1
