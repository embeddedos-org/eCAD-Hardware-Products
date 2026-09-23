"""Simulation truth tests: absent engineering evidence must never pass."""

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from ecad_validation.cases import execute_cases  # noqa: E402
from ecad_validation.models import ExecutionStatus, GateLevel, Verdict  # noqa: E402


class TestECADSimulation(unittest.TestCase):
    def test_signal_integrity_without_reference_model_is_blocked(self):
        """A missing SI model is unknown engineering state, not a synthetic pass."""
        with tempfile.TemporaryDirectory() as directory:
            product = Path(directory) / "product"
            product.mkdir()
            result = execute_cases(product, GateLevel.V3, "golden")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].execution_status, ExecutionStatus.UNAVAILABLE)
        self.assertEqual(result[0].verdict, Verdict.BLOCKED)
        self.assertEqual(result[0].reason_code, "GOLDEN_EVIDENCE_MISSING")


if __name__ == "__main__":
    unittest.main()
