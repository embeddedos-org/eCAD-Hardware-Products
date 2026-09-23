"""V0-V4 orchestration for every committed eCAD product."""

from __future__ import annotations

import glob
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import validate_products as legacy

from .cases import execute_cases
from .discovery import InventoryEntry
from .hashing import canonical_json_bytes, hash_tree, sha256_bytes, sha256_file
from .models import (
    CheckResult,
    Domain,
    EvidenceReference,
    ExecutionStatus,
    GateLevel,
    GateResult,
    Layer,
    ProductRunResult,
    RepositoryRunResult,
    Verdict,
)


def repository_state(root: Path) -> tuple[str, bool]:
    """Return the exact source commit and whether the worktree has changes."""
    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"cannot establish repository provenance: {exc}") from exc
    if len(commit) != 40:
        raise ValueError(f"git returned a non-canonical commit ID: {commit!r}")
    return commit, dirty


def _evidence(path: Path, product_root: Path, media_type: str) -> List[EvidenceReference]:
    if not path.is_file():
        return []
    return [
        EvidenceReference(
            path=path.relative_to(product_root).as_posix(),
            sha256=sha256_file(path),
            media_type=media_type,
            size_bytes=path.stat().st_size,
        )
    ]


def _result(
    check_id: str,
    gate: GateLevel,
    domain: Domain,
    layer: Layer,
    verdict: Verdict,
    reason_code: str,
    summary: str,
    *,
    execution_status: ExecutionStatus = ExecutionStatus.COMPLETED,
    findings: Sequence[str] = (),
    evidence: Sequence[EvidenceReference] = (),
    generated_evidence: Optional[Dict[str, bytes]] = None,
) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        gate=gate,
        domain=domain,
        layer=layer,
        execution_status=execution_status,
        verdict=verdict,
        reason_code=reason_code,
        summary=summary,
        findings=list(findings),
        evidence=list(evidence),
        generated_evidence=generated_evidence or {},
    )


def _legacy_result(
    *,
    check_id: str,
    gate: GateLevel,
    domain: Domain,
    layer: Layer,
    result: legacy.Result,
    evidence: Sequence[EvidenceReference] = (),
) -> CheckResult:
    record = canonical_json_bytes(
        {
            "check_id": check_id,
            "failures": result.failures,
            "known": result.known,
            "skips": result.skips,
            "target": result.target,
        }
    ) + b"\n"
    record_digest = sha256_bytes(record)
    record_path = f"generated/{record_digest}.json"
    result_evidence = [
        *evidence,
        EvidenceReference(
            path=record_path,
            sha256=record_digest,
            media_type="application/json",
            size_bytes=len(record),
        ),
    ]
    generated = {record_path: record}
    if result.failures:
        missing_only = all(item.lower().startswith("missing ") for item in result.failures)
        return _result(
            check_id,
            gate,
            domain,
            layer,
            Verdict.BLOCKED if missing_only else Verdict.FAIL,
            "REQUIRED_INPUT_MISSING" if missing_only else "VALIDATION_FAILED",
            "required inputs are missing" if missing_only else "validation found defects",
            findings=result.failures,
            evidence=result_evidence,
            generated_evidence=generated,
        )
    if result.skips:
        return _result(
            check_id,
            gate,
            domain,
            layer,
            Verdict.BLOCKED,
            "REQUIRED_CAPABILITY_UNAVAILABLE",
            "a required validation capability was unavailable",
            execution_status=ExecutionStatus.UNAVAILABLE,
            findings=result.skips,
            evidence=result_evidence,
            generated_evidence=generated,
        )
    return _result(
        check_id,
        gate,
        domain,
        layer,
        Verdict.PASS,
        "CHECK_PASSED",
        "check completed with passing evidence",
        evidence=result_evidence,
        generated_evidence=generated,
    )


