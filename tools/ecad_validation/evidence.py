"""Write and verify portable, content-addressed validation bundles."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict

from .contract import (
    artifact_reference,
    build_product_contract,
    build_product_manifest,
    validate_document,
)
from .hashing import canonical_json_bytes, sha256_bytes, sha256_file
from .models import RepositoryRunResult
from .reports import junit_xml, product_html, product_markdown, repository_markdown


def _write_json(path: Path, value: Any) -> str:
    payload = canonical_json_bytes(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sha256_bytes(payload)


def write_bundle(root: Path, output: Path, result: RepositoryRunResult) -> Path:
    """Write schema-valid product bundles and a repository-level index."""
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"validation output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    receipt_entries = []
    evidence_entries: Dict[str, Dict[str, Any]] = {}
    requirements_source = (
        root / "contracts" / "hardware-validation" / "v1" / "policy-requirements.json"
    )
    requirements_document = json.loads(requirements_source.read_text(encoding="utf-8"))
    validate_document(root, "requirements.schema.json", requirements_document)
    inventory_source = root / "tools" / "catalog" / "product_inventory.json"
    inventory_document = json.loads(inventory_source.read_text(encoding="utf-8"))
    if sha256_bytes(canonical_json_bytes(inventory_document)) != result.inventory_sha256:
        raise ValueError("inventory digest changed during validation")
    inventory_path = output / "product-inventory.json"
    inventory_file_digest = _write_json(inventory_path, inventory_document)

    for product in result.products:
        product_dir = output / "products" / product.product_id.replace(":", "__")
        product_dir.mkdir(parents=True, exist_ok=True)
        product_evidence_root = product_dir / "evidence" / "sha256"
        product_evidence_root.mkdir(parents=True, exist_ok=True)
        product_root = root / product.product_path
        input_files = [path for path in product_root.rglob("*") if path.is_file()]

        requirements_path = product_dir / "requirements.json"
        requirements_digest = _write_json(requirements_path, requirements_document)
        requirements_reference = artifact_reference(
            requirements_path.relative_to(product_dir).as_posix(),
            requirements_digest,
            requirements_path.stat().st_size,
            "application/json",
        )

        manifest = build_product_manifest(root, product, input_files)
        validate_document(root, "product-manifest.schema.json", manifest)
        manifest_path = product_dir / "product-manifest.json"
        manifest_digest = _write_json(manifest_path, manifest)

        contract = build_product_contract(product, requirements_reference)
        validate_document(root, "product-contract.schema.json", contract)
        contract_path = product_dir / "product-contract.json"
        contract_digest = _write_json(contract_path, contract)

        receipt = product.to_receipt()
        product_evidence = []
        for gate_index, gate in enumerate(product.gates):
            for check_index, check in enumerate(gate.checks):
                receipt_check = receipt["gates"][gate_index]["checks"][check_index]
                for reference_index, reference in enumerate(check.evidence):
                    source = product_root / reference.path
                    generated = check.generated_evidence.get(reference.path)
                    target = product_evidence_root / reference.sha256
                    if generated is not None:
                        if sha256_bytes(generated) != reference.sha256:
                            raise ValueError(
                                f"generated evidence digest changed during validation: {reference.path}"
                            )
                        if not target.exists():
                            target.write_bytes(generated)
                        provenance = {
                            "source_type": "generated",
                            "generator_tool_id": check.tool_id,
                            "recorded_at": product.completed_at,
                        }
                    else:
                        if not source.is_file():
                            raise ValueError(f"referenced evidence is missing: {source}")
                        if sha256_file(source) != reference.sha256:
                            raise ValueError(f"evidence changed during validation: {source}")
                        if not target.exists():
                            shutil.copyfile(source, target)
                        provenance = {
                            "source_type": "repository",
                            "source_path": (Path(product.product_path) / reference.path).as_posix(),
                            "source_commit": product.source_commit,
                            "recorded_at": product.completed_at,
                        }
                    bundled_path = target.relative_to(product_dir).as_posix()
                    repository_path = target.relative_to(output).as_posix()
                    receipt_check["evidence"][reference_index]["path"] = bundled_path
                    evidence_entry = {
                        "evidence_id": receipt_check["evidence"][reference_index]["evidence_id"],
                        "path": bundled_path,
                        "sha256": reference.sha256,
                        "media_type": reference.media_type,
                        "size_bytes": reference.size_bytes,
                        "check_id": check.check_id,
                        "requirement_ids": check.requirement_ids,
                        "producer_tool_id": check.tool_id,
                        "captured_at": product.completed_at,
                        "provenance": provenance,
                    }
                    product_evidence.append(evidence_entry)
                    evidence_entries[reference.sha256] = {
                        "sha256": reference.sha256,
                        "size_bytes": reference.size_bytes,
                        "media_type": reference.media_type,
                        "path": repository_path,
                    }

        validate_document(root, "validation-receipt.schema.json", receipt)
        receipt_path = product_dir / "receipt.json"
        receipt_digest = _write_json(receipt_path, receipt)

        evidence_index = {
            "$schema": "https://embeddedos.org/schemas/hardware-validation/v1/evidence-index.schema.json",
            "contract_version": result.contract_version,
            "product_id": product.product_id,
            "receipt_sha256": receipt_digest,
            "generated_at": product.completed_at,
            "evidence": product_evidence,
        }
        validate_document(root, "evidence-index.schema.json", evidence_index)
        product_evidence_path = product_dir / "evidence-index.json"
        product_evidence_digest = _write_json(product_evidence_path, evidence_index)

        document_paths = {
            "product_contract": (contract_path, contract_digest),
            "requirements": (requirements_path, requirements_digest),
            "product_manifest": (manifest_path, manifest_digest),
            "validation_receipt": (receipt_path, receipt_digest),
            "evidence_index": (product_evidence_path, product_evidence_digest),
        }
        product_bundle = {
            "$schema": "https://embeddedos.org/schemas/hardware-validation/v1/bundle.schema.json",
            "contract_version": result.contract_version,
            "bundle_id": f"bundle:{product.product_id}:{product.input_sha256[:16]}",
            "product_id": product.product_id,
            "created_at": product.completed_at,
            "created_by": product.tools[0],
            "documents": {
                name: artifact_reference(
                    path.relative_to(product_dir).as_posix(),
                    digest,
                    path.stat().st_size,
                    "application/json",
                )
                for name, (path, digest) in document_paths.items()
            },
        }
        validate_document(root, "bundle.schema.json", product_bundle)
        product_bundle_path = product_dir / "bundle.json"
        product_bundle_digest = _write_json(product_bundle_path, product_bundle)
        (product_dir / "report.md").write_text(product_markdown(product), encoding="utf-8")
        (product_dir / "report.html").write_text(product_html(product), encoding="utf-8")
        receipt_entries.append(
            {
                "product_id": product.product_id,
                "path": receipt_path.relative_to(output).as_posix(),
                "sha256": receipt_digest,
                "bundle": artifact_reference(
                    product_bundle_path.relative_to(output).as_posix(),
                    product_bundle_digest,
                    product_bundle_path.stat().st_size,
                    "application/json",
                ),
                "verdict": product.overall_verdict.value,
                "execution_complete": product.execution_complete,
                "eligible_for_ebuild": product.eligible_for_ebuild,
            }
        )

    summary = result.to_summary()
    summary_path = output / "summary.json"
    summary_digest = _write_json(summary_path, summary)
    (output / "summary.md").write_text(repository_markdown(result), encoding="utf-8")
    (output / "junit.xml").write_bytes(junit_xml(result))
    repository_evidence_path = output / "evidence-index.json"
    repository_evidence_digest = _write_json(
        repository_evidence_path,
        {"artifacts": [evidence_entries[key] for key in sorted(evidence_entries)]},
    )
    bundle = {
        "$schema": "https://embeddedos.org/schemas/hardware-validation/v1/repository-bundle.schema.json",
        "contract_version": result.contract_version,
        "source_commit": result.source_commit,
        "inventory_sha256": result.inventory_sha256,
        "inventory": artifact_reference(
            inventory_path.relative_to(output).as_posix(),
            inventory_file_digest,
            inventory_path.stat().st_size,
            "application/json",
        ),
        "all_products_executed": result.all_products_executed,
        "receipts": receipt_entries,
        "summary": artifact_reference(
            summary_path.relative_to(output).as_posix(),
            summary_digest,
            summary_path.stat().st_size,
            "application/json",
        ),
        "evidence_index": artifact_reference(
            repository_evidence_path.relative_to(output).as_posix(),
            repository_evidence_digest,
            repository_evidence_path.stat().st_size,
            "application/json",
        ),
    }
    validate_document(root, "repository-bundle.schema.json", bundle)
    _write_json(output / "bundle.json", bundle)
    return output / "bundle.json"


def _aggregate_verdict(values: list[str]) -> str:
    if "FAIL" in values:
        return "FAIL"
    if "BLOCKED" in values or "WARNING" in values:
        return "BLOCKED"
    if "INCONCLUSIVE" in values:
        return "INCONCLUSIVE"
    if "NOT_RUN" in values:
        return "NOT_RUN"
    return "PASS" if values and all(value == "PASS" for value in values) else "BLOCKED"


def _manifest_input_digest(manifest: Dict[str, Any]) -> str:
    product_path = Path(manifest.get("product", {}).get("path", ""))
    entries = []
    for artifact in manifest.get("artifacts", []):
        artifact_path = Path(artifact.get("path", ""))
        try:
            relative = artifact_path.relative_to(product_path).as_posix()
        except ValueError as exc:
            raise ValueError(f"manifest artifact escapes product path: {artifact_path}") from exc
        entries.append({"path": relative, "sha256": artifact.get("sha256")})
    if not entries or len({entry["path"] for entry in entries}) != len(entries):
        raise ValueError("manifest must contain unique product-relative artifact paths")
    return sha256_bytes(canonical_json_bytes(sorted(entries, key=lambda item: item["path"])))


def _bundle_path(root: Path, relative: object, label: str) -> Path:
    candidate = (root / str(relative or "")).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} path escapes bundle: {candidate}") from exc
    return candidate


def verify_bundle(bundle_path: Path) -> Dict[str, Any]:
    """Verify evidence and recompute every receipt decision from child checks."""
    root = bundle_path.parent.resolve()
    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read validation bundle: {exc}") from exc

    for reference_name in ("inventory", "summary", "evidence_index"):
        reference = bundle.get(reference_name)
        if not isinstance(reference, dict):
            raise ValueError(f"repository bundle lacks {reference_name} reference")
        referenced_path = _bundle_path(root, reference.get("path"), reference_name)
        if not referenced_path.is_file() or sha256_file(referenced_path) != reference.get("sha256"):
            raise ValueError(f"{reference_name} digest mismatch: {referenced_path}")
        if referenced_path.stat().st_size != reference.get("size_bytes"):
            raise ValueError(f"{reference_name} size mismatch: {referenced_path}")
    inventory_path = _bundle_path(root, bundle["inventory"].get("path"), "inventory")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if sha256_bytes(canonical_json_bytes(inventory)) != bundle.get("inventory_sha256"):
        raise ValueError("inventory semantic digest mismatch")
    inventory_entries = inventory.get("products", [])
    inventory_paths = {
        entry.get("product_id"): entry.get("path")
        for entry in inventory_entries
        if isinstance(entry, dict)
        and isinstance(entry.get("product_id"), str)
        and isinstance(entry.get("path"), str)
    }
    if (
        len(inventory_paths) != len(inventory_entries)
        or len(set(inventory_paths.values())) != len(inventory_entries)
    ):
        raise ValueError("inventory has duplicate or missing product IDs or paths")
    inventory_ids = set(inventory_paths)
    summary_path = _bundle_path(root, bundle["summary"].get("path"), "summary")
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read validation summary: {exc}") from exc
    if not isinstance(summary, dict):
        raise ValueError("validation summary must be a JSON object")

    index_path = _bundle_path(root, bundle["evidence_index"].get("path"), "evidence index")
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read evidence index: {exc}") from exc
    indexed_evidence = {}
    for artifact in index.get("artifacts", []):
        digest = artifact.get("sha256")
        candidate = _bundle_path(root, artifact.get("path"), "evidence")
        if not digest or digest in indexed_evidence:
            raise ValueError(f"duplicate or missing evidence digest: {digest!r}")
        if not candidate.is_file() or sha256_file(candidate) != digest:
            raise ValueError(f"evidence digest mismatch: {candidate}")
        if candidate.stat().st_size != artifact.get("size_bytes"):
            raise ValueError(f"evidence size mismatch: {candidate}")
        indexed_evidence[digest] = artifact

    validator_root = Path(__file__).resolve().parents[2]
    validate_document(validator_root, "repository-bundle.schema.json", bundle)

    receipts = bundle.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        raise ValueError("validation bundle has no receipts")
    seen = set()
    verdict_counts = {
        "PASS": 0,
        "FAIL": 0,
        "WARNING": 0,
        "NOT_RUN": 0,
        "BLOCKED": 0,
        "INCONCLUSIVE": 0,
    }
    eligible_products = []
    for entry in receipts:
        product_id = entry.get("product_id")
        if not product_id or product_id in seen:
            raise ValueError(f"duplicate or missing product receipt ID: {product_id!r}")
        if product_id not in inventory_ids:
            raise ValueError(f"receipt product is absent from inventory: {product_id}")
        seen.add(product_id)
        candidate = _bundle_path(root, entry.get("path"), "receipt")
        if not candidate.is_file():
            raise ValueError(f"receipt is missing: {candidate}")
        if sha256_file(candidate) != entry.get("sha256"):
            raise ValueError(f"receipt digest mismatch: {candidate}")
        product_bundle_reference = entry.get("bundle")
        if not isinstance(product_bundle_reference, dict):
            raise ValueError(f"product bundle reference is missing: {product_id}")
        product_bundle_path = _bundle_path(
            root, product_bundle_reference.get("path"), "product bundle"
        )
        if not product_bundle_path.is_file():
            raise ValueError(f"product bundle is missing: {product_bundle_path}")
        if sha256_file(product_bundle_path) != product_bundle_reference.get("sha256"):
            raise ValueError(f"product bundle digest mismatch: {product_bundle_path}")
        if product_bundle_path.stat().st_size != product_bundle_reference.get("size_bytes"):
            raise ValueError(f"product bundle size mismatch: {product_bundle_path}")
        product_bundle = json.loads(product_bundle_path.read_text(encoding="utf-8"))
        validate_document(validator_root, "bundle.schema.json", product_bundle)
        if product_bundle.get("product_id") != product_id:
            raise ValueError(f"product bundle identity mismatch: {product_id}")
        document_schemas = {
            "product_contract": "product-contract.schema.json",
            "requirements": "requirements.schema.json",
            "product_manifest": "product-manifest.schema.json",
            "validation_receipt": "validation-receipt.schema.json",
            "evidence_index": "evidence-index.schema.json",
        }
        document_values = {}
        for name, document in product_bundle.get("documents", {}).items():
            document_path = _bundle_path(
                product_bundle_path.parent,
                document.get("path"),
                f"{name} document",
            )
            if not document_path.is_file() or sha256_file(document_path) != document.get("sha256"):
                raise ValueError(f"{name} document digest mismatch: {product_id}")
            if document_path.stat().st_size != document.get("size_bytes"):
                raise ValueError(f"{name} document size mismatch: {product_id}")
            document_value = json.loads(document_path.read_text(encoding="utf-8"))
            validate_document(validator_root, document_schemas[name], document_value)
            document_values[name] = document_value
        receipt = json.loads(candidate.read_text(encoding="utf-8"))
        if document_values.get("validation_receipt") != receipt:
            raise ValueError(f"receipt path disagrees with product bundle: {product_id}")
        contract = document_values["product_contract"]
        manifest = document_values["product_manifest"]
        requirements = document_values["requirements"]
        product_evidence = document_values["evidence_index"]
        if contract.get("product", {}).get("id") != product_id:
            raise ValueError(f"product contract identity mismatch: {product_id}")
        if manifest.get("product", {}).get("id") != product_id:
            raise ValueError(f"product manifest identity mismatch: {product_id}")
        if product_evidence.get("product_id") != product_id:
            raise ValueError(f"product evidence identity mismatch: {product_id}")
        expected_product_path = inventory_paths[product_id]
        product_paths = (
            receipt.get("product", {}).get("path"),
            contract.get("product", {}).get("path"),
            manifest.get("product", {}).get("path"),
            contract.get("provenance", {}).get("source_path"),
        )
        if any(path != expected_product_path for path in product_paths):
            raise ValueError(f"product path disagrees with inventory: {product_id}")
        if product_evidence.get("receipt_sha256") != entry.get("sha256"):
            raise ValueError(f"evidence index receipt digest mismatch: {product_id}")
        if manifest.get("source", {}).get("commit") != bundle.get("source_commit"):
            raise ValueError(f"product manifest source commit mismatch: {product_id}")
        if manifest.get("source", {}).get("input_sha256") != receipt.get("source", {}).get("input_sha256"):
            raise ValueError(f"product manifest input digest mismatch: {product_id}")
        if _manifest_input_digest(manifest) != receipt.get("source", {}).get("input_sha256"):
            raise ValueError(f"manifest artifacts do not match input digest: {product_id}")
        requirement_id_values = [
            value.get("requirement_id") for value in requirements.get("requirements", [])
        ]
        if len(requirement_id_values) != len(set(requirement_id_values)):
            raise ValueError(f"requirement IDs are not unique: {product_id}")
        requirement_ids = set(requirement_id_values)
        contract_requirements = contract.get("requirements", {})
        if contract_requirements.get("catalog") != product_bundle["documents"]["requirements"]:
            raise ValueError(f"product contract requirement catalog mismatch: {product_id}")
        declared_requirement_ids = set(contract_requirements.get("requirement_ids", []))
        if not declared_requirement_ids or not declared_requirement_ids.issubset(requirement_ids):
            raise ValueError(f"product contract references unknown requirements: {product_id}")
        receipt_tools = receipt.get("tools", [])
        tool_id_values = [tool.get("tool_id") for tool in receipt_tools]
        if len(tool_id_values) != len(set(tool_id_values)):
            raise ValueError(f"receipt tool IDs are not unique: {product_id}")
        tool_ids = set(tool_id_values)
        product_evidence_values = product_evidence.get("evidence", [])
        evidence_ids = [value.get("evidence_id") for value in product_evidence_values]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError(f"product evidence IDs are not unique: {product_id}")
        indexed_references = {
            (
                value.get("evidence_id"),
                value.get("sha256"),
                value.get("path"),
                value.get("check_id"),
            )
            for value in product_evidence_values
        }
        if receipt.get("product", {}).get("id") != product_id:
            raise ValueError(f"receipt product identity mismatch: {product_id}")
        if receipt.get("source", {}).get("commit") != bundle.get("source_commit"):
            raise ValueError(f"receipt source commit mismatch: {product_id}")
        if receipt.get("contract_version") != bundle.get("contract_version"):
            raise ValueError(f"receipt contract version mismatch: {product_id}")
        gates = receipt.get("gates", [])
        by_gate = {gate.get("gate"): gate for gate in gates if isinstance(gate, dict)}
        if set(by_gate) != {"V0", "V1", "V2", "V3", "V4"}:
            raise ValueError(f"receipt lacks exact V0-V4 gates: {product_id}")
        gate_verdicts = []
        for name in ("V0", "V1", "V2", "V3", "V4"):
            gate = by_gate[name]
            checks = gate.get("checks")
            if not isinstance(checks, list) or not checks:
                raise ValueError(f"gate {name} has no checks: {product_id}")
            required_values = [
                check.get("verdict")
                for check in checks
                if isinstance(check, dict) and check.get("required", True)
            ]
            calculated_gate = _aggregate_verdict(required_values)
            if gate.get("verdict") != calculated_gate:
                raise ValueError(f"gate {name} verdict disagrees with child checks: {product_id}")
            gate_verdicts.append(calculated_gate)
            for check in checks:
                if check.get("tool_id") not in tool_ids:
                    raise ValueError(f"check references unknown tool: {product_id} {check.get('check_id')}")
                if not set(check.get("requirement_ids", [])).issubset(requirement_ids):
                    raise ValueError(
                        f"check references unknown requirement: {product_id} {check.get('check_id')}"
                    )
                for reference in check.get("evidence", []):
                    evidence_path = _bundle_path(
                        product_bundle_path.parent,
                        reference.get("path"),
                        "receipt evidence",
                    )
                    if not evidence_path.is_file() or sha256_file(evidence_path) != reference.get("sha256"):
                        raise ValueError(
                            f"receipt evidence digest mismatch: {product_id} {check.get('check_id')}"
                        )
                    if evidence_path.stat().st_size != reference.get("size_bytes"):
                        raise ValueError(
                            f"receipt evidence size mismatch: {product_id} {check.get('check_id')}"
                        )
                    if reference.get("sha256") not in indexed_evidence:
                        raise ValueError(
                            f"check references evidence absent from index: {product_id} "
                            f"{check.get('check_id')} {reference.get('sha256')}"
                        )
                    evidence_key = (
                        reference.get("evidence_id"),
                        reference.get("sha256"),
                        reference.get("path"),
                        check.get("check_id"),
                    )
                    if evidence_key not in indexed_references:
                        raise ValueError(
                            f"check evidence disagrees with product index: {product_id} "
                            f"{check.get('check_id')}"
                        )
        calculated_overall = _aggregate_verdict(gate_verdicts)
        if receipt.get("overall_verdict") != calculated_overall:
            raise ValueError(f"overall verdict disagrees with gates: {product_id}")
        calculated_execution_complete = all(
            check.get("execution_status") == "completed"
            for gate in gates
            for check in gate.get("checks", [])
        )
        if bool(receipt.get("execution_complete")) != calculated_execution_complete:
            raise ValueError(
                f"receipt execution completeness disagrees with child checks: {product_id}"
            )
        calculated_eligible = calculated_overall == "PASS"
        if bool(receipt.get("eligible_for_ebuild")) != calculated_eligible:
            raise ValueError(f"receipt eligibility disagrees with child checks: {product_id}")
        if entry.get("verdict") != calculated_overall:
            raise ValueError(f"bundle receipt verdict disagrees with receipt: {product_id}")
        if bool(entry.get("eligible_for_ebuild")) != calculated_eligible:
            raise ValueError(f"bundle receipt eligibility disagrees with receipt: {product_id}")
        if bool(entry.get("execution_complete")) != calculated_execution_complete:
            raise ValueError(f"bundle receipt execution state disagrees with checks: {product_id}")
        verdict_counts[calculated_overall] += 1
        if calculated_eligible:
            eligible_products.append(product_id)
    calculated_selection_complete = bool(receipts)
    calculated_all_products = calculated_selection_complete and seen == inventory_ids
    if bool(bundle.get("all_products_executed")) != calculated_all_products:
        raise ValueError("all_products_executed disagrees with inventory receipt coverage")
    expected_summary = {
        "contract_version": bundle.get("contract_version"),
        "source_commit": bundle.get("source_commit"),
        "inventory_sha256": bundle.get("inventory_sha256"),
        "product_count": len(receipts),
        "inventory_product_count": len(inventory_ids),
        "selection_complete": calculated_selection_complete,
        "all_products_executed": calculated_all_products,
        "eligible_products": sorted(eligible_products),
        "verdict_counts": verdict_counts,
    }
    if summary != expected_summary:
        raise ValueError("validation summary disagrees with verified receipts")
    return bundle
