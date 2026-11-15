from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from larkbot import send
from model.fund import FundReport, NavPoint
from service import (
    query,
    route,
    schedule_add,
    schedule_delete,
    schedule_query,
    watchlist_add,
    watchlist_delete,
    watchlist_query,
)

TODAY = date(2026, 11, 11)


@pytest.fixture
def sent(monkeypatch):
    texts: list[tuple[str, str]] = []
    files: list[tuple[str, str, bytes]] = []
    monkeypatch.setattr(send, "send_text", lambda uid, content: texts.append((uid, content)))
    monkeypatch.setattr(
        send, "send_file", lambda uid, filename, content: files.append((uid, filename, content))
    )
    return SimpleNamespace(texts=texts, files=files)


def _report(code: str = "000001", days: int = 400, name: str | None = None) -> FundReport:
    start = TODAY - timedelta(days=days - 1)
    points = [
        NavPoint(date=start + timedelta(days=index), nav=1.0 + 0.01 * index, growth=0.5)
        for index in range(days)
    ]
    return FundReport(code=code, name=name or code, points=points)


def _points(days: int) -> list[NavPoint]:
    return _report(days=days).points


@pytest.fixture
def rendered(monkeypatch):
    blocks: list[list] = []

    def fake_render(items):
        blocks.append(items)
        return b"%PDF-fake"

    monkeypatch.setattr(query, "render", fake_render)
    monkeypatch.setattr(query, "_today", lambda: TODAY)
    return blocks


def _patch_fetch(monkeypatch, handler, module=query):
    calls: list[tuple[str, date, date]] = []

    def fetch(code: str, start_time: date, end_time: date) -> FundReport:
        calls.append((code, start_time, end_time))
        return handler(code, start_time, end_time)

    monkeypatch.setattr(module.fetcher, "fetch", fetch)
    return calls


def test_query_requires_range_word(sent) -> None:
    query.handle_query("ou_1", [])
    assert len(sent.texts) == 1
    assert "至少指定一个区间词" in sent.texts[0][1]
    assert sent.files == []


def test_query_rejects_invalid_word(sent) -> None:
    query.handle_query("ou_1", ["明天"])
    assert len(sent.texts) == 1
    message = sent.texts[0][1]
    assert "区间词不合法：明天" in message
    for word in ("今天", "7天", "30天", "1年", "3年", "5年"):
        assert word in message


def test_query_code_without_range_word(sent) -> None:
    query.handle_query("ou_1", ["000001"])
    assert len(sent.texts) == 1
    assert "至少指定一个区间词" in sent.texts[0][1]


def test_query_fetches_once_with_max_range(sent, rendered, monkeypatch) -> None:
    monkeypatch.setattr(query.db, "list_watch", lambda user_id: [("000001", "华夏成长")])
    calls = _patch_fetch(monkeypatch, lambda code, start, end: _report(code, days=400))

    query.handle_query("ou_1", ["7天", "1年"])

    assert calls == [("000001", TODAY - timedelta(days=365), TODAY)]
    blocks = rendered[0]
    assert len(blocks) == 1
    assert [chart.caption for chart in blocks[0].charts] == ["近 7 天", "近 1 年"]
    assert blocks[0].name == "华夏成长"
    assert len(blocks[0].table_points) == 400
    assert len(sent.files) == 1
    assert sent.files[0][1] == "基金_20261111.pdf"
    assert sent.texts == []


def test_query_chart_order_ascending(sent, rendered, monkeypatch) -> None:
    monkeypatch.setattr(query.db, "list_watch", lambda user_id: [("000001", "甲")])
    _patch_fetch(monkeypatch, lambda code, start, end: _report(code, days=1200))

    query.handle_query("ou_1", ["5年", "7天", "1年"])

    captions = [chart.caption for chart in rendered[0][0].charts]
    assert captions == ["近 7 天", "近 1 年", "近 5 年"]
    assert all(
        point.date >= TODAY - timedelta(days=7)
        for point in rendered[0][0].charts[0].points
    )


