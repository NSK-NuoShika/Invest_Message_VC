import ast
from datetime import date
from pathlib import Path

import pytest

from src.model.fund import FundReport, NavPoint

SRC = Path(__file__).resolve().parents[1] / "src"

# 除同包内的模块外，架构允许的跨包依赖。
ALLOWED_EDGES = {
    ("src.command", "src.service"),
    ("src.service", "src.database"),
    ("src.service", "src.fund"),
    ("src.service", "src.pdf"),
    ("src.service", "src.scheduler"),
    ("src.service", "src.larkbot"),
    ("src.scheduler", "src.database"),
    ("src.fund", "src.model"),
    ("src.pdf", "src.model"),
    ("src.larkbot", "src.config"),
}

# 所有模块都可以依赖的包。
UNIVERSAL_PACKAGES = {"src.config", "src.log", "src.model"}


def _package_of(path: Path) -> str:
    """文件所属的包。文件自身是模块，去掉最后一段即包名。"""

    relative = path.relative_to(SRC).with_suffix("")
    parts = list(relative.parts)[:-1]
    return ".".join(["src", *parts])


def _resolve_package(module: str) -> str:
    """把被导入的模块名折算为所属的包名。"""

    parts = module.split(".")
    if len(parts) <= 2:
        return module
    return ".".join(parts[:2])


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
        package = _package_of(path)
        for lineno, module in _imports(path):
            if module != "src" and not module.startswith("src."):
                continue
            target = _resolve_package(module)
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
