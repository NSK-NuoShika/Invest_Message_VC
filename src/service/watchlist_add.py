"""`基金 自选 添加`。"""

from __future__ import annotations

from datetime import date, timedelta

from database import db
from fund import fetcher
from larkbot import send


def _is_code(value: str) -> bool:
    return len(value) == 6 and value.isdigit()


def handle_watchlist_add(user_id: str, args: list[str]) -> None:

    if not args:
        send.send_text(user_id, "参数不足：基金 自选 添加 <代码>")
        return
    if len(args) > 1:
        send.send_text(user_id, "参数过多：一次只能添加一只基金")
        return

    code = args[0]
    if not _is_code(code):
        send.send_text(user_id, "基金代码必须是六位数字")
        return

    today = date.today()
    try:
        report = fetcher.fetch(code, today - timedelta(days=7), today)
    except Exception:
        send.send_text(user_id, "查询基金信息失败，请稍后重试")
        return

    if not report.points:
        send.send_text(user_id, "未找到该基金，或暂不支持该类型")
        return

    name = report.name if report.name != code else code
    if not db.add_watch(user_id, code, name):
        send.send_text(user_id, "该基金已在自选中")
        return

    send.send_text(user_id, f"已添加自选：{code} {name}")