def test_query_today_only_has_no_charts_or_table(sent, rendered, monkeypatch) -> None:
    monkeypatch.setattr(query.db, "list_watch", lambda user_id: [("000001", "甲")])
    _patch_fetch(monkeypatch, lambda code, start, end: _report(code, days=10))

    query.handle_query("ou_1", ["今天"])

    block = rendered[0][0]
    assert block.charts == []
    assert block.table_points == []
    assert len(sent.files) == 1


def test_query_failure_text_before_pdf(sent, rendered, monkeypatch) -> None:
    monkeypatch.setattr(
        query.db, "list_watch", lambda user_id: [("000001", "甲"), ("161725", "乙")]
    )

    def handler(code: str, start: date, end: date) -> FundReport:
        if code == "161725":
            raise ValueError("network")
        return _report(code, days=10)

    _patch_fetch(monkeypatch, handler)
    query.handle_query("ou_1", ["7天"])

    assert len(sent.texts) == 1
    assert sent.texts[0][1].startswith("以下基金取数失败，已跳过：")
    assert "161725" in sent.texts[0][1]
    assert len(rendered[0]) == 1
    assert len(sent.files) == 1
    assert sent.texts[0][0] == "ou_1"


def test_query_all_failed_sends_text_only(sent, rendered, monkeypatch) -> None:
    monkeypatch.setattr(
        query.db, "list_watch", lambda user_id: [("000001", "甲"), ("161725", "乙")]
    )

    def handler(code: str, start: date, end: date) -> FundReport:
        raise ValueError("network")

    _patch_fetch(monkeypatch, handler)
    query.handle_query("ou_1", ["7天"])

    assert rendered == []
    assert len(sent.texts) == 1
    assert sent.texts[0][1].startswith("全部基金取数失败")
    assert sent.files == []


def test_query_empty_watchlist(sent, monkeypatch) -> None:
    monkeypatch.setattr(query.db, "list_watch", lambda user_id: [])
    calls = _patch_fetch(monkeypatch, lambda code, start, end: _report(code))
    query.handle_query("ou_1", ["7天"])
    assert calls == []
    assert "自选列表为空" in sent.texts[0][1]


def test_query_specified_code_skips_watchlist(sent, rendered, monkeypatch) -> None:
    monkeypatch.setattr(
        query.db, "list_watch", lambda user_id: pytest.fail("不应读取自选")
    )
    calls = _patch_fetch(
        monkeypatch, lambda code, start, end: _report(code, days=10, name="华夏成长")
    )

    query.handle_query("ou_1", ["161725", "7天"])

    assert calls[0][0] == "161725"
    assert rendered[0][0].name == "华夏成长"
    assert len(sent.files) == 1


def test_query_specified_code_falls_back_to_code_without_name(
    sent, rendered, monkeypatch
) -> None:
    monkeypatch.setattr(
        query.db, "list_watch", lambda user_id: pytest.fail("不应读取自选")
    )
    _patch_fetch(monkeypatch, lambda code, start, end: _report(code, days=10))

    query.handle_query("ou_1", ["161725", "7天"])

    assert rendered[0][0].name == "161725"
    assert len(sent.files) == 1


def test_query_prefers_fetched_name_over_stale_code(sent, rendered, monkeypatch) -> None:
    monkeypatch.setattr(query.db, "list_watch", lambda user_id: [("000001", "000001")])
    _patch_fetch(
        monkeypatch, lambda code, start, end: _report(code, days=10, name="华夏成长")
    )

    query.handle_query("ou_1", ["7天"])

    assert rendered[0][0].name == "华夏成长"
    assert len(sent.files) == 1


def test_query_render_failure_sends_text(sent, monkeypatch) -> None:
    monkeypatch.setattr(query.db, "list_watch", lambda user_id: [("000001", "甲")])
    _patch_fetch(monkeypatch, lambda code, start, end: _report(code, days=10))
    monkeypatch.setattr(query, "render", lambda blocks: (_ for _ in ()).throw(RuntimeError()))

    query.handle_query("ou_1", ["7天"])

    assert sent.files == []
    assert "PDF 生成失败" in sent.texts[0][1]


