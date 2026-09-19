"""Icarus Verilog adapter that compiles and executes committed RTL testbenches."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ..models import ExecutionStatus, Verdict
from .base import Adapter, AdapterRequest, AdapterResult, Capability
from .capabilities import probe_executable


class HDLAdapter(Adapter):
    name = "iverilog"

    def capability(self) -> Capability:
        compiler = probe_executable("iverilog", ("iverilog", "-V"))
        if not compiler.available:
            return compiler
        if shutil.which("vvp") is None:
            return Capability(
                adapter=self.name,
                available=False,
                executable=compiler.executable,
                version=compiler.version,
                reason="VVP_NOT_INSTALLED",
            )
        return compiler

    def run(self, request: AdapterRequest) -> AdapterResult:
        capability = self.capability()
        if not capability.available:
            return AdapterResult(
                adapter=self.name,
                execution_status=ExecutionStatus.UNAVAILABLE,
                verdict=Verdict.BLOCKED,
                reason_code=capability.reason or "TOOL_NOT_INSTALLED",
                summary="Icarus Verilog execution capability is unavailable",
            )
        if not request.input_files:
            return AdapterResult(
                adapter=self.name,
                execution_status=ExecutionStatus.UNAVAILABLE,
                verdict=Verdict.BLOCKED,
                reason_code="RTL_INPUT_MISSING",
                summary="RTL sources and testbench are missing",
            )
        root = request.product_root.resolve()
        with tempfile.TemporaryDirectory(prefix="ecad-hdl-") as temporary:
            workspace = Path(temporary)
            relatives = []
            for source in request.input_files:
                resolved = source.resolve()
                try:
                    relative = resolved.relative_to(root)
                except ValueError as exc:
                    raise ValueError(f"RTL input escapes product root: {source}") from exc
                if source.is_symlink():
                    raise ValueError(f"RTL input may not be a symbolic link: {relative}")
                target = workspace / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(resolved, target)
                relatives.append(relative.as_posix())
            compile_command = [
                capability.executable or "iverilog",
                "-g2012",
                "-o",
                "simulation.vvp",
                *relatives,
                *request.arguments,
            ]
            try:
                compiled = subprocess.run(
                    compile_command,
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=request.timeout_seconds,
                    shell=False,
                )
                if compiled.returncode != 0:
                    return AdapterResult(
                        adapter=self.name,
                        execution_status=ExecutionStatus.COMPLETED,
                        verdict=Verdict.FAIL,
                        reason_code="RTL_COMPILE_FAILED",
                        summary="RTL compilation failed",
                        command=compile_command,
                        tool_version=capability.version,
                        stdout=compiled.stdout,
                        stderr=compiled.stderr,
                    )
                run_command = [shutil.which("vvp") or "vvp", "simulation.vvp"]
                executed = subprocess.run(
                    run_command,
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=request.timeout_seconds,
                    shell=False,
                )
            except subprocess.TimeoutExpired as exc:
                return AdapterResult(
                    adapter=self.name,
                    execution_status=ExecutionStatus.TIMED_OUT,
                    verdict=Verdict.INCONCLUSIVE,
                    reason_code="RTL_EXECUTION_TIMED_OUT",
                    summary="RTL compilation or execution timed out",
                    command=compile_command,
                    stdout=exc.stdout or "",
                    stderr=exc.stderr or "",
                )
            except OSError as exc:
                return AdapterResult(
                    adapter=self.name,
                    execution_status=ExecutionStatus.CRASHED,
                    verdict=Verdict.INCONCLUSIVE,
                    reason_code="RTL_EXECUTION_ERROR",
                    summary="RTL tool could not execute",
                    command=compile_command,
                    stderr=str(exc),
                )
            return AdapterResult(
                adapter=self.name,
                execution_status=ExecutionStatus.COMPLETED,
                verdict=Verdict.PASS if executed.returncode == 0 else Verdict.FAIL,
                reason_code="RTL_TESTBENCH_PASSED" if executed.returncode == 0 else "RTL_TESTBENCH_FAILED",
                summary="committed RTL testbench executed",
                command=run_command,
                tool_version=capability.version,
                stdout=executed.stdout,
                stderr=executed.stderr,
            )
