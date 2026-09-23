"""Regression tests for the repository CI workflow and test entry point."""

import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import run_all_tests


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"


class TestCIWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    def test_targets_repository_default_branch(self):
        self.assertIn("branches: [master, develop]", self.workflow)
        self.assertIn("branches: [master]", self.workflow)
        self.assertNotIn("branches: [main", self.workflow)

    def test_installs_checked_in_requirements(self):
        self.assertIn("cache-dependency-path: tools/requirements.txt", self.workflow)
        self.assertIn(
            "python -m pip install -r tools/requirements.txt",
            self.workflow,
        )

    def test_runs_complete_suite_through_repository_runner(self):
        self.assertIn("run: python run_all_tests.py --tb=short", self.workflow)
        for incomplete_path in (
            "tests/unit/",
            "tests/functional/",
            "tests/performance/",
            "tests/simulation/",
        ):
            self.assertNotIn(incomplete_path, self.workflow)

    def test_executes_and_verifies_complete_inventory_evidence(self):
        self.assertIn("validation-evidence:", self.workflow)
        self.assertIn("validate --all", self.workflow)
        self.assertIn("--mode evidence", self.workflow)
        self.assertIn("verify-bundle", self.workflow)
        self.assertIn("uses: actions/upload-artifact@v4", self.workflow)
        self.assertIn("needs: [test, validation-evidence]", self.workflow)

    def test_does_not_attempt_to_build_absent_python_package(self):
        self.assertNotIn("python -m build", self.workflow)
        self.assertNotIn("dist/*.whl", self.workflow)


class TestTestRunner(unittest.TestCase):
    @mock.patch("run_all_tests.subprocess.run")
    def test_runs_entire_tests_tree_with_current_python(self, run):
        run.return_value = subprocess.CompletedProcess(args=[], returncode=7)
        stdout = io.StringIO()

        with mock.patch("sys.stdout", stdout):
            returncode = run_all_tests.main(["--tb=short"])

        run.assert_called_once_with(
            [sys.executable, "-m", "pytest", "tests", "-v", "--tb=short"],
            check=False,
        )
        self.assertEqual(returncode, 7)
        self.assertIn("complete test suite", stdout.getvalue())
        self.assertNotIn("production-ready", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
