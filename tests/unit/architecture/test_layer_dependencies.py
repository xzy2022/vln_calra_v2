from __future__ import annotations

import ast
from pathlib import Path


LAYER_NAMES = {"domain", "usecases", "adapters", "infrastructure", "app"}


def test_layer_dependencies_follow_concentric_rules() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    source_root = repo_root / "src" / "vln_carla2"

    violations: list[str] = []

    for py_file in source_root.rglob("*.py"):
        relative_path = py_file.relative_to(source_root)
        source_layer = relative_path.parts[0]
        if source_layer not in LAYER_NAMES:
            continue

        module_name = "vln_carla2." + ".".join(relative_path.with_suffix("").parts)
        tree = ast.parse(py_file.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            for target in _import_targets(node=node, module_name=module_name):
                if not target.startswith("vln_carla2."):
                    continue
                target_parts = target.split(".")
                if len(target_parts) < 2:
                    continue
                target_layer = target_parts[1]
                if target_layer not in LAYER_NAMES:
                    continue

                reason = _violation_reason(
                    source_layer=source_layer,
                    target_layer=target_layer,
                    target_module=target,
                )
                if reason:
                    violations.append(
                        f"{relative_path}:{node.lineno}: {target} :: {reason}"
                    )

    assert not violations, "Layer dependency violations:\n" + "\n".join(sorted(violations))


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
    source_layer: str,
    target_layer: str,
    target_module: str,
) -> str | None:
    if source_layer == "domain":
        if target_layer != "domain":
            return "domain can only depend on domain"
        return None

    if source_layer == "usecases":
        if target_layer not in {"domain", "usecases"}:
            return "usecases can only depend on domain/usecases"
        return None

    if source_layer == "adapters":
        if target_layer not in {"adapters", "usecases"}:
            return "adapters can only depend on adapters/usecases"
        return None

    if source_layer == "infrastructure":
        if target_layer in {"infrastructure", "domain"}:
            return None
        if target_layer == "usecases":
            if ".ports." in target_module or target_module.endswith(".ports"):
                return None
            return "infrastructure may depend on usecases only via usecases/**/ports"
        return "infrastructure can only depend on infrastructure/domain/usecases/**/ports"

    return None
