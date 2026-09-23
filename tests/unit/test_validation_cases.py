"""Executable golden and corner case tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from ecad_validation.cases import execute_cases  # noqa: E402
from ecad_validation.models import GateLevel, Verdict  # noqa: E402


class TestExecutableCases(unittest.TestCase):
    def _product(self, root: Path, directory: str, case: dict) -> Path:
        product = root / "product"
        (product / "simulation").mkdir(parents=True)
        (product / "validation" / directory).mkdir(parents=True)
        (product / "simulation" / "model.py").write_text(
            'print("{\\"temperature_c\\": 42.5}")\n', encoding="utf-8"
        )
        case.setdefault(
            "domain",
            "system_design" if directory == "golden" else "integrated_physics",
        )
        case.setdefault(
            "requirement_ids",
            ["POLICY:V3-GOLDEN" if directory == "golden" else "POLICY:V4-CORNER"],
        )
        (product / "validation" / directory / "cases.json").write_text(
            json.dumps(
                {
                    "$schema": "https://embeddedos.org/schemas/hardware-validation/v1/validation-cases.schema.json",
                    "contract_version": "1.0.0",
                    "gate": "V3" if directory == "golden" else "V4",
                    "cases": [case],
                }
            ),
            encoding="utf-8",
        )
        return product

    def test_golden_case_compares_real_adapter_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            product = self._product(
                Path(directory),
                "golden",
                {
                    "id": "thermal-reference",
                    "adapter": "python_control",
                    "inputs": ["simulation/model.py"],
                    "expected_metrics": {
                        "temperature_c": {"value": 42.0, "absolute_tolerance": 0.5}
                    },
                    "requirement_ids": ["POLICY:V3-GOLDEN"],
                },
            )
            result = execute_cases(product, GateLevel.V3, "golden")[0]
        self.assertEqual(result.verdict, Verdict.PASS)
        self.assertEqual(result.reason_code, "GOLDEN_COMPARISON_PASSED")
        self.assertEqual(result.requirement_ids, ["POLICY:V3-GOLDEN"])
        generated = [item for item in result.evidence if item.path.startswith("generated/")]
        self.assertEqual(len(generated), 1)
        payload = result.generated_evidence[generated[0].path]
        self.assertEqual(json.loads(payload)["metrics"], {"temperature_c": 42.5})

    def test_golden_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            product = self._product(
                Path(directory),
                "golden",
                {
                    "id": "thermal-reference",
                    "adapter": "python_control",
                    "inputs": ["simulation/model.py"],
                    "expected_metrics": {
                        "temperature_c": {"value": 40.0, "absolute_tolerance": 0.1}
                    },
                },
            )
            result = execute_cases(product, GateLevel.V3, "golden")[0]
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "GOLDEN_COMPARISON_FAILED")

    def test_corner_outside_limit_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            product = self._product(
                Path(directory),
                "corners",
                {
                    "id": "hot-corner",
                    "adapter": "python_control",
                    "inputs": ["simulation/model.py"],
                    "metric_limits": {"temperature_c": {"maximum": 40.0}},
                },
            )
            result = execute_cases(product, GateLevel.V4, "corners")[0]
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "CORNER_LIMITS_FAILED")

    def test_duplicate_case_ids_fail_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product = self._product(
                root,
                "golden",
                {
                    "id": "duplicate",
                    "adapter": "python_control",
                    "inputs": ["simulation/model.py"],
                    "expected_metrics": {
                        "temperature_c": {"value": 42.5, "absolute_tolerance": 0.1}
                    },
                },
            )
            manifest = product / "validation" / "golden" / "cases.json"
            document = json.loads(manifest.read_text(encoding="utf-8"))
            document["cases"].append(dict(document["cases"][0]))
            manifest.write_text(json.dumps(document), encoding="utf-8")

            result = execute_cases(product, GateLevel.V3, "golden")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].verdict, Verdict.FAIL)
        self.assertEqual(result[0].reason_code, "DUPLICATE_CASE_ID")

    def test_invalid_timeout_is_rejected_by_case_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            product = self._product(
                Path(directory),
                "golden",
                {
                    "id": "invalid-timeout",
                    "adapter": "python_control",
                    "inputs": ["simulation/model.py"],
                    "timeout_seconds": "not-an-integer",
                    "expected_metrics": {"temperature_c": {"value": 42.5, "absolute_tolerance": 0}},
                },
            )
            result = execute_cases(product, GateLevel.V3, "golden")[0]
        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.reason_code, "CASE_SCHEMA_INVALID")

    def test_missing_case_input_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            product = self._product(
                Path(directory),
                "golden",
                {
                    "id": "missing-model",
                    "adapter": "python_control",
                    "inputs": ["simulation/not-there.py"],
                    "expected_metrics": {"x": {"value": 1, "absolute_tolerance": 0}},
                },
            )
            result = execute_cases(product, GateLevel.V3, "golden")[0]
        self.assertEqual(result.verdict, Verdict.BLOCKED)
        self.assertEqual(result.reason_code, "CASE_INPUT_MISSING_OR_UNSAFE")


if __name__ == "__main__":
    unittest.main()
