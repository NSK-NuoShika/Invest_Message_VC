from __future__ import annotations

import gc
import math
import threading
import time
from datetime import date

import akshare as ak
import pandas as pd

from log import task_log
from model.fund import FundReport, NavPoint

_INDICATOR = "单位净值走势"

# akshare 每次取数都会在本进程内新建一个 V8 isolate，而该引擎的进程级初始化不是
# 线程安全的：多线程同时进入会踩坏其内部全局结构，使进程收到 SIGSEGV（Linux 退出
# 码 139）。锁必须全进程唯一，且覆盖 isolate 的创建、使用与销毁。
_LOCK = threading.Lock()


def _discard_traceback(exc: BaseException) -> None:
    """断开异常对上层栈帧的引用，使残留的 isolate 在当前锁内销毁。"""

    exc.__traceback__ = None
    exc.__context__ = None
    exc.__cause__ = None
    gc.collect()


def _elapsed_ms(started: float) -> int:
    return int(round((time.perf_counter() - started) * 1000))


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _to_points(frame: pd.DataFrame, start_time: date, end_time: date) -> list[NavPoint]:
    if frame is None or frame.empty:
        return []
    points: list[NavPoint] = []
    for point_date, nav, growth in frame.itertuples(index=False, name=None):
        if not isinstance(point_date, date):
            continue
        if point_date < start_time or point_date > end_time:
            continue
        nav_value = _to_float(nav)
        if nav_value is None:
            continue
        points.append(NavPoint(date=point_date, nav=nav_value, growth=_to_float(growth)))
    points.sort(key=lambda point: point.date)
    return points


def fetch(code: str, start_time: date, end_time: date) -> FundReport:
    """取回该基金在 [start_time, end_time] 内的净值记录。"""

    started = time.perf_counter()
    with _LOCK:
        try:
            frame = ak.fund_open_fund_info_em(symbol=code, indicator=_INDICATOR)
            points = _to_points(frame, start_time, end_time)
        except Exception as exc:
            task_log.fetch(code, _elapsed_ms(started), "FAIL")
            _discard_traceback(exc)
            raise

        name = code
        try:
            info = ak.fund_individual_basic_info_xq(symbol=code)
            matched = info.loc[info["item"] == "基金名称", "value"]
            if not matched.empty and not pd.isna(matched.iloc[0]):
                name = str(matched.iloc[0]).strip() or code
        except Exception:
            name = code

        task_log.fetch(code, _elapsed_ms(started), "OK")
        return FundReport(code=code, name=name, points=points)
