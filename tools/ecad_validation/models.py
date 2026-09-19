"""Typed validation results with fail-closed aggregation semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from .policy import CONTRACT_VERSION, REQUIRED_GATES


class ExecutionStatus(str, Enum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"
    TIMED_OUT = "timed_out"
    CRASHED = "crashed"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_RUN = "NOT_RUN"
    BLOCKED = "BLOCKED"
    INCONCLUSIVE = "INCONCLUSIVE"


class GateLevel(str, Enum):
    V0 = "V0"
    V1 = "V1"
    V2 = "V2"
    V3 = "V3"
    V4 = "V4"


class Domain(str, Enum):
    EDA_CIRCUIT = "eda_circuit"
    PHYSICAL_DESIGN = "physical_design"
    SYSTEM_DESIGN = "system_design"
    DEVICE_MODELING = "device_modeling"
    DATA_MANAGEMENT = "data_management"
    INTEGRATED_PHYSICS = "integrated_physics"


class Layer(str, Enum):
    DESIGN = "design"
    MODEL = "model"
    SIMULATION = "simulation"
    VALIDATION = "validation"


@dataclass(frozen=True)
class EvidenceReference:
    path: str
    sha256: str
    media_type: str = "application/octet-stream"
    size_bytes: int = 0
    evidence_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id or f"evidence:{self.sha256[:16]}",
            "path": self.path,
            "sha256": self.sha256,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
        }


@dataclass
class CheckResult:
    check_id: str
    gate: GateLevel
    domain: Domain
    layer: Layer
    execution_status: ExecutionStatus
    verdict: Verdict
    reason_code: str
    summary: str
    required: bool = True
    tool_id: str = "ecad-validator"
    tool_version: str = ""
    tool_invocation: List[str] = field(default_factory=list)
    tool_settings: Dict[str, Any] = field(default_factory=dict)
    requirement_ids: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    evidence: List[EvidenceReference] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    generated_evidence: Dict[str, bytes] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not self.check_id.strip():
            raise ValueError("check_id must not be empty")
        if self.verdict is Verdict.PASS and self.execution_status is not ExecutionStatus.COMPLETED:
            raise ValueError("PASS requires execution_status=completed")
        if self.execution_status is ExecutionStatus.UNAVAILABLE and self.verdict is Verdict.PASS:
            raise ValueError("an unavailable tool cannot pass")
        if self.verdict is Verdict.PASS and not self.evidence:
            raise ValueError("PASS requires at least one evidence reference")
        if not self.requirement_ids:
            self.requirement_ids = [
                {
                    GateLevel.V0: "POLICY:V0-SCHEMA",
                    GateLevel.V1: "POLICY:V1-SANITY",
                    GateLevel.V2: "POLICY:V2-INVARIANTS",
                    GateLevel.V3: "POLICY:V3-GOLDEN",
                    GateLevel.V4: "POLICY:V4-CORNER",
                }[self.gate]
            ]

    def to_dict(self) -> Dict[str, Any]:
        evidence = []
        for index, reference in enumerate(self.evidence):
            value = reference.to_dict()
            if not reference.evidence_id:
                value["evidence_id"] = (
                    f"evidence:{self.check_id}:{index}:{reference.sha256[:16]}"
                )
            evidence.append(value)
        return {
            "check_id": self.check_id,
            "gate": self.gate.value,
            "domain": self.domain.value,
            "layer": self.layer.value,
            "tool_id": self.tool_id,
            "execution_status": self.execution_status.value,
            "verdict": self.verdict.value,
            "reason_code": self.reason_code,
            "summary": self.summary,
            "required": self.required,
            "requirement_ids": self.requirement_ids,
            "metrics": self.metrics,
            "evidence": evidence,
            "findings": self.findings,
        }


@dataclass
class GateResult:
    gate: GateLevel
    verdict: Verdict
    checks: List[CheckResult] = field(default_factory=list)

    @classmethod
    def from_checks(cls, gate: GateLevel, checks: List[CheckResult]) -> "GateResult":
        required = [check for check in checks if check.required]
        if not required:
            verdict = Verdict.BLOCKED
        elif any(check.verdict is Verdict.FAIL for check in required):
            verdict = Verdict.FAIL
        elif any(check.verdict is Verdict.BLOCKED for check in required):
            verdict = Verdict.BLOCKED
        elif any(check.verdict is Verdict.INCONCLUSIVE for check in required):
            verdict = Verdict.INCONCLUSIVE
        elif any(check.verdict is Verdict.NOT_RUN for check in required):
            verdict = Verdict.NOT_RUN
        elif any(check.verdict is Verdict.WARNING for check in required):
            # A warning can be informative, but it cannot satisfy a required check.
            verdict = Verdict.BLOCKED
        elif all(check.verdict is Verdict.PASS for check in required):
            verdict = Verdict.PASS
        else:
            verdict = Verdict.INCONCLUSIVE
        return cls(gate=gate, verdict=verdict, checks=checks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate": self.gate.value,
            "verdict": self.verdict.value,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass
class ProductRunResult:
    product_id: str
    product_path: str
    source_commit: str
    source_dirty: bool
    input_sha256: str
    started_at: str
    completed_at: str
    gates: List[GateResult]
    tools: List[Dict[str, Any]] = field(default_factory=list)
    contract_version: str = CONTRACT_VERSION

    @property
    def overall_verdict(self) -> Verdict:
        by_gate = {gate.gate.value: gate for gate in self.gates}
        if any(name not in by_gate for name in REQUIRED_GATES):
            return Verdict.BLOCKED
        ordered = [by_gate[name].verdict for name in REQUIRED_GATES]
        if any(value is Verdict.FAIL for value in ordered):
            return Verdict.FAIL
        if any(value is Verdict.BLOCKED for value in ordered):
            return Verdict.BLOCKED
        if any(value is Verdict.INCONCLUSIVE for value in ordered):
            return Verdict.INCONCLUSIVE
        if any(value is Verdict.NOT_RUN for value in ordered):
            return Verdict.NOT_RUN
        if any(value is Verdict.WARNING for value in ordered):
            return Verdict.BLOCKED
        return Verdict.PASS if all(value is Verdict.PASS for value in ordered) else Verdict.INCONCLUSIVE

    @property
    def eligible_for_ebuild(self) -> bool:
        return self.overall_verdict is Verdict.PASS

    @property
    def execution_complete(self) -> bool:
        return all(
            check.execution_status is ExecutionStatus.COMPLETED
            for gate in self.gates
            for check in gate.checks
        )

    def to_receipt(self) -> Dict[str, Any]:
        return {
            "$schema": "https://embeddedos.org/schemas/hardware-validation/v1/validation-receipt.schema.json",
            "contract_version": self.contract_version,
            "receipt_id": f"receipt:{self.product_id}:{self.input_sha256[:16]}",
            "product": {"id": self.product_id, "path": self.product_path},
            "source": {
                "repository": "https://github.com/embeddedos-org/eCAD-Hardware-Products",
                "commit": self.source_commit,
                "dirty": self.source_dirty,
                "input_sha256": self.input_sha256,
            },
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "tools": self.tools,
            "gates": [gate.to_dict() for gate in self.gates],
            "overall_verdict": self.overall_verdict.value,
            "execution_complete": self.execution_complete,
            "eligible_for_ebuild": self.eligible_for_ebuild,
        }


@dataclass
class RepositoryRunResult:
    source_commit: str
    products: List[ProductRunResult]
    inventory_sha256: str
    inventory_product_ids: List[str]
    contract_version: str = CONTRACT_VERSION

    @property
    def selection_complete(self) -> bool:
        return bool(self.products) and all(
            {gate.gate for gate in product.gates} == set(GateLevel)
            for product in self.products
        )

    @property
    def all_products_executed(self) -> bool:
        return self.selection_complete and {
            product.product_id for product in self.products
        } == set(self.inventory_product_ids)

    @property
    def eligible_products(self) -> List[ProductRunResult]:
        return [product for product in self.products if product.eligible_for_ebuild]

    def to_summary(self) -> Dict[str, Any]:
        counts = {verdict.value: 0 for verdict in Verdict}
        for product in self.products:
            counts[product.overall_verdict.value] += 1
        return {
            "contract_version": self.contract_version,
            "source_commit": self.source_commit,
            "inventory_sha256": self.inventory_sha256,
            "product_count": len(self.products),
            "inventory_product_count": len(self.inventory_product_ids),
            "selection_complete": self.selection_complete,
            "all_products_executed": self.all_products_executed,
            "eligible_products": sorted(product.product_id for product in self.eligible_products),
            "verdict_counts": counts,
        }
