"""Tests for the strict eCAD validation contract foundation."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

from jsonschema import Draft7Validator, FormatChecker, RefResolver

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from ecad_validation.discovery import (  # noqa: E402
    InventoryEntry,
    discover_candidate_products,
    entries_from_document,
    load_inventory,
    reconcile_inventory,
)
from ecad_validation.engine import _v0_checks, validate_product  # noqa: E402
from ecad_validation.evidence import verify_bundle, write_bundle  # noqa: E402
from ecad_validation.hashing import (  # noqa: E402
    canonical_json_bytes,
    hash_tree,
    sha256_bytes,
    sha256_file,
)
from ecad_validation.models import (  # noqa: E402
    CheckResult,
    Domain,
    ExecutionStatus,
    EvidenceReference,
    GateLevel,
    GateResult,
    Layer,
    ProductRunResult,
    RepositoryRunResult,
    Verdict,
)


def passing_check(gate: GateLevel) -> CheckResult:
    return CheckResult(
        check_id=f"{gate.value.lower()}.test",
        gate=gate,
        domain=Domain.DATA_MANAGEMENT,
        layer=Layer.VALIDATION,
        execution_status=ExecutionStatus.COMPLETED,
        verdict=Verdict.PASS,
        reason_code="CHECK_PASSED",
        summary="fixture passed",
        evidence=[
            EvidenceReference(
                path="fixture.json",
                sha256="d" * 64,
                media_type="application/json",
                size_bytes=1,
            )
        ],
    )


class TestStrictResultModel(unittest.TestCase):
    def test_pass_requires_completed_execution(self):
        with self.assertRaisesRegex(ValueError, "PASS requires"):
            CheckResult(
                check_id="v0.invalid",
                gate=GateLevel.V0,
                domain=Domain.DATA_MANAGEMENT,
                layer=Layer.VALIDATION,
                execution_status=ExecutionStatus.SKIPPED,
                verdict=Verdict.PASS,
                reason_code="INVALID",
                summary="must fail construction",
            )

    def test_required_warning_cannot_satisfy_gate(self):
        warning = passing_check(GateLevel.V0)
        warning.verdict = Verdict.WARNING
        gate = GateResult.from_checks(GateLevel.V0, [warning])
        self.assertEqual(gate.verdict, Verdict.BLOCKED)

    def test_every_non_pass_required_state_denies_eligibility(self):
        for denied in (
            Verdict.FAIL,
            Verdict.WARNING,
            Verdict.NOT_RUN,
            Verdict.BLOCKED,
            Verdict.INCONCLUSIVE,
        ):
            with self.subTest(verdict=denied):
                gates = []
                for level in GateLevel:
                    check = passing_check(level)
                    if level is GateLevel.V3:
                        check.verdict = denied
                    gates.append(GateResult.from_checks(level, [check]))
                product = ProductRunResult(
                    product_id="fixture:product",
                    product_path="fixture/product",
                    source_commit="a" * 40,
                    source_dirty=False,
                    input_sha256="b" * 64,
                    started_at="2026-09-19T07:00:00Z",
                    completed_at="2026-09-19T07:00:01Z",
                    gates=gates,
                    tools=[{"tool_id": "ecad-validator", "name": "validator", "version": "1.0.0", "invocation": ["python"], "settings": {}}],
                )
                self.assertFalse(product.eligible_for_ebuild)

    def test_missing_gate_blocks_product(self):
        gates = [
            GateResult.from_checks(level, [passing_check(level)])
            for level in (GateLevel.V0, GateLevel.V1, GateLevel.V2, GateLevel.V3)
        ]
        product = ProductRunResult(
            product_id="fixture:product",
            product_path="fixture/product",
            source_commit="a" * 40,
            source_dirty=False,
            input_sha256="b" * 64,
            started_at="2026-09-19T07:00:00Z",
            completed_at="2026-09-19T07:00:01Z",
            gates=gates,
            tools=[{"tool_id": "ecad-validator", "name": "validator", "version": "1.0.0", "invocation": ["python"], "settings": {}}],
        )
        self.assertEqual(product.overall_verdict, Verdict.BLOCKED)


class TestProductInventory(unittest.TestCase):
    def setUp(self):
        self.inventory_path = REPO_ROOT / "tools" / "catalog" / "product_inventory.json"
        self.document = load_inventory(self.inventory_path)

    def test_inventory_matches_every_discovered_product(self):
        self.assertEqual(reconcile_inventory(REPO_ROOT, self.document), [])
        committed = entries_from_document(self.document)
        discovered = discover_candidate_products(REPO_ROOT)
        self.assertEqual(committed, discovered)
        self.assertEqual(len(committed), 125)

    def test_future_concepts_are_not_silently_omitted(self):
        ids = {entry.product_id for entry in entries_from_document(self.document)}
        self.assertIn("future_designs:eBCI-Lite", ids)
        self.assertIn("future_designs:eVision", ids)

    def test_historical_baseline_does_not_hide_bom_failure(self):
        product = REPO_ROOT / "eConsumer_CAD_Design" / "smart_devices"
        checks = _v0_checks(product)
        bom = next(check for check in checks if check.check_id == "v0.canonical-bom")
        self.assertEqual(bom.verdict, Verdict.FAIL)
        self.assertTrue(any("stated total" in finding for finding in bom.findings))

    def test_real_product_emits_schema_valid_blocked_receipt(self):
        entry = next(
            item
            for item in entries_from_document(self.document)
            if item.product_id == "eAerospace_CAD_Design:flight_control"
        )
        product = validate_product(
            REPO_ROOT,
            entry,
            source_commit="a" * 40,
            source_dirty=True,
        )
        self.assertEqual(product.overall_verdict, Verdict.BLOCKED)
        source_check = next(
            check
            for check in product.gates[0].checks
            if check.check_id == "v0.pinned-clean-source"
        )
        self.assertEqual(source_check.verdict, Verdict.BLOCKED)
        self.assertEqual(source_check.reason_code, "SOURCE_TREE_DIRTY")
        receipt_validator().validate(product.to_receipt())

    def test_product_tree_mutation_during_validation_is_a_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product_root = root / "division" / "product"
            product_root.mkdir(parents=True)
            (product_root / "input.txt").write_text("before", encoding="utf-8")
            entry = InventoryEntry(
                product_id="division:product",
                path="division/product",
                division="division",
                lifecycle="design",
            )

            def mutate(_product):
                (product_root / "input.txt").write_text("after", encoding="utf-8")
                return []

            with mock.patch("ecad_validation.engine._v1_checks", side_effect=mutate):
                result = validate_product(
                    root,
                    entry,
                    source_commit="a" * 40,
                    source_dirty=False,
                )

        mutation_check = next(
            check
            for check in result.gates[0].checks
            if check.check_id == "v0.validation-input-immutability"
        )
        self.assertEqual(mutation_check.verdict, Verdict.FAIL)
        self.assertEqual(
            mutation_check.reason_code,
            "SOURCE_MUTATED_DURING_VALIDATION",
        )
        self.assertEqual(result.overall_verdict, Verdict.FAIL)


def receipt_validator() -> Draft7Validator:
    schema_dir = REPO_ROOT / "schemas" / "hardware-validation" / "v1"
    schemas = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in schema_dir.glob("*.schema.json")
    }
    schema = schemas["validation-receipt.schema.json"]
    store = {value["$id"]: value for value in schemas.values() if "$id" in value}
    return Draft7Validator(
        schema,
        resolver=RefResolver.from_schema(schema, store=store),
        format_checker=FormatChecker(),
    )


class TestEvidenceBundle(unittest.TestCase):
    def _passing_repository(self, source_root: Path) -> RepositoryRunResult:
        shutil.copytree(REPO_ROOT / "schemas", source_root / "schemas")
        shutil.copytree(REPO_ROOT / "contracts", source_root / "contracts")
        inventory = {
            "contract_version": "1.0.0",
            "discovery_policy": "artifact-union-v1",
            "products": [
                {
                    "division": "fixture",
                    "lifecycle": "design",
                    "path": "fixture/product",
                    "product_id": "fixture:product",
                }
            ],
        }
        inventory_path = source_root / "tools" / "catalog" / "product_inventory.json"
        inventory_path.parent.mkdir(parents=True)
        inventory_path.write_bytes(canonical_json_bytes(inventory) + b"\n")
        evidence_path = source_root / "fixture" / "product" / "fixture.json"
        evidence_path.parent.mkdir(parents=True)
        evidence_path.write_text("{}\n", encoding="utf-8")
        evidence = EvidenceReference(
            path="fixture.json",
            sha256=sha256_file(evidence_path),
            media_type="application/json",
            size_bytes=evidence_path.stat().st_size,
        )
        gates = []
        for level in GateLevel:
            check = passing_check(level)
            check.evidence = [evidence]
            if level is GateLevel.V3:
                generated = canonical_json_bytes({"metric": 1}) + b"\n"
                generated_digest = sha256_bytes(generated)
                generated_path = f"generated/{generated_digest}.json"
                check.evidence.append(
                    EvidenceReference(
                        path=generated_path,
                        sha256=generated_digest,
                        media_type="application/json",
                        size_bytes=len(generated),
                    )
                )
                check.generated_evidence[generated_path] = generated
            gates.append(GateResult.from_checks(level, [check]))
        product = ProductRunResult(
            product_id="fixture:product",
            product_path="fixture/product",
            source_commit="a" * 40,
            source_dirty=False,
            input_sha256=hash_tree(evidence_path.parent, [evidence_path]),
            started_at="2026-09-19T07:00:00Z",
            completed_at="2026-09-19T07:00:01Z",
            gates=gates,
            tools=[{"tool_id": "ecad-validator", "name": "validator", "version": "1.0.0", "invocation": ["python"], "settings": {}}],
        )
        return RepositoryRunResult(
            source_commit="a" * 40,
            products=[product],
            inventory_sha256=sha256_bytes(canonical_json_bytes(inventory)),
            inventory_product_ids=["fixture:product"],
        )

    def test_emitted_receipt_conforms_to_v1_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory) / "source"
            product = self._passing_repository(source_root).products[0]
            receipt_validator().validate(product.to_receipt())

    def test_inventory_coverage_is_distinct_from_selected_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self._passing_repository(Path(directory) / "source")
            result.inventory_product_ids.append("fixture:missing-product")
            self.assertTrue(result.selection_complete)
            self.assertFalse(result.all_products_executed)

    def test_bundle_verifier_recomputes_inventory_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory) / "source"
            output = Path(directory) / "bundle"
            bundle_path = write_bundle(source_root, output, self._passing_repository(source_root))
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            bundle["all_products_executed"] = False
            bundle_path.write_bytes(canonical_json_bytes(bundle) + b"\n")
            with self.assertRaisesRegex(ValueError, "disagrees with inventory receipt coverage"):
                verify_bundle(bundle_path)

    def test_bundle_verifier_recomputes_summary_from_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory) / "source"
            output = Path(directory) / "bundle"
            bundle_path = write_bundle(source_root, output, self._passing_repository(source_root))
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            summary_path = output / bundle["summary"]["path"]
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["eligible_products"] = []
            summary_path.write_bytes(canonical_json_bytes(summary) + b"\n")
            bundle["summary"]["sha256"] = sha256_file(summary_path)
            bundle["summary"]["size_bytes"] = summary_path.stat().st_size
            bundle_path.write_bytes(canonical_json_bytes(bundle) + b"\n")

            with self.assertRaisesRegex(ValueError, "summary disagrees"):
                verify_bundle(bundle_path)

    def test_bundle_verifier_recomputes_receipt_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory) / "source"
            output = Path(directory) / "bundle"
            bundle_path = write_bundle(source_root, output, self._passing_repository(source_root))
            verified = verify_bundle(bundle_path)
            self.assertEqual(len(verified["receipts"]), 1)
            ET.parse(output / "junit.xml")
            product_dir = output / "products" / "fixture__product"
            self.assertIn("fixture:product", (product_dir / "report.html").read_text())

            receipt = output / verified["receipts"][0]["path"]
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            payload["eligible_for_ebuild"] = False
            receipt.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                verify_bundle(bundle_path)

    def test_bundle_verifier_recomputes_gate_verdicts(self):
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory) / "source"
            output = Path(directory) / "bundle"
            bundle_path = write_bundle(source_root, output, self._passing_repository(source_root))
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            receipt_path = output / bundle["receipts"][0]["path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["gates"][0]["verdict"] = "BLOCKED"
            receipt["overall_verdict"] = "BLOCKED"
            receipt["eligible_for_ebuild"] = False
            receipt_path.write_bytes(canonical_json_bytes(receipt) + b"\n")
            receipt_entry = bundle["receipts"][0]
            receipt_entry["sha256"] = sha256_file(receipt_path)
            receipt_entry["verdict"] = "BLOCKED"
            receipt_entry["eligible_for_ebuild"] = False
            product_bundle_path = output / receipt_entry["bundle"]["path"]
            product_bundle = json.loads(product_bundle_path.read_text(encoding="utf-8"))
            receipt_document = product_bundle["documents"]["validation_receipt"]
            receipt_document["sha256"] = receipt_entry["sha256"]
            receipt_document["size_bytes"] = receipt_path.stat().st_size
            evidence_document = product_bundle["documents"]["evidence_index"]
            evidence_path = product_bundle_path.parent / evidence_document["path"]
            evidence_index = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence_index["receipt_sha256"] = receipt_entry["sha256"]
            evidence_path.write_bytes(canonical_json_bytes(evidence_index) + b"\n")
            evidence_document["sha256"] = sha256_file(evidence_path)
            evidence_document["size_bytes"] = evidence_path.stat().st_size
            product_bundle_path.write_bytes(canonical_json_bytes(product_bundle) + b"\n")
            receipt_entry["bundle"]["sha256"] = sha256_file(product_bundle_path)
            receipt_entry["bundle"]["size_bytes"] = product_bundle_path.stat().st_size
            bundle_path.write_bytes(canonical_json_bytes(bundle) + b"\n")
            with self.assertRaisesRegex(ValueError, "verdict disagrees with child checks"):
                verify_bundle(bundle_path)


if __name__ == "__main__":
    unittest.main()
