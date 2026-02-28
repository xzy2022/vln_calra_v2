from __future__ import annotations

import ast
from pathlib import Path


def test_cli_commands_do_not_import_usecases_modules() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    commands_path = repo_root / "src" / "vln_carla2" / "adapters" / "cli" / "commands.py"

    tree = ast.parse(commands_path.read_text(encoding="utf-8"))
    imported_modules: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.append(node.module)

    violations = [name for name in imported_modules if name.startswith("vln_carla2.usecases")]
    assert not violations, f"commands.py must not import usecases modules: {violations}"


def test_bootstrap_only_exposes_composition_root_constructor() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    bootstrap_path = repo_root / "src" / "vln_carla2" / "app" / "bootstrap.py"
    tree = ast.parse(bootstrap_path.read_text(encoding="utf-8"))

    function_defs = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    class_defs = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]

    assert function_defs == ["build_cli_application"]
    assert class_defs == []

