"""Application composition root."""

from __future__ import annotations

from vln_carla2.app.wiring.cli_workflow_gateway import CliWorkflowGateway
from vln_carla2.infrastructure.carla.runtime_session_registry_adapter import (
    RuntimeSessionRegistryAdapter,
)
from vln_carla2.infrastructure.carla.server_control_adapter import CarlaServerControlAdapter
from vln_carla2.infrastructure.filesystem.scene_template_loader_adapter import (
    SceneTemplateLoaderAdapter,
)
from vln_carla2.usecases.cli.service import CliApplicationService
from vln_carla2.usecases.cli.ports.inbound import CliApplicationUseCasePort


def build_cli_application() -> CliApplicationUseCasePort:
    """Build concrete CLI use-case application implementation."""
    return CliApplicationService(
        workflows=CliWorkflowGateway(),
        server_control=CarlaServerControlAdapter(),
        runtime_registry=RuntimeSessionRegistryAdapter(),
        scene_template_loader=SceneTemplateLoaderAdapter(),
    )

