"""Execute reviewed V3 golden and V4 corner case declarations."""

from __future__ import annotations

import json
import os
import math
from pathlib import Path
from typing import Dict, List, Mapping, Type

from .adapters.base import Adapter, AdapterRequest
from .adapters.hdl import HDLAdapter
from .adapters.kicad import KiCadAdapter
from .adapters.mujoco import MujocoAdapter
from .adapters.ngspice import NgspiceAdapter
from .adapters.python_control import PythonControlAdapter
from .contract import validate_document
from .hashing import canonical_json_bytes, sha256_bytes, sha256_file
from .models import (
    CheckResult,
    Domain,
    EvidenceReference,
    ExecutionStatus,
    GateLevel,
    Layer,
    Verdict,
)

ADAPTERS: Dict[str, Type[Adapter]] = {
    "python_control": PythonControlAdapter,
    "mujoco": MujocoAdapter,
    "kicad": KiCadAdapter,
    "ngspice": NgspiceAdapter,
    "iverilog": HDLAdapter,
}


def _blocked(gate: GateLevel, check_id: str, reason: str, summary: str) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        gate=gate,
        domain=Domain.SYSTEM_DESIGN if gate is GateLevel.V3 else Domain.INTEGRATED_PHYSICS,
        layer=Layer.VALIDATION,
        execution_status=ExecutionStatus.UNAVAILABLE,
        verdict=Verdict.BLOCKED,
        reason_code=reason,
        summary=summary,
    )


def _references(product: Path, paths: List[Path]) -> List[EvidenceReference]:
    return [
        EvidenceReference(
            path=path.relative_to(product).as_posix(),
            sha256=sha256_file(path),
            size_bytes=path.stat().st_size,
        )
        for path in paths
        if path.is_file()
    ]