def _v0_checks(product: Path) -> List[CheckResult]:
    checks = []
    required_files = ("product_datasheet.md", "bom.csv")
    required_dirs = ("hardware/cad", "hardware/pcb", "simulation")
    missing = [name for name in required_files if not (product / name).is_file()]
    missing.extend(f"{name}/" for name in required_dirs if not (product / name).is_dir())
    checks.append(
        _result(
            "v0.required-artifacts",
            GateLevel.V0,
            Domain.DATA_MANAGEMENT,
            Layer.DESIGN,
            Verdict.BLOCKED if missing else Verdict.PASS,
            "REQUIRED_INPUT_MISSING" if missing else "CHECK_PASSED",
            "required product artifacts are missing" if missing else "required product artifacts exist",
            execution_status=ExecutionStatus.UNAVAILABLE if missing else ExecutionStatus.COMPLETED,
            findings=[f"missing {name}" for name in missing],
            evidence=(
                [
                    reference
                    for name in required_files
                    for reference in _evidence(product / name, product, "application/octet-stream")
                ]
                if not missing
                else []
            ),
        )
    )

    bom = product / "bom.csv"
    if bom.is_file():
        checks.append(
            _legacy_result(
                check_id="v0.canonical-bom",
                gate=GateLevel.V0,
                domain=Domain.DATA_MANAGEMENT,
                layer=Layer.DESIGN,
                result=legacy.validate_bom(str(bom)),
                evidence=_evidence(bom, product, "text/csv"),
            )
        )
    else:
        checks.append(
            _result(
                "v0.canonical-bom",
                GateLevel.V0,
                Domain.DATA_MANAGEMENT,
                Layer.DESIGN,
                Verdict.BLOCKED,
                "BOM_MISSING",
                "canonical BOM is missing",
                execution_status=ExecutionStatus.UNAVAILABLE,
            )
        )

    datasheet = product / "product_datasheet.md"
    if datasheet.is_file():
        checks.append(
            _legacy_result(
                check_id="v0.datasheet-contract",
                gate=GateLevel.V0,
                domain=Domain.SYSTEM_DESIGN,
                layer=Layer.DESIGN,
                result=legacy.validate_datasheet(str(datasheet)),
                evidence=_evidence(datasheet, product, "text/markdown"),
            )
        )
    else:
        checks.append(
            _result(
                "v0.datasheet-contract",
                GateLevel.V0,
                Domain.SYSTEM_DESIGN,
                Layer.DESIGN,
                Verdict.BLOCKED,
                "DATASHEET_MISSING",
                "product datasheet is missing",
                execution_status=ExecutionStatus.UNAVAILABLE,
            )
        )
    return checks


def _v1_checks(product: Path) -> List[CheckResult]:
    scripts = sorted(product.glob("simulation/*.py"))
    if not scripts:
        return [
            _result(
                "v1.simulation-execution",
                GateLevel.V1,
                Domain.SYSTEM_DESIGN,
                Layer.SIMULATION,
                Verdict.BLOCKED,
                "SIMULATION_MODEL_MISSING",
                "no executable Python simulation model exists",
                execution_status=ExecutionStatus.UNAVAILABLE,
            )
        ]

    checks = []
    for script in scripts:
        result = legacy.validate_simulation(str(script), run=True)
        check_id = f"v1.simulation.{script.stem}"
        if any("timeout" in finding.lower() for finding in result.failures):
            checks.append(
                _result(
                    check_id,
                    GateLevel.V1,
                    Domain.SYSTEM_DESIGN,
                    Layer.SIMULATION,
                    Verdict.INCONCLUSIVE,
                    "SIMULATION_TIMED_OUT",
                    "simulation exceeded its execution timeout",
                    execution_status=ExecutionStatus.TIMED_OUT,
                    findings=result.failures,
                    evidence=_evidence(script, product, "text/x-python"),
                )
            )
        else:
            checks.append(
                _legacy_result(
                    check_id=check_id,
                    gate=GateLevel.V1,
                    domain=Domain.SYSTEM_DESIGN,
                    layer=Layer.SIMULATION,
                    result=result,
                    evidence=_evidence(script, product, "text/x-python"),
                )
            )
    return checks


def _v2_checks(product: Path, *, render: bool) -> List[CheckResult]:
    result = legacy.validate_cad(str(product), product.name, render=render)
    evidence_paths = []
    for pattern in (
        "hardware/pcb/*.kicad_pcb",
        "hardware/pcb/*.net",
        "hardware/cad/*.dxf",
        "hardware/cad/*.scad",
    ):
        evidence_paths.extend(Path(path) for path in glob.glob(str(product / pattern)))
    evidence = []
    for path in sorted(evidence_paths):
        evidence.extend(_evidence(path, product, "application/octet-stream"))
    return [
        _legacy_result(
            check_id="v2.cad-invariants",
            gate=GateLevel.V2,
            domain=Domain.PHYSICAL_DESIGN,
            layer=Layer.VALIDATION,
            result=result,
            evidence=evidence,
        )
    ]


