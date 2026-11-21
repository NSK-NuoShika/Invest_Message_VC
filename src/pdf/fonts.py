"""注册中文字体，返回常规与粗体字体名。"""

from __future__ import annotations

from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"

NORMAL_PATH = ASSETS_DIR / "SourceHanSerif-Regular.ttf"
BOLD_PATH = ASSETS_DIR / "SourceHanSerif-Bold.ttf"

NORMAL_NAME = "SourceHanSerifCN-Regular"
BOLD_NAME = "SourceHanSerifCN-Bold"

_registered = False


def _load(name: str, path: Path) -> TTFont:
    if not path.is_file():
        raise RuntimeError(f"字体文件不存在：{path}")

    font = TTFont(name, str(path))
    # 两个字体文件内部的 PostScript 名相同，reportlab 会按该名去重，
    # 导致粗体被静默替换成常规字重。改用注册名，保证两套字形分别嵌入。
    font.face.name = name.encode("ascii")
    return font


def register() -> tuple[str, str]:
    """注册常规与粗体中文字体，返回 (常规, 粗体) 字体名。"""

    global _registered
    if _registered:
        return NORMAL_NAME, BOLD_NAME

    pdfmetrics.registerFont(_load(NORMAL_NAME, NORMAL_PATH))
    pdfmetrics.registerFont(_load(BOLD_NAME, BOLD_PATH))

    _registered = True
    return NORMAL_NAME, BOLD_NAME
