"""把 service 传入的可渲染数据排成 PDF。"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from typing import Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfbase.pdfmetrics import stringWidth

from src.log import task_log
from src.model.fund import NavPoint
from src.pdf import fonts

MARGIN = 15 * mm
TITLE = "Invest_Message"

DARK = colors.HexColor("#222222")
GRAY = colors.HexColor("#808080")
LIGHT_GRAY = colors.HexColor("#d0d0d0")
DARK_BLUE = colors.HexColor("#1f3a5f")
UP = colors.HexColor("#c81e1e")
DOWN = colors.HexColor("#1e8e3e")


@dataclass(frozen=True)
class ChartSpec:
    caption: str
    points: list[NavPoint]


@dataclass(frozen=True)
class FundBlock:
    code: str
    name: str
    day_change: float | None
    day_change_date: date | None
    updated_today: bool
    charts: list[ChartSpec]
    table_points: list[NavPoint]


def _elapsed_ms(started: float) -> int:
    return int(round((time.perf_counter() - started) * 1000))


def _sign_color(value: float | None) -> colors.Color:
    if value is None or value == 0:
        return DARK
    return UP if value > 0 else DOWN


def _format_change(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.2f}%"


def _axis_bounds(changes: Sequence[float]) -> tuple[float, float]:
    values = list(changes) or [0.0]
    low, high = min(values), max(values)
    if high - low < 1e-9:
        low, high = low - 0.5, high + 0.5
    padding = (high - low) * 0.1
    return low - padding, high + padding


class _ChartFlowable(Flowable):
    """一张折线图：上方图注，下方 42mm 高的坐标区，不跨页。"""

    _CAPTION_HEIGHT = 6 * mm
    _CHART_HEIGHT = 42 * mm

    def __init__(self, spec: ChartSpec, font: str, bold_font: str) -> None:
        super().__init__()
        self._spec = spec
        self._font = font
        self._bold_font = bold_font
        self.width = 0
        self.height = self._CAPTION_HEIGHT + self._CHART_HEIGHT

    def wrap(self, availWidth: float, availHeight: float) -> tuple[float, float]:
        self.width = availWidth
        return self.width, self.height

    def draw(self) -> None:
        self.canv.setFillColor(DARK)
        self.canv.setFont(self._bold_font, 13)
        self.canv.drawCentredString(
            self.width / 2, self._CHART_HEIGHT + 2 * mm, self._spec.caption
        )
        self._draw_chart()

    def _draw_chart(self) -> None:
        canvas = self.canv
        points = list(self._spec.points)
        changes = (
            [(point.nav / points[0].nav - 1) * 100 for point in points]
            if points
            else [0.0]
        )
        low, high = _axis_bounds(changes)
        ticks = [low + (high - low) * index / 4 for index in range(5)]

        canvas.setFont(self._font, 12)
        labels = [_format_change(value) for value in ticks]
        label_width = max(stringWidth(label, self._font, 12) for label in labels) + 3 * mm
        x0, x1 = label_width, self.width
        y0, y1 = 7 * mm, self._CHART_HEIGHT - 1 * mm

        for value, label in zip(ticks, labels):
            y = y0 + (value - low) / (high - low) * (y1 - y0)
            canvas.setStrokeColor(LIGHT_GRAY)
            canvas.setLineWidth(0.3)
            canvas.line(x0, y, x1, y)
            canvas.setFillColor(GRAY)
            canvas.drawRightString(x0 - 2 * mm, y - 4, label)

        if len(points) >= 2:
            first_day = points[0].date
            span = (points[-1].date - first_day).days or 1
            canvas.setStrokeColor(DARK_BLUE)
            canvas.setLineWidth(1.2)
            path = canvas.beginPath()
            for index, point in enumerate(points):
                fraction = (point.date - first_day).days / span
                x = x0 + fraction * (x1 - x0)
                y = y0 + (changes[index] - low) / (high - low) * (y1 - y0)
                if index == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            canvas.drawPath(path, stroke=1, fill=0)

        if points:
            canvas.setFillColor(GRAY)
            canvas.setFont(self._font, 12)
            canvas.drawString(x0, 2.5 * mm, points[0].date.isoformat())
            canvas.drawRightString(x1, 2.5 * mm, points[-1].date.isoformat())


def _build_table(points: list[NavPoint], font: str, width: float) -> Table:
    ordered = sorted(points, key=lambda point: point.date, reverse=True)
    rows: list[list[str]] = [["日期", "单位净值", "涨跌幅"]]
    for point in ordered:
        rows.append(
            [
                point.date.isoformat(),
                f"{point.nav:.4f}",
                _format_change(point.growth),
            ]
        )

    table = Table(
        rows,
        colWidths=[width * 0.4, width * 0.3, width * 0.3],
        repeatRows=1,
    )
    style = [
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, DARK_BLUE),
    ]
    for index in range(1, len(rows)):
        style.append(("LINEBELOW", (0, index), (-1, index), 0.3, LIGHT_GRAY))
        style.append(
            (
                "TEXTCOLOR",
                (2, index),
                (2, index),
                _sign_color(ordered[index - 1].growth),
            )
        )
    table.setStyle(TableStyle(style))
    return table


def _day_label(updated_today: bool) -> str:
    return "今日涨跌幅" if updated_today else "上一交易日涨跌幅"


def _date_text(block: FundBlock) -> str:
    parts: list[str] = []
    if block.day_change_date is not None:
        parts.append(block.day_change_date.isoformat())
    if not block.updated_today:
        parts.append("今日未更新")
    return " ".join(parts)


def _build_story(
    blocks: list[FundBlock], font: str, bold_font: str
) -> list[Flowable]:
    body_width = A4[0] - MARGIN * 2
    title_style = ParagraphStyle(
        "title", fontName=font, fontSize=24, leading=30, alignment=TA_CENTER, textColor=DARK
    )
    name_style = ParagraphStyle(
        "name", fontName=font, fontSize=18, leading=24, textColor=DARK, wordWrap="CJK"
    )
    code_style = ParagraphStyle(
        "code", fontName=font, fontSize=11, leading=14, textColor=GRAY
    )
    label_style = ParagraphStyle(
        "label", fontName=font, fontSize=13, leading=17, textColor=DARK
    )
    date_style = ParagraphStyle(
        "date", fontName=font, fontSize=10.5, leading=14, textColor=GRAY
    )

    story: list[Flowable] = [Paragraph(TITLE, title_style), Spacer(1, 4 * mm)]
    for index, block in enumerate(blocks):
        if index:
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=LIGHT_GRAY,
                    spaceBefore=5 * mm,
                    spaceAfter=5 * mm,
                )
            )
        story.append(Paragraph(block.name, name_style))
        story.append(Paragraph(block.code, code_style))
        story.append(Spacer(1, 1.5 * mm))
        story.append(Paragraph(_day_label(block.updated_today), label_style))
        change_style = ParagraphStyle(
            "change",
            fontName=bold_font,
            fontSize=34,
            leading=40,
            textColor=_sign_color(block.day_change),
        )
        story.append(Paragraph(_format_change(block.day_change), change_style))
        date_text = _date_text(block)
        if date_text:
            story.append(Paragraph(date_text, date_style))
        for spec in block.charts:
            story.append(_ChartFlowable(spec, font, bold_font))
        if block.table_points:
            story.append(Spacer(1, 3 * mm))
            story.append(_build_table(block.table_points, font, body_width))
    return story


def render(blocks: list[FundBlock]) -> bytes:
    """把基金区块渲染为 PDF 字节流。内部失败向上抛出。"""

    started = time.perf_counter()
    try:
        if not blocks:
            raise ValueError("blocks 不能为空")
        font = fonts.register()
        bold_font = fonts.BOLD_NAME
        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
            title=TITLE,
            author=TITLE,
            subject=TITLE,
        )
        document.build(_build_story(blocks, font, bold_font))
        data = buffer.getvalue()
    except Exception:
        task_log.pdf(0, _elapsed_ms(started), "FAIL")
        raise
    task_log.pdf(len(data), _elapsed_ms(started), "OK")
    return data
