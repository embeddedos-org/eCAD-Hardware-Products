"""Hardened subprocess execution shared by all external-tool adapters."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional

from ..models import ExecutionStatus

MAX_CAPTURE_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True)
class ProcessRequest:
    argv: List[str]
    input_root: Path
    input_files: List[Path]
    timeout_seconds: int = 180
    environment: Mapping[str, str] = field(default_factory=dict)


@dataclass
class ProcessResult:
    execution_status: ExecutionStatus
    reason_code: str
    argv: List[str]
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    workspace: Optional[Path] = None
    outputs: List[Path] = field(default_factory=list)


def _limited(text: str) -> str:
    data = text.encode("utf-8", errors="replace")
    if len(data) <= MAX_CAPTURE_BYTES:
        return text
    return data[:MAX_CAPTURE_BYTES].decode("utf-8", errors="replace") + "\n[output truncated]"


def run_process(request: ProcessRequest) -> ProcessResult:
    """Run without a shell in a temporary workspace containing copied inputs."""
    if not request.argv:
        raise ValueError("process argv must not be empty")
    root = request.input_root.resolve()
    with tempfile.TemporaryDirectory(prefix="ecad-validation-") as temporary:
        workspace = Path(temporary)
        input_relatives = set()
        for source in request.input_files:
            resolved = source.resolve()
            relative = Path(
                os.path.relpath(
                    os.path.abspath(str(source)),
                    os.path.abspath(str(request.input_root)),
                )
            )
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"adapter input escapes product root: {source}")
            ancestor = resolved
            for _part in relative.parts:
                ancestor = ancestor.parent
            try:
                contained = os.path.samefile(ancestor, root)
            except OSError:
                contained = False
            if not contained:
                raise ValueError(f"adapter input escapes product root: {source}")
            if source.is_symlink():
                raise ValueError(f"adapter inputs may not be symbolic links: {relative}")
            input_relatives.add(relative)
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(resolved, target)

        executable = shutil.which(request.argv[0])
        if executable is None:
            return ProcessResult(
                execution_status=ExecutionStatus.UNAVAILABLE,
                reason_code="TOOL_NOT_INSTALLED",
                argv=request.argv,
            )

        environment: Dict[str, str] = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(workspace / ".home"),
            "TMPDIR": str(workspace / ".tmp"),
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
        }
        for key in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"):
            if key in os.environ:
                environment[key] = os.environ[key]
        environment.update({str(key): str(value) for key, value in request.environment.items()})
        Path(environment["HOME"]).mkdir(parents=True, exist_ok=True)
        Path(environment["TMPDIR"]).mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            environment["TEMP"] = environment["TMPDIR"]
            environment["TMP"] = environment["TMPDIR"]
        argv = [executable, *request.argv[1:]]
        try:
            completed = subprocess.run(
                argv,
                cwd=workspace,
                env=environment,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ProcessResult(
                execution_status=ExecutionStatus.TIMED_OUT,
                reason_code="TOOL_TIMED_OUT",
                argv=argv,
                stdout=_limited(exc.stdout or ""),
                stderr=_limited(exc.stderr or ""),
            )
        except OSError as exc:
            return ProcessResult(
                execution_status=ExecutionStatus.CRASHED,
                reason_code="TOOL_EXECUTION_ERROR",
                argv=argv,
                stderr=str(exc),
            )

        outputs = [
            path.relative_to(workspace)
            for path in workspace.rglob("*")
            if path.is_file() and path.relative_to(workspace) not in input_relatives
        ]
        return ProcessResult(
            execution_status=ExecutionStatus.COMPLETED,
            reason_code="TOOL_EXITED_ZERO" if completed.returncode == 0 else "TOOL_EXITED_NONZERO",
            argv=argv,
            returncode=completed.returncode,
            stdout=_limited(completed.stdout or ""),
            stderr=_limited(completed.stderr or ""),
            outputs=outputs,
        )