def test_query_day_change_and_update_flag(sent, rendered, monkeypatch) -> None:
    monkeypatch.setattr(query.db, "list_watch", lambda user_id: [("000001", "甲")])
    report = FundReport(
        code="000001",
        name="甲",
        points=[
            NavPoint(date=TODAY - timedelta(days=2), nav=1.0, growth=0.25),
            NavPoint(date=TODAY - timedelta(days=1), nav=1.1, growth=0.55),
        ],
    )
    _patch_fetch(monkeypatch, lambda code, start, end: report)

    query.handle_query("ou_1", ["7天"])

    block = rendered[0][0]
    assert block.day_change == 0.55
    assert block.day_change_date == TODAY - timedelta(days=1)
    assert block.updated_today is False


def test_query_marks_updated_today(sent, rendered, monkeypatch) -> None:
    monkeypatch.setattr(query.db, "list_watch", lambda user_id: [("000001", "甲")])
    _patch_fetch(monkeypatch, lambda code, start, end: _report(code, days=3))

    query.handle_query("ou_1", ["今天"])

    block = rendered[0][0]
    assert block.updated_today is True
    assert block.day_change_date == TODAY


def test_watchlist_query_lists_in_order(sent, monkeypatch) -> None:
    monkeypatch.setattr(
        watchlist_query.db, "list_watch", lambda user_id: [("000001", "甲"), ("000002", "乙")]
    )
    watchlist_query.handle_watchlist_query("ou_1")
    assert sent.texts == [("ou_1", "000001 甲\n000002 乙")]


def test_watchlist_query_empty(sent, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_query.db, "list_watch", lambda user_id: [])
    watchlist_query.handle_watchlist_query("ou_1")
    assert sent.texts == [("ou_1", "自选列表为空")]


def test_watchlist_add_success(sent, monkeypatch) -> None:
    _patch_fetch(monkeypatch, lambda code, start, end: _report(code, days=10), watchlist_add)
    added: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        watchlist_add.db,
        "add_watch",
        lambda user_id, code, name: added.append((user_id, code, name)) or True,
    )

    watchlist_add.handle_watchlist_add("ou_1", ["000001"])

    assert added == [("ou_1", "000001", "000001")]
    assert sent.texts[0][1] == "已添加自选：000001 000001"


def test_watchlist_add_stores_fetched_name(sent, monkeypatch) -> None:
    _patch_fetch(
        monkeypatch,
        lambda code, start, end: _report(code, days=10, name="华夏成长"),
        watchlist_add,
    )
    added: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        watchlist_add.db,
        "add_watch",
        lambda user_id, code, name: added.append((user_id, code, name)) or True,
    )

    watchlist_add.handle_watchlist_add("ou_1", ["000001"])

    assert added == [("ou_1", "000001", "华夏成长")]
    assert sent.texts[0][1] == "已添加自选：000001 华夏成长"


def test_watchlist_add_existing(sent, monkeypatch) -> None:
    _patch_fetch(monkeypatch, lambda code, start, end: _report(code, days=10), watchlist_add)
    monkeypatch.setattr(watchlist_add.db, "add_watch", lambda *args: False)
    watchlist_add.handle_watchlist_add("ou_1", ["000001"])
    assert sent.texts[0][1] == "该基金已在自选中"


def test_watchlist_add_invalid_code(sent) -> None:
    watchlist_add.handle_watchlist_add("ou_1", ["12345"])
    assert sent.texts[0][1] == "基金代码必须是六位数字"


def test_watchlist_add_argument_counts(sent) -> None:
    watchlist_add.handle_watchlist_add("ou_1", [])
    watchlist_add.handle_watchlist_add("ou_1", ["000001", "000002"])
    assert sent.texts[0][1].startswith("参数不足")
    assert sent.texts[1][1].startswith("参数过多")


