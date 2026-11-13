"""HTTP 入口。"""

from __future__ import annotations

import threading
from typing import Callable

from flask import Flask, jsonify, request

from config.settings import get_setting
from log import larkbot_log
from service import route

Handler = Callable[[str, list[str]], None]


def _run(handler: Handler, user_id: str, args: list[str]) -> None:
    """后台执行处理函数，异常不中断线程。"""
    try:
        handler(user_id, args)
    except Exception:
        pass


def _parse_request() -> tuple[str, list[str], str | None]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return "", [], "请求体必须是 JSON 对象"
    sender = payload.get("sender")
    if not isinstance(sender, str) or not sender:
        return "", [], "sender 必须是非空字符串"
    args = payload.get("args")
    if not isinstance(args, list) or any(not isinstance(item, str) for item in args):
        return "", [], "args 必须是字符串数组"
    return sender, list(args), None


def _make_view(handler: Handler) -> Callable[[], object]:
    def view():
        sender, args, error = _parse_request()
        url = request.url
        if error is not None:
            larkbot_log.receive(url, sender or "-", 400, 0)
            return jsonify({"code": 0, "message": error, "data": None}), 400

        larkbot_log.receive(url, sender, 200, 0)
        threading.Thread(
            target=_run, args=(handler, sender, args), daemon=True
        ).start()
        return jsonify({"code": 0, "message": "ok", "data": None}), 200

    return view


def create_app() -> Flask:
    """创建 Flask 应用，四个路由全部转交 service 的 route。"""

    app = Flask(__name__)
    handlers: tuple[tuple[str, Handler], ...] = (
        ("/help", lambda user_id, args: route.route_help(user_id)),
        ("/query", lambda user_id, args: route.route_query(user_id, args)),
        ("/watchlist", lambda user_id, args: route.route_watchlist(user_id, args)),
        ("/schedule", lambda user_id, args: route.route_schedule(user_id, args)),
    )
    for path, handler in handlers:
        app.add_url_rule(
            path, endpoint=path, view_func=_make_view(handler), methods=["POST"]
        )
    return app


def start() -> None:
    """启动 HTTP 服务，只监听 127.0.0.1。"""

    app = create_app()
    app.run(
        host="127.0.0.1",
        port=get_setting().port,
        threaded=True,
        use_reloader=False,
    )