def validate_product(
    root: Path,
    entry: InventoryEntry,
    *,
    source_commit: str,
    source_dirty: bool,
    render: bool = False,
) -> ProductRunResult:
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    product = root / entry.path
    files = [path for path in product.rglob("*") if path.is_file()]
    input_sha256 = hash_tree(product, files)
    gate_checks = {
        GateLevel.V0: _v0_checks(product),
        GateLevel.V1: _v1_checks(product),
        GateLevel.V2: _v2_checks(product, render=render),
        GateLevel.V3: execute_cases(product, GateLevel.V3, "golden"),
        GateLevel.V4: execute_cases(product, GateLevel.V4, "corners"),
    }
    final_files = [path for path in product.rglob("*") if path.is_file()]
    final_input_sha256 = hash_tree(product, final_files)
    mutation_record = canonical_json_bytes(
        {
            "after_input_sha256": final_input_sha256,
            "before_input_sha256": input_sha256,
            "product_id": entry.product_id,
        }
    ) + b"\n"
    mutation_digest = sha256_bytes(mutation_record)
    mutation_evidence_path = f"generated/{mutation_digest}.json"
    mutated = final_input_sha256 != input_sha256
    gate_checks[GateLevel.V0].append(
        CheckResult(
            check_id="v0.validation-input-immutability",
            gate=GateLevel.V0,
            domain=Domain.DATA_MANAGEMENT,
            layer=Layer.VALIDATION,
            execution_status=ExecutionStatus.COMPLETED,
            verdict=Verdict.FAIL if mutated else Verdict.PASS,
            reason_code=(
                "SOURCE_MUTATED_DURING_VALIDATION"
                if mutated
                else "VALIDATION_INPUT_UNCHANGED"
            ),
            summary=(
                "product inputs changed while validation was running"
                if mutated
                else "product input digest remained stable during validation"
            ),
            evidence=[
                EvidenceReference(
                    path=mutation_evidence_path,
                    sha256=mutation_digest,
                    media_type="application/json",
                    size_bytes=len(mutation_record),
                )
            ],
            generated_evidence={mutation_evidence_path: mutation_record},
        )
    )
    input_sha256 = final_input_sha256
    source_record = canonical_json_bytes(
        {"commit": source_commit, "dirty": source_dirty, "product_id": entry.product_id}
    ) + b"\n"
    source_digest = sha256_bytes(source_record)
    source_evidence_path = f"generated/{source_digest}.json"
    gate_checks[GateLevel.V0].append(
        CheckResult(
            check_id="v0.pinned-clean-source",
            gate=GateLevel.V0,
            domain=Domain.DATA_MANAGEMENT,
            layer=Layer.VALIDATION,
            execution_status=ExecutionStatus.COMPLETED,
            verdict=Verdict.BLOCKED if source_dirty else Verdict.PASS,
            reason_code="SOURCE_TREE_DIRTY" if source_dirty else "SOURCE_REVISION_PINNED",
            summary=(
                "source tree contains changes not represented by the pinned commit"
                if source_dirty
                else "source tree is clean and bound to the recorded commit"
            ),
            evidence=[
                EvidenceReference(
                    path=source_evidence_path,
                    sha256=source_digest,
                    media_type="application/json",
                    size_bytes=len(source_record),
                )
            ],
            generated_evidence={source_evidence_path: source_record},
        )
    )
    gates = [GateResult.from_checks(level, gate_checks[level]) for level in GateLevel]
    completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    tools = {
        "ecad-validator": {
            "tool_id": "ecad-validator",
            "name": "eCAD hardware validator",
            "version": "1.0.0",
            "invocation": ["python3", "tools/validate_products.py", "validate"],
            "settings": {"render": render},
        }
    }
    for gate in gates:
        for check in gate.checks:
            if check.tool_id != "ecad-validator" and check.tool_version:
                tools[check.tool_id] = {
                    "tool_id": check.tool_id,
                    "name": check.tool_id,
                    "version": check.tool_version,
                    "invocation": check.tool_invocation or [check.tool_id],
                    "settings": check.tool_settings,
                }
    return ProductRunResult(
        product_id=entry.product_id,
        product_path=entry.path,
        source_commit=source_commit,
        source_dirty=source_dirty,
        input_sha256=input_sha256,
        started_at=started_at,
        completed_at=completed_at,
        gates=gates,
        tools=[tools[name] for name in sorted(tools)],
    )


def validate_repository(
    root: Path,
    entries: Iterable[InventoryEntry],
    *,
    inventory_sha256: str,
    inventory_product_ids: Iterable[str],
    render: bool = False,
) -> RepositoryRunResult:
    source_commit, source_dirty = repository_state(root)
    products = [
        validate_product(
            root,
            entry,
            source_commit=source_commit,
            source_dirty=source_dirty,
            render=render,
        )
        for entry in entries
    ]
    return RepositoryRunResult(
        source_commit=source_commit,
        products=products,
        inventory_sha256=inventory_sha256,
        inventory_product_ids=sorted(inventory_product_ids),
    )
