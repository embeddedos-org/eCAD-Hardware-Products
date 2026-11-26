"""Gate and drift-check the development-board CAD database (issue #28).

Two modes, because they answer different questions and must fail differently.

``validate`` (default, offline) answers "is this database internally sound?". It is safe to
block a pull request on, because nothing in it can fail for a reason the author does not
control - no vendor is contacted.

``--revalidate`` (networked) answers "is this database still true of the world?". Records
age against the vendors rather than against the repository: URLs move, product pages are
reorganised, revisions supersede one another. It re-fetches what each record claims and
reports drift. It is advisory by construction, since a vendor outage or a newly deployed bot
challenge says nothing about the correctness of the data.

A drifted digest is never repaired silently. Silent repair would turn a vendor swapping a
file under a stable URL - exactly the event worth knowing about - into an invisible one.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from devboard_cad.query import FILE_FORMATS  # noqa: E402
from devboard_cad.verify import Fetcher, derive_status, records_dir  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "schemas" / "devboard-cad" / "v1" / "board-record.schema.json"
DRIFT_REPORT = "devboard-cad-drift.json"


def _load_schema() -> Dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate(root: Path) -> List[str]:
    """Return a list of problems. Empty means the database is internally sound."""
    from jsonschema import Draft7Validator

    schema = _load_schema()
    Draft7Validator.check_schema(schema)
    validator = Draft7Validator(schema)

    problems: List[str] = []
    seen: Dict[str, str] = {}
    paths = sorted(records_dir(root).glob("*.json"))
    if not paths:
        return [f"no records found under {records_dir(root)}"]

    for path in paths:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{path.name}: not valid JSON ({exc})")
            continue

        for error in validator.iter_errors(record):
            location = "/".join(str(p) for p in error.absolute_path) or "<root>"
            problems.append(f"{path.name}: {location}: {error.message}")

        board_id = record.get("board_id")
        if not isinstance(board_id, str):
            continue
        if board_id in seen:
            problems.append(f"{path.name}: board_id '{board_id}' already used by {seen[board_id]}")
        seen[board_id] = path.name
        if path.stem != board_id.replace(":", "__"):
            problems.append(
                f"{path.name}: filename does not match board_id '{board_id}' "
                f"(expected {board_id.replace(':', '__')}.json)")

        derived = derive_status(record)
        if record.get("record_status") != derived:
            problems.append(
                f"{path.name}: record_status is '{record.get('record_status')}' but the "
                f"data says '{derived}'")

        for name, entry in record.get("files", {}).items():
            if name not in FILE_FORMATS:
                problems.append(f"{path.name}: format '{name}' is not queryable by query.py")
            if entry.get("available") is None and entry.get("evidence") is not None:
                problems.append(
                    f"{path.name}: {name}: unknown must not carry evidence, or 'we have not "
                    f"looked' becomes indistinguishable from 'we looked and it is absent'")
            if entry.get("available") is None and entry.get("verified_geometry") is not None:
                problems.append(
                    f"{path.name}: {name}: unknown must not carry verified_geometry")

        problems.extend(_licence_problems(path.name, record))

    return problems


def _licence_problems(name: str, record: Dict[str, Any]) -> List[str]:
    """Licensing is the part that does not automate, so its claims need a citation.

    Issue #28 section 12 keeps licensing separate from file availability, and
    ``commercial_use_allowed`` is the field a downstream user will actually rely on. A bare
    boolean with nothing behind it is worse than an honest null.
    """
    problems: List[str] = []
    licenses = record.get("licenses", {})
    decided = [f for f in ("commercial_use_allowed", "modification_allowed",
                           "redistribution_allowed")
               if licenses.get(f) is not None]
    if decided:
        if not licenses.get("license_url"):
            problems.append(
                f"{name}: {', '.join(decided)} decided with no license_url")
        if str(licenses.get("hardware_license", "")).strip().upper() in {"", "UNVERIFIED"}:
            problems.append(
                f"{name}: {', '.join(decided)} decided with no named hardware_license")
    if record.get("sources", {}).get("source_tier") == "community" \
            and not (record.get("notes") or "").strip():
        problems.append(
            f"{name}: community source tier with no justification in notes "
            f"(issue #28 section 10 makes it a last resort)")
    return problems


def revalidate(root: Path, min_interval: float, timeout: float) -> Tuple[List[Dict[str, Any]], int]:
    """Re-fetch every positively claimed file and compare against the recorded digest."""
    fetcher = Fetcher(min_interval=min_interval, timeout=timeout, refresh=True)
    findings: List[Dict[str, Any]] = []
    checked = 0

    for path in sorted(records_dir(root).glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        for name, entry in record.get("files", {}).items():
            if entry.get("available") is not True:
                continue
            url = entry.get("url")
            recorded = (entry.get("evidence") or {}).get("sha256")
            if not url or not recorded:
                continue
            checked += 1
            result = fetcher.get(url)
            if result.payload is None:
                findings.append({
                    "board_id": record["board_id"], "format": name, "url": url,
                    "kind": "unreachable", "http_status": result.status,
                    "detail": result.error,
                    "action": "demote to null after confirming the vendor moved the file; "
                              "do not record false without an index or a 404",
                })
                continue
            if result.sha256 != recorded:
                findings.append({
                    "board_id": record["board_id"], "format": name, "url": url,
                    "kind": "digest_changed", "recorded_sha256": recorded,
                    "observed_sha256": result.sha256,
                    "observed_size": result.size,
                    "action": "the vendor replaced the file at a stable URL; re-verify the "
                              "revision before updating the record",
                })

    report = {
        "checked": checked,
        "findings": findings,
        "summary": f"{len(findings)} of {checked} claimed file(s) drifted",
    }
    Path(DRIFT_REPORT).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return findings, checked


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--revalidate", action="store_true",
                        help="also re-fetch claimed files and report digest drift")
    parser.add_argument("--min-interval", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    problems = validate(root)
    count = len(sorted(records_dir(root).glob("*.json")))
    if problems:
        print(f"{len(problems)} problem(s) across {count} record(s):", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(f"{count} record(s) validate against {SCHEMA_PATH.relative_to(root)}")

    if args.revalidate:
        findings, checked = revalidate(root, args.min_interval, args.timeout)
        print(f"revalidated {checked} claimed file(s); {len(findings)} drifted")
        for finding in findings:
            print(f"  {finding['board_id']}.{finding['format']}: {finding['kind']}")
        print(f"report written to {DRIFT_REPORT}")
        # Advisory: drift is news, not a defect in the commit under test.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
