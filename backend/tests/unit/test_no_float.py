"""No money calculation uses float: enforced by static analysis of the code."""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
MONEY_PACKAGES = ("domain", "services", "repositories", "schemas", "models")


def test_money_code_never_uses_float() -> None:
    offenders = []
    for package in MONEY_PACKAGES:
        for path in (APP / package).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Name) and node.id == "float":
                    offenders.append(f"{path.relative_to(APP)}:{node.lineno}")
                if isinstance(node, ast.Constant) and type(node.value) is float:
                    offenders.append(f"{path.relative_to(APP)}:{node.lineno}")
    # money.py mentions float only to reject it; colors.py computes hues, not money;
    # export_files.py lays the PDF out in millimetres (its amounts stay Decimal).
    allowed = ("domain/money.py", "domain/colors.py", "services/export_files.py")
    offenders = [o for o in offenders if not o.startswith(allowed)]
    assert offenders == []
