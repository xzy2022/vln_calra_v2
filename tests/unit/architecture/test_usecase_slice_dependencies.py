from __future__ import annotations

import ast
from pathlib import Path


SLICE_NAMES = {"control", "runtime", "scene", "exp", "cli", "shared"}


def test_usecase_slice_dependencies_are_shared_or_api_only() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    usecases_root = repo_root / "src" / "vln_carla2" / "usecases"

    violations: list[str] = []

    for py_file in usecases_root.rglob("*.py"):
        relative_path = py_file.relative_to(usecases_root)
        source_slice = relative_path.parts[0]
        if source_slice not in SLICE_NAMES:
            continue

        module_name = "vln_carla2.usecases." + ".".join(relative_path.with_suffix("").parts)
        tree = ast.parse(py_file.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            for target in _import_targets(node=node, module_name=module_name):
                if not target.startswith("vln_carla2.usecases."):
                    continue
                target_parts = target.split(".")
                if len(target_parts) < 3:
                    continue
                target_slice = target_parts[2]
                if target_slice not in SLICE_NAMES:
                    continue

                reason = _violation_reason(
                    source_slice=source_slice,
                    target_slice=target_slice,
                    target_module=target,
                )
                if reason:
                    violations.append(
                        f"{relative_path}:{node.lineno}: {target} :: {reason}"
                    )

    assert not violations, (
        "Usecase slice dependency violations:\n" + "\n".join(sorted(violations))
    )


def _import_targets(*, node: ast.AST, module_name: str) -> list[str]:
    targets: list[str] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            targets.append(alias.name)
        return targets

    if not isinstance(node, ast.ImportFrom):
        return targets

    if node.level == 0:
        if node.module:
            targets.append(node.module)
        return targets

    base_parts = module_name.split(".")[:-node.level]
    if node.module:
        base_parts = base_parts + node.module.split(".")
    if base_parts:
        targets.append(".".join(base_parts))
    return targets


def _violation_reason(
    *,
    source_slice: str,
    target_slice: str,
    target_module: str,
) -> str | None:
    if source_slice == target_slice:
        return None

    if source_slice == "shared":
        return "shared can only depend on shared (and domain)"

    if target_slice == "shared":
        return None

    if _is_api_module(target_slice=target_slice, target_module=target_module):
        return None

    return "cross-slice imports must use usecases.<slice>.api or usecases.shared"


def _is_api_module(*, target_slice: str, target_module: str) -> bool:
    api_module = f"vln_carla2.usecases.{target_slice}.api"
    return target_module == api_module or target_module.startswith(api_module + ".")

