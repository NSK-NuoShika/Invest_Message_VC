"""`基金 定时 删除`。"""

from __future__ import annotations

import re

from src.database import db
from src.larkbot import send
from src.log import schedule_log
from src.scheduler import jobs

_TIME_PATTERN = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")


def handle_schedule_delete(user_id: str, args: list[str]) -> None:

    if not args:
        send.send_text(user_id, "参数不足：基金 定时 删除 <HH:MM>")
        return
    if len(args) > 1:
        send.send_text(user_id, "参数过多：一次只能删除一个时间点")
        return

    hhmm = args[0]
    if not _TIME_PATTERN.match(hhmm):
        send.send_text(user_id, "时间格式错误，应为 HH:MM（24 小时制）")
        return

    if not db.remove_schedule(user_id, hhmm):
        send.send_text(user_id, "该时间点不存在")
        return

    jobs.remove(user_id, hhmm)
    schedule_log.delete(user_id, hhmm)
    send.send_text(user_id, f"已删除定时：{hhmm}")
