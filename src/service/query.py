"""基金 查询。"""

from __future__ import annotations

from datetime import date, timedelta

from database import db
from fund import fetcher
from larkbot import send
from pdf.renderer import ChartSpec, FundBlock, render

RANGE_WORDS: dict[str, int] = {
    "今天": 1,
    "7天": 7,
    "30天": 30,
    "1年": 365,
    "3年": 1095,
    "5年": 1826,
}

_RANGE_CAPTIONS: dict[str, str] = {
    "7天": "近 7 天",
    "30天": "近 30 天",
    "1年": "近 1 年",
    "3年": "近 3 年",
    "5年": "近 5 年",
}

_WORDS_TEXT = "今天、7天、30天、1年、3年、5年"


def _today() -> date:
    return date.today()


def _is_code(value: str) -> bool:
    return len(value) == 6 and value.isdigit()


def _split_args(args: list[str]) -> tuple[str | None, list[str]]:
    if args and _is_code(args[0]):
        return args[0], args[1:]
    return None, args


def _chart_points(points: list, end_time: date, days: int) -> list:
    start_time = end_time - timedelta(days=days)
    return [point for point in points if point.date >= start_time]


def handle_query(user_id: str, args: list[str]) -> None:

    code, words = _split_args(args)

    if not words:
        send.send_text(user_id, f"请至少指定一个区间词：{_WORDS_TEXT}")
        return

    for word in words:
        if word not in RANGE_WORDS:
            send.send_text(
                user_id, f"区间词不合法：{word}\n可用区间词：{_WORDS_TEXT}"
            )
            return

    if code is None:
        watchlist = db.list_watch(user_id)
        if not watchlist:
            send.send_text(user_id, "你的自选列表为空，请先添加：基金 自选 添加 <代码>")
            return
        targets = list(watchlist)
    else:
        targets = [(code, code)]

    max_days = max(RANGE_WORDS[word] for word in words)
    end_time = _today()
    start_time = end_time - timedelta(days=max_days)
    chart_words = sorted(
        (word for word in words if word != "今天"),
        key=lambda word: RANGE_WORDS[word],
    )

    blocks: list[FundBlock] = []
    failures: list[str] = []

    for fund_code, fund_name in targets:
        try:
            report = fetcher.fetch(fund_code, start_time, end_time)
        except Exception:
            failures.append(fund_code)
            continue
        if not report.points:
            failures.append(fund_code)
            continue

        points = report.points
        last = points[-1]
        blocks.append(
            FundBlock(
                code=fund_code,
                name=fund_name,
                day_change=last.growth,
                day_change_date=last.date,
                updated_today=last.date == end_time,
                charts=[
                    ChartSpec(
                        caption=_RANGE_CAPTIONS[word],
                        points=_chart_points(points, end_time, RANGE_WORDS[word]),
                    )
                    for word in chart_words
                ],
                table_points=list(points) if chart_words else [],
            )
        )

    if not blocks:
        send.send_text(
            user_id,
            "全部基金取数失败，未生成 PDF：\n" + "\n".join(failures),
        )
        return

    if failures:
        send.send_text(
            user_id,
            "以下基金取数失败，已跳过：\n" + "\n".join(failures),
        )

    try:
        data = render(blocks)
    except Exception:
        send.send_text(user_id, "PDF 生成失败，请稍后重试")
        return

    send.send_file(user_id, f"基金_{end_time:%Y%m%d}.pdf", data)
