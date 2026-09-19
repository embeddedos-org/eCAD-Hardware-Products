"""Typed interfaces implemented by external validation adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from ..models import ExecutionStatus, Verdict


@dataclass(frozen=True)
class Capability:
    adapter: str
    available: bool
    executable: Optional[str] = None
    version: Optional[str] = None
    reason: Optional[str] = None


@dataclass(frozen=True)
class AdapterRequest:
    case_id: str
    product_root: Path
    input_files: List[Path]
    arguments: List[str] = field(default_factory=list)
    timeout_seconds: int = 180
    seed: Optional[int] = None
    settings: Dict[str, object] = field(default_factory=dict)


@dataclass
class AdapterResult:
    adapter: str
    execution_status: ExecutionStatus
    verdict: Verdict
    reason_code: str
    summary: str
    command: List[str] = field(default_factory=list)
    tool_version: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    metrics: Dict[str, object] = field(default_factory=dict)
    output_files: List[Path] = field(default_factory=list)


class Adapter(ABC):
    name: str

    @abstractmethod
    def capability(self) -> Capability:
        """Report exact tool availability and version support."""

    @abstractmethod
    def run(self, request: AdapterRequest) -> AdapterResult:
        """Execute one validation case in an isolated workspace."""
