"""`基金 定时 查询`。"""

from __future__ import annotations

from src.database import db
from src.larkbot import send

def handle_schedule_query(user_id: str) -> None:
    """按时间升序逐行列出该用户的定时。"""

    rows = db.list_user_schedules(user_id)
    if not rows:
        send.send_text(user_id, "定时列表为空")
        return
    send.send_text(user_id, "\n".join(rows))