def test_watchlist_add_fetch_error_and_empty(sent, monkeypatch) -> None:
    def raising(code, start, end):
        raise ValueError("network")

    _patch_fetch(monkeypatch, raising, watchlist_add)
    watchlist_add.handle_watchlist_add("ou_1", ["000001"])
    assert "查询基金信息失败" in sent.texts[0][1]

    _patch_fetch(
        monkeypatch,
        lambda code, start, end: FundReport(code=code, name=code, points=[]),
        watchlist_add,
    )
    watchlist_add.handle_watchlist_add("ou_1", ["999999"])
    assert "未找到该基金" in sent.texts[1][1]


def test_watchlist_delete_success(sent, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_delete.db, "remove_watch", lambda *args: True)
    watchlist_delete.handle_watchlist_delete("ou_1", ["000001"])
    assert sent.texts[0][1] == "已删除自选：000001"


def test_watchlist_delete_missing(sent, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_delete.db, "remove_watch", lambda *args: False)
    watchlist_delete.handle_watchlist_delete("ou_1", ["000001"])
    assert sent.texts[0][1] == "该基金不在自选中"


def test_watchlist_delete_invalid_code(sent) -> None:
    watchlist_delete.handle_watchlist_delete("ou_1", ["abc"])
    assert sent.texts[0][1] == "基金代码必须是六位数字"


def test_schedule_add_success(sent, monkeypatch) -> None:
    added: list[tuple[str, str]] = []
    jobs_added: list[tuple[str, str]] = []
    logged: list[tuple[str, str]] = []
    monkeypatch.setattr(
        schedule_add.db,
        "add_schedule",
        lambda user_id, hhmm: added.append((user_id, hhmm)) or True,
    )
    monkeypatch.setattr(
        schedule_add.jobs, "add", lambda user_id, hhmm: jobs_added.append((user_id, hhmm))
    )
    monkeypatch.setattr(
        schedule_add.schedule_log, "add", lambda user_id, hhmm: logged.append((user_id, hhmm))
    )

    schedule_add.handle_schedule_add("ou_1", ["09:30"])

    assert added == [("ou_1", "09:30")]
    assert jobs_added == [("ou_1", "09:30")]
    assert logged == [("ou_1", "09:30")]
    assert sent.texts[0][1] == "已添加定时：09:30"


def test_schedule_add_duplicate_skips_job(sent, monkeypatch) -> None:
    monkeypatch.setattr(schedule_add.db, "add_schedule", lambda *args: False)
    monkeypatch.setattr(
        schedule_add.jobs, "add", lambda *args: pytest.fail("不应建调度任务")
    )
    monkeypatch.setattr(
        schedule_add.schedule_log, "add", lambda *args: pytest.fail("不应写 ADD 日志")
    )
    schedule_add.handle_schedule_add("ou_1", ["09:30"])
    assert sent.texts[0][1] == "该时间点已存在"


def test_schedule_add_invalid_time(sent, monkeypatch) -> None:
    monkeypatch.setattr(
        schedule_add.db, "add_schedule", lambda *args: pytest.fail("不应写库")
    )
    monkeypatch.setattr(
        schedule_add.schedule_log, "add", lambda *args: pytest.fail("不应写 ADD 日志")
    )
    for value in ("9:30", "24:00", "09:60", "0930"):
        schedule_add.handle_schedule_add("ou_1", [value])
    assert all("时间格式错误" in text for _, text in sent.texts)


def test_schedule_add_argument_counts(sent) -> None:
    schedule_add.handle_schedule_add("ou_1", [])
    schedule_add.handle_schedule_add("ou_1", ["09:30", "21:00"])
    assert sent.texts[0][1].startswith("参数不足")
    assert sent.texts[1][1].startswith("参数过多")


def test_schedule_delete_success(sent, monkeypatch) -> None:
    removed: list[tuple[str, str]] = []
    logged: list[tuple[str, str]] = []
    monkeypatch.setattr(schedule_delete.db, "remove_schedule", lambda *args: True)
    monkeypatch.setattr(
        schedule_delete.jobs, "remove", lambda user_id, hhmm: removed.append((user_id, hhmm))
    )
    monkeypatch.setattr(
        schedule_delete.schedule_log,
        "delete",
        lambda user_id, hhmm: logged.append((user_id, hhmm)),
    )
    schedule_delete.handle_schedule_delete("ou_1", ["09:30"])
    assert removed == [("ou_1", "09:30")]
    assert logged == [("ou_1", "09:30")]
    assert sent.texts[0][1] == "已删除定时：09:30"


