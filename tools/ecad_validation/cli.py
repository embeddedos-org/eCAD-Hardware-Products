"""Command-line interface for strict eCAD product validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapters import detect_capabilities
from .discovery import (
    discover_candidate_products,
    entries_from_document,
    inventory_digest,
    inventory_document,
    load_inventory,
    reconcile_inventory,
)
from .engine import validate_repository
from .evidence import verify_bundle, write_bundle
from .hashing import canonical_json_bytes


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _inventory_path(root: Path) -> Path:
    return root / "tools" / "catalog" / "product_inventory.json"


def _cmd_discover(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    document = inventory_document(discover_candidate_products(root))
    if args.write:
        path = _inventory_path(root)
        path.write_bytes(canonical_json_bytes(document) + b"\n")
        print(f"wrote {len(document['products'])} products to {path}")
    else:
        print(json.dumps(document, indent=2, sort_keys=True))
    return 0


def _cmd_capabilities(_args: argparse.Namespace) -> int:
    capabilities = {
        name: {
            "available": capability.available,
            "executable": capability.executable,
            "version": capability.version,
            "reason": capability.reason,
        }
        for name, capability in detect_capabilities().items()
    }
    print(json.dumps(capabilities, indent=2, sort_keys=True))
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    document = load_inventory(_inventory_path(root))
    drift = reconcile_inventory(root, document)
    if drift:
        for finding in drift:
            print(f"inventory error: {finding}", file=sys.stderr)
        return 2
    all_entries = entries_from_document(document)
    entries = all_entries
    if args.product:
        entries = [entry for entry in entries if entry.product_id == args.product]
        if not entries:
            print(f"error: product not found in inventory: {args.product}", file=sys.stderr)
            return 2
    result = validate_repository(
        root,
        entries,
        inventory_sha256=inventory_digest(document),
        inventory_product_ids=[entry.product_id for entry in all_entries],
        render=args.render,
    )
    output = Path(args.output).resolve()
    try:
        bundle = write_bundle(root, output, result)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    summary = result.to_summary()
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"bundle: {bundle}")
    # Evidence mode succeeds when every product executed and receipts are valid,
    # even when products are honestly blocked. Gate mode requires eligibility.
    if not result.selection_complete:
        return 1
    if args.mode == "gate" and len(result.eligible_products) != len(result.products):
        return 1
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    try:
        bundle = verify_bundle(Path(args.bundle).resolve())
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"verified {len(bundle['receipts'])} receipts for "
        f"{bundle.get('source_commit', 'unknown commit')}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evidence-backed eCAD validation")
    parser.add_argument("--root", default=str(_repo_root()), help="eCAD repository root")
    commands = parser.add_subparsers(dest="command", required=True)

    discover = commands.add_parser("discover", help="discover the complete product inventory")
    discover.add_argument("--write", action="store_true", help="write the committed inventory")
    discover.set_defaults(handler=_cmd_discover)

    capabilities = commands.add_parser("capabilities", help="report available validator tools")
    capabilities.set_defaults(handler=_cmd_capabilities)

    validate = commands.add_parser("validate", help="run V0-V4 validation")
    validate.add_argument("--all", action="store_true", help="validate every inventoried product")
    validate.add_argument("--product", help="validate one stable product ID")
    validate.add_argument("--output", required=True, help="evidence bundle output directory")
    validate.add_argument("--mode", choices=("evidence", "gate"), default="evidence")
    validate.add_argument("--render", action="store_true", help="render OpenSCAD enclosures")
    validate.set_defaults(handler=_cmd_validate)

    verify = commands.add_parser("verify-bundle", help="verify receipt and bundle integrity")
    verify.add_argument("bundle", help="path to bundle.json")
    verify.set_defaults(handler=_cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate" and not (args.all or args.product):
        parser.error("validate requires --all or --product")
    if args.command == "validate" and args.all and args.product:
        parser.error("validate accepts only one of --all or --product")
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
