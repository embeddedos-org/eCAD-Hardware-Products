"""Adapter for deterministic Python models that emit one JSON metrics object."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from ..models import ExecutionStatus, Verdict
from .base import Adapter, AdapterRequest, AdapterResult, Capability
from .process import ProcessRequest, run_process


class PythonControlAdapter(Adapter):
    name = "python_control"

    def capability(self) -> Capability:
        executable = shutil.which(Path(sys.executable).name) or sys.executable
        return Capability(
            adapter=self.name,
            available=Path(executable).exists(),
            executable=executable,
            version=sys.version.split()[0],
            reason=None if Path(executable).exists() else "PYTHON_NOT_INSTALLED",
        )

    def run(self, request: AdapterRequest) -> AdapterResult:
        capability = self.capability()
        if not capability.available or not request.input_files:
            return AdapterResult(
                adapter=self.name,
                execution_status=ExecutionStatus.UNAVAILABLE,
                verdict=Verdict.BLOCKED,
                reason_code=capability.reason or "MODEL_INPUT_MISSING",
                summary="Python model cannot be executed",
                tool_version=capability.version,
            )
        script = request.input_files[0].resolve()
        try:
            relative = script.relative_to(request.product_root.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError(f"Python model escapes product root: {script}") from exc
        process = run_process(
            ProcessRequest(
                argv=[capability.executable or sys.executable, relative, *request.arguments],
                input_root=request.product_root,
                input_files=request.input_files,
                timeout_seconds=request.timeout_seconds,
                environment={"ECAD_VALIDATION_SEED": str(request.seed)} if request.seed is not None else {},
            )
        )
        if process.execution_status is ExecutionStatus.UNAVAILABLE:
            verdict = Verdict.BLOCKED
        elif process.execution_status is ExecutionStatus.TIMED_OUT:
            verdict = Verdict.INCONCLUSIVE
        elif process.execution_status is not ExecutionStatus.COMPLETED:
            verdict = Verdict.INCONCLUSIVE
        elif process.returncode != 0:
            verdict = Verdict.FAIL
        else:
            verdict = Verdict.PASS

        metrics = {}
        if verdict is Verdict.PASS:
            lines = [line.strip() for line in process.stdout.splitlines() if line.strip()]
            parse_failed = False
            try:
                metrics = json.loads(lines[-1]) if lines else {}
            except json.JSONDecodeError:
                verdict = Verdict.INCONCLUSIVE
                process.reason_code = "METRICS_JSON_INVALID"
                parse_failed = True
            if not parse_failed and (not isinstance(metrics, dict) or not metrics):
                verdict = Verdict.INCONCLUSIVE
                process.reason_code = "METRICS_JSON_MISSING"
            if not isinstance(metrics, dict):
                metrics = {}
        return AdapterResult(
            adapter=self.name,
            execution_status=process.execution_status,
            verdict=verdict,
            reason_code=process.reason_code,
            summary="Python model execution completed" if verdict is Verdict.PASS else "Python model did not produce passing evidence",
            command=process.argv,
            tool_version=capability.version,
            stdout=process.stdout,
            stderr=process.stderr,
            metrics=metrics,
            output_files=process.outputs,
        )
