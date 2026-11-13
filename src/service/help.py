"""基金 帮助。"""

from __future__ import annotations

from larkbot import send

HELP_TEXT = """可用命令：
基金 帮助
基金 查询 <区间词…>
基金 查询 <代码> <区间词…>
基金 自选 查询
基金 自选 添加 <代码>
基金 自选 删除 <代码>
基金 定时 查询
基金 定时 添加 <HH:MM>
基金 定时 删除 <HH:MM>

区间词：今天、7天、30天、1年、3年、5年"""


def handle_help(user_id: str) -> None:
    send.send_text(user_id, HELP_TEXT)
