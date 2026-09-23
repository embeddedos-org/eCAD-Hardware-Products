"""Capability discovery that never equates a missing tool with success."""

from __future__ import annotations

import shutil
import subprocess
from typing import Dict, Iterable

from .base import Capability

TOOL_COMMANDS = {
    "kicad": ("kicad-cli", "--version"),
    "ngspice": ("ngspice", "--version"),
    "verilator": ("verilator", "--version"),
    "iverilog": ("iverilog", "-V"),
    "openscad": ("openscad", "--version"),
}


def probe_executable(adapter: str, command: Iterable[str]) -> Capability:
    argv = list(command)
    executable = shutil.which(argv[0])
    if executable is None:
        return Capability(adapter=adapter, available=False, reason="TOOL_NOT_INSTALLED")
    try:
        completed = subprocess.run(
            [executable, *argv[1:]],
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return Capability(
            adapter=adapter,
            available=False,
            executable=executable,
            reason="VERSION_PROBE_TIMED_OUT",
        )
    except OSError as exc:
        return Capability(
            adapter=adapter,
            available=False,
            executable=executable,
            reason=f"VERSION_PROBE_ERROR:{exc}",
        )
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    version_line = output.splitlines()[0].strip() if output else None
    if completed.returncode != 0 and not version_line:
        return Capability(
            adapter=adapter,
            available=False,
            executable=executable,
            reason=f"VERSION_PROBE_EXIT_{completed.returncode}",
        )
    return Capability(
        adapter=adapter,
        available=True,
        executable=executable,
        version=version_line,
    )


def detect_mujoco() -> Capability:
    python = shutil.which("python3") or shutil.which("python")
    if python is None:
        return Capability(adapter="mujoco", available=False, reason="PYTHON_NOT_INSTALLED")
    try:
        completed = subprocess.run(
            [python, "-c", "import mujoco; print(mujoco.__version__)"],
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return Capability(adapter="mujoco", available=False, executable=python, reason="VERSION_PROBE_TIMED_OUT")
    except OSError as exc:
        return Capability(adapter="mujoco", available=False, executable=python, reason=f"VERSION_PROBE_ERROR:{exc}")
    if completed.returncode != 0:
        return Capability(adapter="mujoco", available=False, executable=python, reason="MUJOCO_NOT_INSTALLED")
    return Capability(
        adapter="mujoco",
        available=True,
        executable=python,
        version=completed.stdout.strip(),
    )


def detect_capabilities() -> Dict[str, Capability]:
    capabilities = {
        name: probe_executable(name, command)
        for name, command in TOOL_COMMANDS.items()
    }
    capabilities["mujoco"] = detect_mujoco()
    return capabilities