def test_schedule_delete_missing_skips_job(sent, monkeypatch) -> None:
    monkeypatch.setattr(schedule_delete.db, "remove_schedule", lambda *args: False)
    monkeypatch.setattr(
        schedule_delete.jobs, "remove", lambda *args: pytest.fail("不应删调度任务")
    )
    monkeypatch.setattr(
        schedule_delete.schedule_log, "delete", lambda *args: pytest.fail("不应写 DEL 日志")
    )
    schedule_delete.handle_schedule_delete("ou_1", ["09:30"])
    assert sent.texts[0][1] == "该时间点不存在"


def test_schedule_delete_invalid_time(sent) -> None:
    schedule_delete.handle_schedule_delete("ou_1", ["25:00"])
    assert "时间格式错误" in sent.texts[0][1]


def test_schedule_query(sent, monkeypatch) -> None:
    monkeypatch.setattr(
        schedule_query.db, "list_user_schedules", lambda user_id: ["09:30", "21:00"]
    )
    schedule_query.handle_schedule_query("ou_1")
    assert sent.texts[0][1] == "09:30\n21:00"


def test_schedule_query_empty(sent, monkeypatch) -> None:
    monkeypatch.setattr(schedule_query.db, "list_user_schedules", lambda user_id: [])
    schedule_query.handle_schedule_query("ou_1")
    assert sent.texts[0][1] == "定时列表为空"


def test_route_watchlist_dispatch(sent, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        route.watchlist_query, "handle_watchlist_query", lambda uid: calls.append((uid, None))
    )
    monkeypatch.setattr(
        route.watchlist_add,
        "handle_watchlist_add",
        lambda uid, args: calls.append((uid, args)),
    )
    monkeypatch.setattr(
        route.watchlist_delete,
        "handle_watchlist_delete",
        lambda uid, args: calls.append((uid, args)),
    )

    route.route_watchlist("ou_1", ["查询"])
    route.route_watchlist("ou_1", ["添加", "000001"])
    route.route_watchlist("ou_1", ["删除", "000001"])

    assert calls == [("ou_1", None), ("ou_1", ["000001"]), ("ou_1", ["000001"])]


def test_route_watchlist_invalid(sent) -> None:
    route.route_watchlist("ou_1", [])
    route.route_watchlist("ou_1", ["未知"])
    assert sent.texts[0][1].startswith("用法：基金 自选")


def test_route_schedule_dispatch(sent, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        route.schedule_query, "handle_schedule_query", lambda uid: calls.append((uid, None))
    )
    monkeypatch.setattr(
        route.schedule_add,
        "handle_schedule_add",
        lambda uid, args: calls.append((uid, args)),
    )
    monkeypatch.setattr(
        route.schedule_delete,
        "handle_schedule_delete",
        lambda uid, args: calls.append((uid, args)),
    )

    route.route_schedule("ou_1", ["查询"])
    route.route_schedule("ou_1", ["添加", "09:30"])
    route.route_schedule("ou_1", ["删除", "09:30"])

    assert calls == [("ou_1", None), ("ou_1", ["09:30"]), ("ou_1", ["09:30"])]


def test_route_schedule_invalid(sent) -> None:
    route.route_schedule("ou_1", [])
    assert sent.texts[0][1].startswith("用法：基金 定时")


def test_route_help_and_query(sent, monkeypatch) -> None:
    seen: list[tuple[str, str, list[str]]] = []
    monkeypatch.setattr(
        route.help, "handle_help", lambda uid: seen.append(("help", uid, []))
    )
    monkeypatch.setattr(
        route.query, "handle_query", lambda uid, args: seen.append(("query", uid, args))
    )

    route.route_help("ou_1")
    route.route_query("ou_2", ["今天"])

    assert seen == [("help", "ou_1", []), ("query", "ou_2", ["今天"])]
