import ast
from datetime import date
from pathlib import Path

import pytest

from model.fund import FundReport, NavPoint

SRC = Path(__file__).resolve().parents[1] / "src"

# 本项目自己的顶层包。
INTERNAL_PACKAGES = {
    "command",
    "config",
    "database",
    "fund",
    "larkbot",
    "log",
    "model",
    "pdf",
    "scheduler",
    "service",
}

# 除同包内的模块外，架构允许的跨包依赖。
ALLOWED_EDGES = {
    ("command", "service"),
    ("service", "database"),
    ("service", "fund"),
    ("service", "pdf"),
    ("service", "scheduler"),
    ("service", "larkbot"),
    ("scheduler", "database"),
    ("fund", "model"),
    ("pdf", "model"),
    ("larkbot", "config"),
}

# 所有模块都可以依赖的包。
UNIVERSAL_PACKAGES = {"config", "log", "model"}


def _package_of(path: Path) -> str:
    """文件所属的包。文件自身是模块，去掉最后一段即包名。"""

    parts = list(path.relative_to(SRC).with_suffix("").parts)[:-1]
    return ".".join(parts)


def _resolve_package(module: str) -> str:
    """把被导入的模块名折算为所属的顶层包名。"""

    return module.split(".")[0]


def _imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            if node.module:
                found.append((node.lineno, node.module))
    return found


def test_import_boundaries() -> None:
    violations: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        # main.py 是装配入口，允许依赖任意包。
        if path == SRC / "main.py":
            continue
        package = _package_of(path)
        for lineno, module in _imports(path):
            target = _resolve_package(module)
            if target not in INTERNAL_PACKAGES:
                continue
            if target == package:
                continue
            if target in UNIVERSAL_PACKAGES:
                continue
            if (package, target) in ALLOWED_EDGES:
                continue
            violations.append(f"{path.relative_to(SRC.parent)}:{lineno} {package} -> {module}")
    assert not violations, "违反依赖方向：\n" + "\n".join(violations)


def test_nav_point_is_frozen() -> None:
    point = NavPoint(date=date(2026, 11, 11), nav=1.0)
    with pytest.raises(AttributeError):
        point.nav = 2.0  # type: ignore[misc]


def test_nav_point_growth_defaults_to_none() -> None:
    point = NavPoint(date=date(2026, 11, 11), nav=1.0)
    assert point.growth is None


def test_nav_point_carries_growth() -> None:
    point = NavPoint(date=date(2026, 11, 11), nav=1.0, growth=0.5)
    assert point.growth == 0.5


def test_fund_report_holds_points() -> None:
    report = FundReport(
        code="000001",
        name="000001",
        points=[NavPoint(date=date(2026, 11, 11), nav=1.0)],
    )
    assert report.points[0].nav == 1.0
