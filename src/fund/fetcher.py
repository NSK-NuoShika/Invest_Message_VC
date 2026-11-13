from __future__ import annotations

import math
import time
from datetime import date

import akshare as ak
import pandas as pd

from src.log import task_log
from src.model.fund import FundReport, NavPoint

_INDICATOR = "单位净值走势"


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
    try:
        frame = ak.fund_open_fund_info_em(symbol=code, indicator=_INDICATOR)
        points = _to_points(frame, start_time, end_time)
    except Exception:
        task_log.fetch(code, _elapsed_ms(started), "FAIL")
        raise
    task_log.fetch(code, _elapsed_ms(started), "OK")
    return FundReport(code=code, name=code, points=points)
