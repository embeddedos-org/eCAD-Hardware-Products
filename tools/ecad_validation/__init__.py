"""Strict, evidence-backed validation contracts for eCAD products."""

from .models import (
    CheckResult,
    Domain,
    ExecutionStatus,
    GateLevel,
    GateResult,
    Layer,
    ProductRunResult,
    RepositoryRunResult,
    Verdict,
)

__all__ = [
    "CheckResult",
    "Domain",
    "ExecutionStatus",
    "GateLevel",
    "GateResult",
    "Layer",
    "ProductRunResult",
    "RepositoryRunResult",
    "Verdict",
]
