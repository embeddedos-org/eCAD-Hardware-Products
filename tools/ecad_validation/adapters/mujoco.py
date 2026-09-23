"""MuJoCo adapter for reviewed Python-based integrated-physics cases."""

from __future__ import annotations

from ..models import ExecutionStatus, Verdict
from .base import AdapterRequest, AdapterResult, Capability
from .capabilities import detect_mujoco
from .python_control import PythonControlAdapter


class MujocoAdapter(PythonControlAdapter):
    name = "mujoco"

    def capability(self) -> Capability:
        return detect_mujoco()

    def run(self, request: AdapterRequest) -> AdapterResult:
        capability = self.capability()
        if not capability.available:
            return AdapterResult(
                adapter=self.name,
                execution_status=ExecutionStatus.UNAVAILABLE,
                verdict=Verdict.BLOCKED,
                reason_code=capability.reason or "MUJOCO_NOT_INSTALLED",
                summary="MuJoCo validation capability is unavailable",
            )
        result = super().run(request)
        result.adapter = self.name
        result.tool_version = capability.version
        return result