def _numeric(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _compare_golden(metrics: Mapping[str, object], expected: object) -> tuple[Verdict, List[str]]:
    if not isinstance(expected, dict) or not expected:
        return Verdict.BLOCKED, ["golden case has no expected_metrics"]
    findings = []
    for name, specification in expected.items():
        if not isinstance(specification, dict) or not _numeric(specification.get("value")):
            findings.append(f"{name}: expected value is missing or non-finite")
            continue
        tolerance = specification.get("absolute_tolerance")
        if not _numeric(tolerance) or float(tolerance) < 0:
            findings.append(f"{name}: absolute_tolerance is missing, negative, or non-finite")
            continue
        actual = metrics.get(name)
        if not _numeric(actual):
            findings.append(f"{name}: adapter produced no finite numeric metric")
            continue
        delta = abs(float(actual) - float(specification["value"]))
        if delta > float(tolerance):
            findings.append(
                f"{name}: actual {actual} differs from expected {specification['value']} "
                f"by {delta}, exceeding tolerance {tolerance}"
            )
    if not findings:
        return Verdict.PASS, []
    if any("differs" in finding for finding in findings):
        return Verdict.FAIL, findings
    return Verdict.INCONCLUSIVE, findings


def _compare_corner(metrics: Mapping[str, object], limits: object) -> tuple[Verdict, List[str]]:
    if not isinstance(limits, dict) or not limits:
        return Verdict.BLOCKED, ["corner case has no metric_limits"]
    findings = []
    for name, specification in limits.items():
        if not isinstance(specification, dict):
            findings.append(f"{name}: limit must be an object")
            continue
        actual = metrics.get(name)
        if not _numeric(actual):
            findings.append(f"{name}: adapter produced no finite numeric metric")
            continue
        minimum = specification.get("minimum")
        maximum = specification.get("maximum")
        if minimum is None and maximum is None:
            findings.append(f"{name}: minimum or maximum is required")
            continue
        if minimum is not None and (not _numeric(minimum) or float(actual) < float(minimum)):
            findings.append(f"{name}: actual {actual} is below minimum {minimum}")
        if maximum is not None and (not _numeric(maximum) or float(actual) > float(maximum)):
            findings.append(f"{name}: actual {actual} is above maximum {maximum}")
    if not findings:
        return Verdict.PASS, []
    if any("actual" in finding and ("below" in finding or "above" in finding) for finding in findings):
        return Verdict.FAIL, findings
    return Verdict.INCONCLUSIVE, findings


def execute_cases(product: Path, gate: GateLevel, directory: str) -> List[CheckResult]:
    manifest = product / "validation" / directory / "cases.json"
    if not manifest.is_file():
        return [
            _blocked(
                gate,
                f"{gate.value.lower()}.{directory}-cases",
                f"{directory.upper()}_EVIDENCE_MISSING",
                f"reviewed {directory} cases and evidence are missing",
            )
        ]
    try:
        document = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            CheckResult(
                check_id=f"{gate.value.lower()}.{directory}-manifest",
                gate=gate,
                domain=Domain.SYSTEM_DESIGN if gate is GateLevel.V3 else Domain.INTEGRATED_PHYSICS,
                layer=Layer.VALIDATION,
                execution_status=ExecutionStatus.COMPLETED,
                verdict=Verdict.FAIL,
                reason_code="CASE_MANIFEST_INVALID",
                summary="case manifest cannot be parsed",
                findings=[str(exc)],
            )
        ]
    try:
        validate_document(
            Path(__file__).resolve().parents[2],
            "validation-cases.schema.json",
            document,
        )
    except ValueError as exc:
        return [
            CheckResult(
                check_id=f"{gate.value.lower()}.{directory}-manifest",
                gate=gate,
                domain=Domain.DATA_MANAGEMENT,
                layer=Layer.VALIDATION,
                execution_status=ExecutionStatus.COMPLETED,
                verdict=Verdict.FAIL,
                reason_code="CASE_SCHEMA_INVALID",
                summary="case manifest does not conform to the v1 schema",
                evidence=_references(product, [manifest]),
                findings=[str(exc)],
            )
        ]
    if document.get("gate") != gate.value:
        return [
            CheckResult(
                check_id=f"{gate.value.lower()}.{directory}-manifest",
                gate=gate,
                domain=Domain.DATA_MANAGEMENT,
                layer=Layer.VALIDATION,
                execution_status=ExecutionStatus.COMPLETED,
                verdict=Verdict.FAIL,
                reason_code="CASE_GATE_MISMATCH",
                summary="case manifest gate does not match its validation directory",
                evidence=_references(product, [manifest]),
            )
        ]
    cases = document.get("cases") if isinstance(document, dict) else None
    if not isinstance(cases, list) or not cases:
        return [
            _blocked(
                gate,
                f"{gate.value.lower()}.{directory}-manifest",
                "CASE_MANIFEST_EMPTY",
                "case manifest contains no executable cases",
            )
        ]
    case_ids = [case.get("id") for case in cases]
    if len(case_ids) != len(set(case_ids)):
        return [
            CheckResult(
                check_id=f"{gate.value.lower()}.{directory}-manifest",
                gate=gate,
                domain=Domain.DATA_MANAGEMENT,
                layer=Layer.VALIDATION,
                execution_status=ExecutionStatus.COMPLETED,
                verdict=Verdict.FAIL,
                reason_code="DUPLICATE_CASE_ID",
                summary="case manifest contains duplicate case identifiers",
                evidence=_references(product, [manifest]),
            )
        ]

    results = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            results.append(
                CheckResult(
                    check_id=f"{gate.value.lower()}.{directory}.{index}",
                    gate=gate,
                    domain=Domain.SYSTEM_DESIGN if gate is GateLevel.V3 else Domain.INTEGRATED_PHYSICS,
                    layer=Layer.VALIDATION,
                    execution_status=ExecutionStatus.COMPLETED,
                    verdict=Verdict.FAIL,
                    reason_code="CASE_INVALID",
                    summary="case declaration is not an object",
                )
            )
            continue
        case_id = str(case.get("id") or index)
        domain_name = str(
            case.get(
                "domain",
                "system_design" if gate is GateLevel.V3 else "integrated_physics",
            )
        )
        try:
            domain = Domain(domain_name)
        except ValueError:
            results.append(
                CheckResult(
                    check_id=f"{gate.value.lower()}.{case_id}",
                    gate=gate,
                    domain=Domain.DATA_MANAGEMENT,
                    layer=Layer.VALIDATION,
                    execution_status=ExecutionStatus.COMPLETED,
                    verdict=Verdict.FAIL,
                    reason_code="CASE_DOMAIN_INVALID",
                    summary=f"case declares unsupported domain {domain_name!r}",
                    evidence=_references(product, [manifest]),
                )
            )
            continue
        adapter_name = str(case.get("adapter") or "")
        adapter_type = ADAPTERS.get(adapter_name)
        if adapter_type is None:
            results.append(
                _blocked(
                    gate,
                    f"{gate.value.lower()}.{case_id}",
                    "ADAPTER_UNSUPPORTED",
                    f"adapter {adapter_name!r} is not implemented",
                )
            )
            continue
        input_values = case.get("inputs")
        if not isinstance(input_values, list) or not input_values:
            results.append(
                _blocked(
                    gate,
                    f"{gate.value.lower()}.{case_id}",
                    "CASE_INPUTS_MISSING",
                    "case declares no input artifacts",
                )
            )
            continue
        input_files = []
        invalid_path = None
        for value in input_values:
            relative = Path(str(value))
            declared = product / relative
            candidate = declared.resolve()
            ancestor = candidate
            for _part in relative.parts:
                ancestor = ancestor.parent
            try:
                contained = os.path.samefile(ancestor, product.resolve())
            except OSError:
                contained = False
            if not contained:
                invalid_path = str(value)
                break
            if declared.is_symlink() or not candidate.is_file():
                invalid_path = str(value)
                break
            input_files.append(declared)
        if invalid_path is not None:
            results.append(
                _blocked(
                    gate,
                    f"{gate.value.lower()}.{case_id}",
                    "CASE_INPUT_MISSING_OR_UNSAFE",
                    f"case input is missing or escapes the product root: {invalid_path}",
                )
            )
            continue
        try:
            timeout_seconds = int(case.get("timeout_seconds", 180))
            seed = int(case["seed"]) if case.get("seed") is not None else None
            if timeout_seconds <= 0 or timeout_seconds > 3600:
                raise ValueError("timeout_seconds must be between 1 and 3600")
        except (TypeError, ValueError) as exc:
            results.append(
                CheckResult(
                    check_id=f"{gate.value.lower()}.{case_id}",
                    gate=gate,
                    domain=Domain.DATA_MANAGEMENT,
                    layer=Layer.VALIDATION,
                    execution_status=ExecutionStatus.COMPLETED,
                    verdict=Verdict.FAIL,
                    reason_code="CASE_CONFIGURATION_INVALID",
                    summary="case execution settings are invalid",
                    evidence=_references(product, [manifest, *input_files]),
                    findings=[str(exc)],
                )
            )
            continue
        try:
            adapter_result = adapter_type().run(
                AdapterRequest(
                    case_id=case_id,
                    product_root=product,
                    input_files=input_files,
                    arguments=[str(value) for value in case.get("arguments", [])],
                    timeout_seconds=timeout_seconds,
                    seed=seed,
                    settings=(
                        case.get("settings", {})
                        if isinstance(case.get("settings", {}), dict)
                        else {}
                    ),
                )
            )
        except (OSError, ValueError) as exc:
            results.append(
                CheckResult(
                    check_id=f"{gate.value.lower()}.{case_id}",
                    gate=gate,
                    domain=Domain.DATA_MANAGEMENT,
                    layer=Layer.VALIDATION,
                    execution_status=ExecutionStatus.CRASHED,
                    verdict=Verdict.FAIL,
                    reason_code="ADAPTER_EXECUTION_ERROR",
                    summary="adapter rejected the case or failed before producing a result",
                    evidence=_references(product, [manifest, *input_files]),
                    findings=[str(exc)],
                )
            )
            continue
        execution_record = {
            "adapter": adapter_result.adapter,
            "case_id": case_id,
            "command": adapter_result.command,
            "execution_status": adapter_result.execution_status.value,
            "metrics": adapter_result.metrics,
            "reason_code": adapter_result.reason_code,
            "return_summary": adapter_result.summary,
            "stderr": adapter_result.stderr,
            "stdout": adapter_result.stdout,
            "tool_version": adapter_result.tool_version,
        }
        execution_bytes = canonical_json_bytes(execution_record) + b"\n"
        execution_digest = sha256_bytes(execution_bytes)
        execution_relative = f"generated/{execution_digest}.json"
        execution_reference = EvidenceReference(
            path=execution_relative,
            sha256=execution_digest,
            media_type="application/json",
            size_bytes=len(execution_bytes),
        )
        verdict = adapter_result.verdict
        reason_code = adapter_result.reason_code
        findings = []
        if verdict is Verdict.PASS:
            if gate is GateLevel.V3:
                verdict, findings = _compare_golden(adapter_result.metrics, case.get("expected_metrics"))
                reason_code = {
                    Verdict.PASS: "GOLDEN_COMPARISON_PASSED",
                    Verdict.FAIL: "GOLDEN_COMPARISON_FAILED",
                    Verdict.BLOCKED: "GOLDEN_EXPECTATION_MISSING",
                    Verdict.INCONCLUSIVE: "GOLDEN_METRICS_INCONCLUSIVE",
                }[verdict]
            else:
                verdict, findings = _compare_corner(adapter_result.metrics, case.get("metric_limits"))
                reason_code = {
                    Verdict.PASS: "CORNER_LIMITS_PASSED",
                    Verdict.FAIL: "CORNER_LIMITS_FAILED",
                    Verdict.BLOCKED: "CORNER_LIMITS_MISSING",
                    Verdict.INCONCLUSIVE: "CORNER_METRICS_INCONCLUSIVE",
                }[verdict]
        evidence = [
            EvidenceReference(
                path=path.relative_to(product).as_posix(),
                sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
            )
            for path in [manifest, *input_files]
        ]
        results.append(
            CheckResult(
                check_id=f"{gate.value.lower()}.{case_id}",
                gate=gate,
                domain=domain,
                layer=Layer.VALIDATION,
                execution_status=adapter_result.execution_status,
                verdict=verdict,
                reason_code=reason_code,
                summary=adapter_result.summary,
                tool_id=adapter_result.adapter,
                tool_version=adapter_result.tool_version or "",
                tool_invocation=adapter_result.command,
                tool_settings={
                    "seed": seed,
                    "timeout_seconds": timeout_seconds,
                    **(case.get("settings", {}) if isinstance(case.get("settings", {}), dict) else {}),
                },
                requirement_ids=[str(value) for value in case.get("requirement_ids", [])],
                metrics=adapter_result.metrics,
                findings=[*findings, *([adapter_result.stderr] if adapter_result.stderr else [])],
                evidence=[*evidence, execution_reference],
                generated_evidence={execution_relative: execution_bytes},
            )
        )
    return results
