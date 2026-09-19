"""End-to-end tests for executable product validation and bundle verification."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestECADFunctional(unittest.TestCase):
    def test_product_validation_emits_a_verifiable_blocked_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "validation"
            validation = subprocess.run(
                [
                    sys.executable,
                    "tools/validate_products.py",
                    "validate",
                    "--product",
                    "eAerospace_CAD_Design:flight_control",
                    "--output",
                    str(output),
                    "--mode",
                    "evidence",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(validation.returncode, 0, validation.stderr)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["product_count"], 1)
            self.assertTrue(summary["selection_complete"])
            self.assertFalse(summary["all_products_executed"])
            self.assertEqual(summary["eligible_products"], [])

            verification = subprocess.run(
                [
                    sys.executable,
                    "tools/validate_products.py",
                    "verify-bundle",
                    str(output / "bundle.json"),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(verification.returncode, 0, verification.stderr)
            self.assertIn("verified 1 receipts", verification.stdout)

            gate_output = Path(directory) / "gate-validation"
            gate = subprocess.run(
                [
                    sys.executable,
                    "tools/validate_products.py",
                    "validate",
                    "--product",
                    "eAerospace_CAD_Design:flight_control",
                    "--output",
                    str(gate_output),
                    "--mode",
                    "gate",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(gate.returncode, 1)
            gate_summary = json.loads((gate_output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(gate_summary["eligible_products"], [])


if __name__ == "__main__":
    unittest.main()
