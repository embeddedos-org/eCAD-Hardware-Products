"""Performance claims remain blocked until executable evidence is declared."""

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from ecad_validation.cases import execute_cases  # noqa: E402
from ecad_validation.models import GateLevel, Verdict  # noqa: E402


class TestECADPerformance(unittest.TestCase):
    def test_autoroute_latency_without_corner_contract_is_blocked(self):
        """Do not manufacture an autorouting SLA from an empty timing loop."""
        with tempfile.TemporaryDirectory() as directory:
            product = Path(directory) / "product"
            product.mkdir()
            result = execute_cases(product, GateLevel.V4, "corners")

        self.assertEqual(result[0].verdict, Verdict.BLOCKED)
        self.assertEqual(result[0].reason_code, "CORNERS_EVIDENCE_MISSING")


if __name__ == "__main__":
    unittest.main()
