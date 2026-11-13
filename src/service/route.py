"""二级命令的识别与分派。"""

from __future__ import annotations

from larkbot import send
from service import (
    help,
    query,
    schedule_add,
    schedule_delete,
    schedule_query,
    watchlist_add,
    watchlist_delete,
    watchlist_query,
)

_WATCHLIST_USAGE = "用法：基金 自选 查询 / 基金 自选 添加 <代码> / 基金 自选 删除 <代码>"
_SCHEDULE_USAGE = "用法：基金 定时 查询 / 基金 定时 添加 <HH:MM> / 基金 定时 删除 <HH:MM>"


def route_help(user_id: str) -> None:
    """`基金 帮助`。"""

    help.handle_help(user_id)


def route_query(user_id: str, args: list[str]) -> None:
    """`基金 查询`。"""

    query.handle_query(user_id, args)


def route_watchlist(user_id: str, args: list[str]) -> None:
    """`基金 自选 <子命令>`。"""

    sub = args[0] if args else ""
    if sub == "查询":
        watchlist_query.handle_watchlist_query(user_id)
    elif sub == "添加":
        watchlist_add.handle_watchlist_add(user_id, args[1:])
    elif sub == "删除":
        watchlist_delete.handle_watchlist_delete(user_id, args[1:])
    else:
        send.send_text(user_id, _WATCHLIST_USAGE)


def route_schedule(user_id: str, args: list[str]) -> None:
    """`基金 定时 <子命令>`。"""

    sub = args[0] if args else ""
    if sub == "查询":
        schedule_query.handle_schedule_query(user_id)
    elif sub == "添加":
        schedule_add.handle_schedule_add(user_id, args[1:])
    elif sub == "删除":
        schedule_delete.handle_schedule_delete(user_id, args[1:])
    else:
        send.send_text(user_id, _SCHEDULE_USAGE)
