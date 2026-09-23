"""Query the development-board CAD record database (issue #28).

Every availability field is tri-state: True (verified present), False
(verified absent), or null (unknown). Unknown never counts as a match for a
positive claim, and records never assert family-level coverage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FILE_FORMATS = (
    "schematic",
    "pcb_source",
    "gerbers",
    "bom",
    "pick_and_place",
    "step",
    "dxf",
    "stl",
    "kicad",
    "eagle",
    "altium",
    "mechanical",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _records_dir(root: Path) -> Path:
    return root / "tools" / "devboard_cad" / "records"


def load_records(root: Path) -> list[dict]:
    records = []
    for path in sorted(_records_dir(root).glob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def has_format(record: dict, name: str) -> bool:
    return record.get("files", {}).get(name, {}).get("available") is True


def _print(records: list[dict]) -> int:
    for record in records:
        print(f"{record['board_id']} [{record['record_status']}] {record['board']}")
    print(f"matched={len(records)}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    return _print(load_records(root))


def cmd_with(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    wanted = args.formats
    unknown = [name for name in wanted if name not in FILE_FORMATS]
    if unknown:
        print(f"error: unknown format(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    matched = [
        record
        for record in load_records(root)
        if all(has_format(record, name) for name in wanted)
    ]
    return _print(matched)


def cmd_commercial(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    matched = [
        record
        for record in load_records(root)
        if record.get("licenses", {}).get("modification_allowed") is True
        and record.get("licenses", {}).get("commercial_use_allowed") is True
    ]
    return _print(matched)


def cmd_mechanical(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    matched = [
        record
        for record in load_records(root)
        if has_format(record, "step") or has_format(record, "mechanical")
    ]
    return _print(matched)


def cmd_open_electrical(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    matched = [
        record
        for record in load_records(root)
        if has_format(record, "schematic")
        and record.get("licenses", {}).get("commercial_use_allowed") is True
    ]
    return _print(matched)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query the dev-board CAD database")
    parser.add_argument("--root", default=str(_repo_root()))
    commands = parser.add_subparsers(dest="command", required=True)

    list_cmd = commands.add_parser("list", help="list all board records")
    list_cmd.set_defaults(handler=cmd_list)

    with_cmd = commands.add_parser(
        "with-formats", help="boards with every named format verified present"
    )
    with_cmd.add_argument("formats", nargs="+", help="format names from FILE_FORMATS")
    with_cmd.set_defaults(handler=cmd_with)

    full = commands.add_parser(
        "full-stack",
        help="boards with schematic + pcb_source + gerbers + bom + step verified",
    )
    full.set_defaults(
        handler=lambda args: cmd_with(
            argparse.Namespace(
                root=args.root,
                formats=["schematic", "pcb_source", "gerbers", "bom", "step"],
            )
        )
    )
    commercial = commands.add_parser(
        "commercial-reuse",
        help="boards verified modifiable and commercially reusable",
    )
    commercial.set_defaults(handler=cmd_commercial)

    mechanical = commands.add_parser(
        "mechanical", help="boards with STEP or mechanical CAD verified"
    )
    mechanical.set_defaults(handler=cmd_mechanical)

    electrical = commands.add_parser(
        "open-electrical",
        help="boards with open schematics and commercial reuse verified",
    )
    electrical.set_defaults(handler=cmd_open_electrical)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
