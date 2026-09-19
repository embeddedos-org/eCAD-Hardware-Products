"""KiCad CLI adapter for machine-executed PCB design-rule checks."""

from __future__ import annotations

from ..models import ExecutionStatus, Verdict
from .base import Adapter, AdapterRequest, AdapterResult, Capability
from .capabilities import probe_executable
from .process import ProcessRequest, run_process


class KiCadAdapter(Adapter):
    name = "kicad"

    def capability(self) -> Capability:
        return probe_executable(self.name, ("kicad-cli", "--version"))

    def run(self, request: AdapterRequest) -> AdapterResult:
        capability = self.capability()
        if not capability.available:
            return AdapterResult(
                adapter=self.name,
                execution_status=ExecutionStatus.UNAVAILABLE,
                verdict=Verdict.BLOCKED,
                reason_code=capability.reason or "TOOL_NOT_INSTALLED",
                summary="KiCad CLI is unavailable",
            )
        if not request.input_files:
            return AdapterResult(
                adapter=self.name,
                execution_status=ExecutionStatus.UNAVAILABLE,
                verdict=Verdict.BLOCKED,
                reason_code="PCB_INPUT_MISSING",
                summary="KiCad board input is missing",
                tool_version=capability.version,
            )
        board = request.input_files[0].resolve()
        relative = board.relative_to(request.product_root.resolve()).as_posix()
        process = run_process(
            ProcessRequest(
                argv=[
                    capability.executable or "kicad-cli",
                    "pcb",
                    "drc",
                    "--exit-code-violations",
                    "--output",
                    "kicad-drc.rpt",
                    relative,
                ],
                input_root=request.product_root,
                input_files=request.input_files,
                timeout_seconds=request.timeout_seconds,
            )
        )
        verdict = (
            Verdict.BLOCKED
            if process.execution_status is ExecutionStatus.UNAVAILABLE
            else Verdict.INCONCLUSIVE
            if process.execution_status is not ExecutionStatus.COMPLETED
            else Verdict.PASS
            if process.returncode == 0
            else Verdict.FAIL
        )
        return AdapterResult(
            adapter=self.name,
            execution_status=process.execution_status,
            verdict=verdict,
            reason_code=process.reason_code,
            summary="KiCad DRC completed" if verdict is Verdict.PASS else "KiCad DRC did not pass",
            command=process.argv,
            tool_version=capability.version,
            stdout=process.stdout,
            stderr=process.stderr,
            output_files=process.outputs,
        )
