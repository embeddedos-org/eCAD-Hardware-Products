"""Contract tests for the versioned eCAD hardware validation schemas."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, FormatChecker, RefResolver


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "schemas" / "hardware-validation" / "v1"
SCHEMA_BASE = "https://embeddedos.org/schemas/hardware-validation/v1/"
SHA256 = "a" * 64
STAMP = "2026-09-19T07:00:00Z"
COMMIT = "1" * 40


def _load_schemas():
    schemas = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        with path.open(encoding="utf-8") as handle:
            schema = json.load(handle)
        schemas[path.name] = schema
    return schemas


SCHEMAS = _load_schemas()
STORE = {schema["$id"]: schema for schema in SCHEMAS.values()}


def _validator(name):
    schema = SCHEMAS[name]
    resolver = RefResolver.from_schema(schema, store=STORE)
    return Draft7Validator(schema, resolver=resolver, format_checker=FormatChecker())


def _artifact(path):
    return {
        "path": path,
        "sha256": SHA256,
        "media_type": "application/json",
        "size_bytes": 128,
    }


def _provenance(path="tools/catalog/taxonomy.json"):
    return {
        "source_type": "repository",
        "source_path": path,
        "source_commit": COMMIT,
        "recorded_at": STAMP,
    }


def _tool():
    return {
        "tool_id": "ecad-validator",
        "name": "eCAD validator",
        "version": "1.0.0",
        "invocation": ["python3", "tools/validate_products.py"],
        "settings": {"render": False},
    }


def _evidence(gate):
    return {
        "evidence_id": "evidence-{}".format(gate.lower()),
        "path": "validation/evidence/{}.json".format(gate.lower()),
        "sha256": SHA256,
        "media_type": "application/json",
        "size_bytes": 128,
    }


def _check(gate):
    return {
        "check_id": "{}-schema-check".format(gate.lower()),
        "gate": gate,
        "domain": "data_management",
        "layer": "validation",
        "tool_id": "ecad-validator",
        "execution_status": "completed",
        "verdict": "PASS",
        "reason_code": "CHECK_PASSED",
        "summary": "The declared check completed successfully.",
        "required": True,
        "requirement_ids": ["REQ-{}".format(gate)],
        "metrics": {"errors": 0},
        "evidence": [_evidence(gate)],
        "findings": [],
    }


def _receipt():
    return {
        "$schema": SCHEMA_BASE + "validation-receipt.schema.json",
        "contract_version": "1.0.0",
        "receipt_id": "receipt-product-one",
        "product": {"id": "product-one", "path": "eExample_CAD_Design/product_one"},
        "source": {
            "repository": "embeddedos-org/eCAD-Hardware-Products",
            "commit": COMMIT,
            "dirty": False,
            "input_sha256": SHA256,
        },
        "started_at": STAMP,
        "completed_at": STAMP,
        "tools": [_tool()],
        "gates": [
            {"gate": gate, "verdict": "PASS", "checks": [_check(gate)]}
            for gate in ("V0", "V1", "V2", "V3", "V4")
        ],
        "overall_verdict": "PASS",
        "execution_complete": True,
        "eligible_for_ebuild": True,
    }


def _valid_instances():
    evidence = _evidence("V0")
    return {
        "product-contract.schema.json": {
            "$schema": SCHEMA_BASE + "product-contract.schema.json",
            "contract_version": "1.0.0",
            "contract_id": "contract-product-one",
            "product": {
                "id": "product-one",
                "name": "Product One",
                "path": "eExample_CAD_Design/product_one",
            },
            "validation_scope": {
                "gates": ["V0", "V1", "V2", "V3", "V4"],
                "domains": [
                    "eda_circuit",
                    "physical_design",
                    "system_design",
                    "device_modeling",
                    "data_management",
                    "integrated_physics",
                ],
                "layers": ["design", "model", "simulation", "validation"],
            },
            "requirements": {
                "catalog": _artifact("validation/requirements.json"),
                "requirement_ids": ["REQ-V0"],
            },
            "baseline_findings": [
                {
                    "finding_id": "legacy-missing-layout",
                    "requirement_id": "REQ-V2",
                    "verdict": "BLOCKED",
                    "reason": "The legacy product has no checked-in PCB layout.",
                    "evidence": [evidence],
                }
            ],
            "provenance": _provenance(),
        },
        "requirements.schema.json": {
            "$schema": SCHEMA_BASE + "requirements.schema.json",
            "contract_version": "1.0.0",
            "catalog_id": "ecad-requirements",
            "requirements": [
                {
                    "requirement_id": "REQ-V0",
                    "title": "Manifest conforms to schema",
                    "statement": "The product manifest must conform to the v1 schema.",
                    "gate": "V0",
                    "domains": ["data_management"],
                    "layers": ["validation"],
                    "required": True,
                    "acceptance_criteria": ["No schema validation errors are emitted."],
                    "evidence_types": ["application/json"],
                }
            ],
            "provenance": _provenance(),
        },
        "product-manifest.schema.json": {
            "$schema": SCHEMA_BASE + "product-manifest.schema.json",
            "contract_version": "1.0.0",
            "product": {"id": "product-one", "path": "eExample_CAD_Design/product_one"},
            "source": {
                "repository": "embeddedos-org/eCAD-Hardware-Products",
                "commit": COMMIT,
                "dirty": False,
                "input_sha256": SHA256,
            },
            "generated_at": STAMP,
            "artifacts": [
                {
                    "artifact_id": "product-readme",
                    "path": "eExample_CAD_Design/product_one/README.md",
                    "sha256": SHA256,
                    "media_type": "text/markdown",
                    "size_bytes": 128,
                    "role": "design",
                    "provenance": _provenance("eExample_CAD_Design/product_one/README.md"),
                }
            ],
        },
        "validation-cases.schema.json": {
            "$schema": SCHEMA_BASE + "validation-cases.schema.json",
            "contract_version": "1.0.0",
            "gate": "V3",
            "cases": [
                {
                    "id": "thermal-reference",
                    "adapter": "python_control",
                    "domain": "integrated_physics",
                    "inputs": ["simulation/model.py"],
                    "requirement_ids": ["POLICY:V3-GOLDEN"],
                    "timeout_seconds": 30,
                    "seed": 7,
                    "settings": {},
                    "expected_metrics": {
                        "temperature_c": {"value": 42.0, "absolute_tolerance": 0.5}
                    },
                }
            ],
        },
        "validation-receipt.schema.json": _receipt(),
        "evidence-index.schema.json": {
            "$schema": SCHEMA_BASE + "evidence-index.schema.json",
            "contract_version": "1.0.0",
            "product_id": "product-one",
            "receipt_sha256": SHA256,
            "generated_at": STAMP,
            "evidence": [
                dict(
                    evidence,
                    check_id="v0-schema-check",
                    requirement_ids=["REQ-V0"],
                    producer_tool_id="ecad-validator",
                    captured_at=STAMP,
                    provenance={
                        "source_type": "generated",
                        "generator_tool_id": "ecad-validator",
                        "recorded_at": STAMP,
                    },
                )
            ],
        },
        "bundle.schema.json": {
            "$schema": SCHEMA_BASE + "bundle.schema.json",
            "contract_version": "1.0.0",
            "bundle_id": "bundle-product-one",
            "product_id": "product-one",
            "created_at": STAMP,
            "created_by": _tool(),
            "documents": {
                "product_contract": _artifact("validation/product-contract.json"),
                "requirements": _artifact("validation/requirements.json"),
                "product_manifest": _artifact("validation/product-manifest.json"),
                "validation_receipt": _artifact("validation/validation-receipt.json"),
                "evidence_index": _artifact("validation/evidence-index.json"),
            },
        },
        "repository-bundle.schema.json": {
            "$schema": SCHEMA_BASE + "repository-bundle.schema.json",
            "contract_version": "1.0.0",
            "source_commit": COMMIT,
            "inventory_sha256": SHA256,
            "inventory": _artifact("product-inventory.json"),
            "all_products_executed": True,
            "receipts": [
                {
                    "product_id": "product-one",
                    "path": "products/product-one/receipt.json",
                    "sha256": SHA256,
                    "verdict": "PASS",
                    "execution_complete": True,
                    "eligible_for_ebuild": True,
                    "bundle": _artifact("products/product-one/bundle.json"),
                }
            ],
            "summary": _artifact("summary.json"),
            "evidence_index": _artifact("evidence-index.json"),
        },
    }


def test_all_v1_schemas_are_valid_and_have_canonical_ids():
    assert set(SCHEMAS) == {
        "bundle.schema.json",
        "common.schema.json",
        "evidence-index.schema.json",
        "product-contract.schema.json",
        "product-manifest.schema.json",
        "repository-bundle.schema.json",
        "requirements.schema.json",
        "validation-cases.schema.json",
        "validation-receipt.schema.json",
    }
    assert len(STORE) == len(SCHEMAS)
    for name, schema in SCHEMAS.items():
        Draft7Validator.check_schema(schema)
        assert schema["$id"] == SCHEMA_BASE + name


@pytest.mark.parametrize("schema_name,instance", sorted(_valid_instances().items()))
def test_public_contract_examples_validate(schema_name, instance):
    _validator(schema_name).validate(instance)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda receipt: receipt["gates"][0]["checks"][0].update(evidence=[]),
        lambda receipt: receipt.update(overall_verdict="BLOCKED", eligible_for_ebuild=True),
        lambda receipt: receipt["gates"][0]["checks"][0].update(
            baseline_finding_id="legacy-finding", verdict="PASS"
        ),
        lambda receipt: receipt["gates"].pop(),
        lambda receipt: receipt["gates"][0]["checks"][0].update(gate="V1"),
        lambda receipt: receipt["gates"][0]["checks"][0].update(domain="unknown_domain"),
        lambda receipt: receipt["gates"][0]["checks"][0]["evidence"][0].update(
            path="/tmp/fabricated-evidence.json"
        ),
    ],
)
def test_receipt_rejects_non_pass_mutations(mutate):
    receipt = copy.deepcopy(_receipt())
    mutate(receipt)
    assert list(_validator("validation-receipt.schema.json").iter_errors(receipt))


def test_repository_bundle_separates_coverage_from_execution_and_eligibility():
    bundle = _valid_instances()["repository-bundle.schema.json"]
    bundle["receipts"][0].update(
        verdict="BLOCKED",
        execution_complete=False,
        eligible_for_ebuild=False,
    )
    _validator("repository-bundle.schema.json").validate(bundle)


def test_repository_bundle_rejects_non_pass_eligibility():
    bundle = _valid_instances()["repository-bundle.schema.json"]
    bundle["receipts"][0].update(verdict="BLOCKED", eligible_for_ebuild=True)
    assert list(_validator("repository-bundle.schema.json").iter_errors(bundle))


def test_committed_policy_requirements_validate():
    policy = json.loads(
        (
            REPO_ROOT
            / "contracts"
            / "hardware-validation"
            / "v1"
            / "policy-requirements.json"
        ).read_text(encoding="utf-8")
    )
    _validator("requirements.schema.json").validate(policy)
    assert {item["gate"] for item in policy["requirements"]} == {
        "V0",
        "V1",
        "V2",
        "V3",
        "V4",
    }


def test_empty_evidence_index_is_valid_for_a_fully_blocked_run():
    evidence_index = _valid_instances()["evidence-index.schema.json"]
    evidence_index["evidence"] = []
    _validator("evidence-index.schema.json").validate(evidence_index)


def test_execution_complete_rejects_timeout_or_crash_states():
    receipt = _receipt()
    check = receipt["gates"][3]["checks"][0]
    check.update(execution_status="timed_out", verdict="INCONCLUSIVE")
    receipt["gates"][3]["verdict"] = "INCONCLUSIVE"
    receipt.update(overall_verdict="INCONCLUSIVE", eligible_for_ebuild=False)
    assert list(_validator("validation-receipt.schema.json").iter_errors(receipt))


def test_blocked_receipt_is_valid_but_not_eligible():
    receipt = _receipt()
    check = receipt["gates"][2]["checks"][0]
    check.update(
        execution_status="unavailable",
        verdict="BLOCKED",
        reason_code="TOOL_UNAVAILABLE",
        summary="The required CAD tool was unavailable.",
        evidence=[],
    )
    receipt["gates"][2]["verdict"] = "BLOCKED"
    receipt.update(
        overall_verdict="BLOCKED",
        execution_complete=False,
        eligible_for_ebuild=False,
    )
    _validator("validation-receipt.schema.json").validate(receipt)
