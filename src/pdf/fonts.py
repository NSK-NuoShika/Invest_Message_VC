"""注册中文字体，返回注册后的字体名。"""

from __future__ import annotations

import os
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_NAME = "SimSun"
BOLD_NAME = "SimSun-Bold"

# (文件名, .ttc 子字体序号)。按顺序尝试，找不到或加载失败就换下一个。
_NORMAL_CANDIDATES: tuple[tuple[str, int | None], ...] = (
    ("simsun.ttc", 0),
    ("simsun.ttf", None),
    ("SimsunExtG.ttf", None),
)
_BOLD_CANDIDATES: tuple[tuple[str, int | None], ...] = (
    ("simhei.ttf", None),
    ("simhei.ttc", 0),
    ("SimHei.ttf", None),
)

_registered = False


def _search_dirs() -> list[Path]:
    dirs: list[Path] = []
    for variable in ("WINDIR", "SystemRoot"):
        root = os.environ.get(variable)
        if root:
            dirs.append(Path(root) / "Fonts")
    dirs.extend(
        [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path.home() / ".fonts",
            Path.home() / ".local" / "share" / "fonts",
        ]
    )
    return [directory for directory in dirs if directory.is_dir()]


def _index_fonts() -> dict[str, Path]:
    index: dict[str, Path] = {}
    for directory in _search_dirs():
        for path in directory.rglob("*"):
            if path.suffix.lower() in {".ttf", ".ttc"}:
                index.setdefault(path.name.lower(), path)
    return index


def _register_one(name: str, path: Path, subfont: int | None) -> None:
    font = TTFont(name, str(path)) if subfont is None else TTFont(name, str(path), subfontIndex=subfont)
    pdfmetrics.registerFont(font)


def _register_first(
    name: str,
    index: dict[str, Path],
    candidates: tuple[tuple[str, int | None], ...],
) -> bool:
    for file_name, subfont in candidates:
        path = index.get(file_name.lower())
        if path is None:
            continue
        try:
            _register_one(name, path, subfont)
        except Exception:
            continue
        return True
    return False


def register() -> str:
    """注册宋体与加粗字体，返回正文使用的字体名。

    加粗字体优先宋体粗体，其次黑体，最后退化为常规字重。
    """

    global _registered, BOLD_NAME
    if _registered:
        return FONT_NAME

    index = _index_fonts()
    if not _register_first(FONT_NAME, index, _NORMAL_CANDIDATES):
        raise RuntimeError("未能注册中文字体：找不到可用的宋体字体文件")

    if _register_first(BOLD_NAME, index, _BOLD_CANDIDATES):
        bold = BOLD_NAME
    else:
        bold = FONT_NAME
        BOLD_NAME = FONT_NAME

    pdfmetrics.registerFontFamily(
        FONT_NAME,
        normal=FONT_NAME,
        bold=bold,
        italic=FONT_NAME,
        boldItalic=bold,
    )
    _registered = True
    return FONT_NAME
