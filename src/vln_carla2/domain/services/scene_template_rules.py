"""Pure rules for scene-template validation."""

from __future__ import annotations


SCENE_TEMPLATE_SCHEMA_V1 = 1


def assert_supported_schema(schema_version: int) -> None:
    """Raise when scene-template schema version is unsupported."""
    if schema_version != SCENE_TEMPLATE_SCHEMA_V1:
        raise ValueError(
            "unsupported scene schema version: "
            f"{schema_version} (supported={SCENE_TEMPLATE_SCHEMA_V1})"
        )


def assert_map_matches(*, expected_map_name: str, template_map_name: str) -> None:
    """Raise when runtime map and template map are different."""
    if expected_map_name != template_map_name:
        raise ValueError(
            "scene map mismatch: "
            f"runtime={expected_map_name} template={template_map_name}"
        )
