"""Issue #28: dev-board records validate and queries stay honest."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from devboard_cad.query import cmd_commercial, cmd_with, load_records  # noqa: E402
from jsonschema import Draft7Validator  # noqa: E402


def _schema() -> dict:
    return json.loads(
        (
            REPO_ROOT / "schemas" / "devboard-cad" / "v1" / "board-record.schema.json"
        ).read_text(encoding="utf-8")
    )


class FakeArgs:
    def __init__(self, root: Path, formats: list[str] | None = None) -> None:
        self.root = str(root)
        self.formats = formats or []


class TestDevboardDatabase(unittest.TestCase):
    def test_every_record_conforms_to_schema(self) -> None:
        schema = _schema()
        Draft7Validator.check_schema(schema)
        records = load_records(REPO_ROOT)
        self.assertGreaterEqual(len(records), 5)
        for record in records:
            errors = list(Draft7Validator(schema).iter_errors(record))
            self.assertEqual(errors, [], f"{record.get('board_id')}: {errors[:2]}")

    def test_no_seed_record_claims_verified_availability(self) -> None:
        for record in load_records(REPO_ROOT):
            for name, entry in record["files"].items():
                self.assertIsNone(
                    entry["available"],
                    f"{record['board_id']}.{name} must stay unknown until verified",
                )
            self.assertEqual(record["record_status"], "incomplete")

    def test_positive_queries_match_nothing_until_verified(self) -> None:
        import io
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            cmd_with(FakeArgs(REPO_ROOT, ["step"]))
        self.assertIn("matched=0", buffer.getvalue())

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            cmd_commercial(FakeArgs(REPO_ROOT))
        self.assertIn("matched=0", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
