"""数据结构。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class NavPoint:
    """一个净值记录点。"""
    date: date
    nav: float
    growth: float | None = None


@dataclass(frozen=True)
class FundReport:
    """一只基金的净值序列。"""
    code: str
    name: str
    points: list[NavPoint]
