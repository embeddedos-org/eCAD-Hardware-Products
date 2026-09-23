"""Failure semantics for external validation tool adapters."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from ecad_validation.adapters.base import AdapterRequest  # noqa: E402
from ecad_validation.adapters.process import ProcessRequest, run_process  # noqa: E402
from ecad_validation.adapters.python_control import PythonControlAdapter  # noqa: E402
from ecad_validation.models import ExecutionStatus, Verdict  # noqa: E402


class TestProcessRunner(unittest.TestCase):
    def test_missing_executable_is_unavailable_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_process(
                ProcessRequest(
                    argv=["ecad-tool-that-does-not-exist"],
                    input_root=root,
                    input_files=[],
                )
            )
        self.assertEqual(result.execution_status, ExecutionStatus.UNAVAILABLE)
        self.assertEqual(result.reason_code, "TOOL_NOT_INSTALLED")
        self.assertIsNone(result.returncode)

    def test_timeout_is_not_reported_as_completed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "slow.py"
            script.write_text("import time\ntime.sleep(2)\n", encoding="utf-8")
            result = run_process(
                ProcessRequest(
                    argv=[sys.executable, "slow.py"],
                    input_root=root,
                    input_files=[script],
                    timeout_seconds=1,
                )
            )
        self.assertEqual(result.execution_status, ExecutionStatus.TIMED_OUT)
        self.assertEqual(result.reason_code, "TOOL_TIMED_OUT")


class TestPythonControlAdapter(unittest.TestCase):
    def test_json_metrics_are_required_for_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "model.py"
            script.write_text('print("not metrics")\n', encoding="utf-8")
            result = PythonControlAdapter().run(
                AdapterRequest(
                    case_id="missing-metrics",
                    product_root=root,
                    input_files=[script],
                )
            )
        self.assertEqual(result.verdict, Verdict.INCONCLUSIVE)
        self.assertEqual(result.reason_code, "METRICS_JSON_INVALID")

    def test_deterministic_json_metrics_can_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "model.py"
            script.write_text('print("{\\"current_a\\": 1.25}")\n', encoding="utf-8")
            result = PythonControlAdapter().run(
                AdapterRequest(
                    case_id="golden-current",
                    product_root=root,
                    input_files=[script],
                    seed=7,
                )
            )
        self.assertEqual(result.execution_status, ExecutionStatus.COMPLETED)
        self.assertEqual(result.verdict, Verdict.PASS)
        self.assertEqual(result.metrics, {"current_a": 1.25})


if __name__ == "__main__":
    unittest.main()
