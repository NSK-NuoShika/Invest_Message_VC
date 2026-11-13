"""`基金 定时 添加`。"""

from __future__ import annotations

import re

from database import db
from larkbot import send
from log import schedule_log
from scheduler import jobs

_TIME_PATTERN = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")


def handle_schedule_add(user_id: str, args: list[str]) -> None:

    if not args:
        send.send_text(user_id, "参数不足：基金 定时 添加 <HH:MM>")
        return
    if len(args) > 1:
        send.send_text(user_id, "参数过多：一次只能添加一个时间")
        return

    hhmm = args[0]
    if not _TIME_PATTERN.match(hhmm):
        send.send_text(user_id, "时间格式错误，应为 HH:MM（24 小时制）")
        return

    if not db.add_schedule(user_id, hhmm):
        send.send_text(user_id, "该时间点已存在")
        return

    jobs.add(user_id, hhmm)
    schedule_log.add(user_id, hhmm)
    send.send_text(user_id, f"已添加定时：{hhmm}")
