"""`基金 自选 查询`。"""

from __future__ import annotations

from database import db
from larkbot import send

def handle_watchlist_query(user_id: str) -> None:

    rows = db.list_watch(user_id)
    if not rows:
        send.send_text(user_id, "自选列表为空")
        return
    send.send_text(user_id, "\n".join(f"{code} {name}" for code, name in rows))
