"""`基金 自选 删除`。"""

from __future__ import annotations

from src.database import db
from src.larkbot import send

def _is_code(value: str) -> bool:
    return len(value) == 6 and value.isdigit()


def handle_watchlist_delete(user_id: str, args: list[str]) -> None:
    """校验格式后删库。"""

    if not args:
        send.send_text(user_id, "参数不足：基金 自选 删除 <代码>")
        return
    if len(args) > 1:
        send.send_text(user_id, "参数过多：一次只能删除一只基金")
        return

    code = args[0]
    if not _is_code(code):
        send.send_text(user_id, "基金代码必须是六位数字")
        return

    if not db.remove_watch(user_id, code):
        send.send_text(user_id, "该基金不在自选中")
        return

    send.send_text(user_id, f"已删除自选：{code}")
