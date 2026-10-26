"""Nenhum cálculo monetário usa float: garantido por análise do código."""

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
    # money.py menciona float só para o rejeitar.
    offenders = [o for o in offenders if not o.startswith("domain/money.py")]
    assert offenders == []
