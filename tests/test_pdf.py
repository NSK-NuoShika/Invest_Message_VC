from datetime import date, timedelta
from pathlib import Path

import pytest
from reportlab.pdfbase import pdfmetrics

from model.fund import NavPoint
from pdf import fonts
from pdf.renderer import ChartSpec, FundBlock, render

TASK_LOG = Path(__file__).resolve().parents[1] / "log" / "task.log"
TODAY = date(2026, 11, 11)


def _reset_log() -> None:
    TASK_LOG.write_text("", encoding="utf-8")


def _log_rows() -> list[list[str]]:
    lines = TASK_LOG.read_text(encoding="utf-8").splitlines()
    return [line.split(" ") for line in lines if line]


def _points(count: int = 5) -> list[NavPoint]:
    start = TODAY - timedelta(days=count - 1)
    return [
        NavPoint(date=start + timedelta(days=index), nav=1.0 + 0.01 * index, growth=0.5)
        for index in range(count)
    ]


def _block(**overrides) -> FundBlock:
    values = {
        "code": "000001",
        "name": "华夏成长",
        "day_change": 0.55,
        "day_change_date": TODAY,
        "updated_today": True,
        "charts": [ChartSpec(caption="近 7 天", points=_points())],
        "table_points": _points(),
    }
    values.update(overrides)
    return FundBlock(**values)


def test_fonts_register_is_idempotent() -> None:
    name, bold = fonts.register()
    assert (name, bold) == (fonts.NORMAL_NAME, fonts.BOLD_NAME)
    assert fonts.register() == (name, bold)
    assert pdfmetrics.getFont(name) is not None
    assert pdfmetrics.getFont(bold) is not None
    assert pdfmetrics.getFont(bold) is not pdfmetrics.getFont(name)


def test_empty_blocks_raises_and_logs_fail() -> None:
    _reset_log()
    with pytest.raises(ValueError):
        render([])
    rows = _log_rows()
    assert len(rows) == 1
    assert rows[0][1:] == ["PDF", "0", rows[0][3], "FAIL"]


def test_render_returns_pdf_bytes_and_logs_ok() -> None:
    _reset_log()
    data = render([_block()])
    assert data.startswith(b"%PDF-")
    assert len(data) > 1000
    rows = _log_rows()
    assert len(rows) == 1
    assert rows[0][1] == "PDF"
    assert rows[0][2] == str(len(data))
    assert rows[0][4] == "OK"


def test_render_without_charts_or_table() -> None:
    _reset_log()
    data = render([_block(charts=[], table_points=[])])
    assert data.startswith(b"%PDF-")


def test_render_not_updated_today_and_negative_change() -> None:
    _reset_log()
    block = _block(
        day_change=-1.25,
        day_change_date=TODAY - timedelta(days=3),
        updated_today=False,
    )
    data = render([block])
    assert data.startswith(b"%PDF-")


def test_render_flat_change_uses_dark_color() -> None:
    _reset_log()
    data = render([_block(day_change=0.0)])
    assert data.startswith(b"%PDF-")


def test_render_table_with_missing_growth() -> None:
    _reset_log()
    points = _points()
    points[-1] = NavPoint(date=points[-1].date, nav=points[-1].nav, growth=None)
    data = render([_block(table_points=points, charts=[])])
    assert data.startswith(b"%PDF-")


def test_render_chart_with_single_point() -> None:
    _reset_log()
    single = [NavPoint(date=TODAY, nav=1.2, growth=0.1)]
    data = render(
        [_block(charts=[ChartSpec(caption="近 7 天", points=single)], table_points=single)]
    )
    assert data.startswith(b"%PDF-")


def test_render_multiple_blocks() -> None:
    _reset_log()
    blocks = [
        _block(),
        _block(code="161725", name="161725", day_change=-0.4, updated_today=False),
    ]
    data = render(blocks)
    assert data.startswith(b"%PDF-")
