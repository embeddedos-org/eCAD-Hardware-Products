"""Deterministic product discovery and committed-inventory reconciliation."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from .hashing import sha256_json
from .policy import CONTRACT_VERSION

DIVISION_PATTERN = re.compile(r"^e[A-Za-z0-9_-]*_CAD_Design$")
PRODUCT_MARKERS = ("bom.csv", "product_datasheet.md")
NON_PRODUCT_NAMES = {
    "assets",
    "docs",
    "documentation",
    "ebuild_simulation",
    "images",
    "site",
}


@dataclass(frozen=True)
class InventoryEntry:
    product_id: str
    path: str
    division: str
    lifecycle: str


def _candidate_children(parent: Path) -> Iterable[Path]:
    for child in sorted(parent.iterdir(), key=lambda item: item.name.casefold()):
        if not child.is_dir() or child.name in NON_PRODUCT_NAMES:
            continue
        if any((child / marker).is_file() for marker in PRODUCT_MARKERS):
            yield child


def discover_candidate_products(root: Path) -> List[InventoryEntry]:
    """Discover products from all design divisions and future concepts.

    Discovery is intentionally broader than the generated catalogs. Catalogs are
    useful authoring inputs, but they do not cover every hand-authored product.
    """
    entries: List[InventoryEntry] = []
    for division in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if not division.is_dir() or not DIVISION_PATTERN.match(division.name):
            continue
        for product in _candidate_children(division):
            relative = product.relative_to(root).as_posix()
            entries.append(
                InventoryEntry(
                    product_id=f"{division.name}:{product.name}",
                    path=relative,
                    division=division.name,
                    lifecycle="design",
                )
            )

    future = root / "future_designs"
    if future.is_dir():
        for product in _candidate_children(future):
            relative = product.relative_to(root).as_posix()
            entries.append(
                InventoryEntry(
                    product_id=f"future_designs:{product.name}",
                    path=relative,
                    division="future_designs",
                    lifecycle="future_concept",
                )
            )

    ids = [entry.product_id for entry in entries]
    paths = [entry.path for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("product discovery produced duplicate stable IDs")
    if len(paths) != len(set(paths)):
        raise ValueError("product discovery produced duplicate paths")
    return sorted(entries, key=lambda entry: entry.product_id.casefold())


def inventory_document(entries: Iterable[InventoryEntry]) -> Dict[str, object]:
    products = [asdict(entry) for entry in sorted(entries, key=lambda item: item.product_id.casefold())]
    return {
        "contract_version": CONTRACT_VERSION,
        "discovery_policy": "artifact-union-v1",
        "products": products,
    }


def inventory_digest(document: Dict[str, object]) -> str:
    return sha256_json(document)


def load_inventory(path: Path) -> Dict[str, object]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"committed product inventory is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"product inventory is invalid JSON: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("products"), list):
        raise ValueError("product inventory must be an object with a products array")
    return document


def entries_from_document(document: Dict[str, object]) -> List[InventoryEntry]:
    entries = []
    for index, value in enumerate(document.get("products", [])):
        if not isinstance(value, dict):
            raise ValueError(f"inventory product {index} is not an object")
        try:
            entry = InventoryEntry(
                product_id=str(value["product_id"]),
                path=str(value["path"]),
                division=str(value["division"]),
                lifecycle=str(value["lifecycle"]),
            )
        except KeyError as exc:
            raise ValueError(f"inventory product {index} is missing {exc.args[0]}") from exc
        entries.append(entry)
    return entries


def reconcile_inventory(root: Path, document: Dict[str, object]) -> List[str]:
    """Return drift findings between committed inventory and current artifacts."""
    committed = {entry.product_id: entry for entry in entries_from_document(document)}
    discovered = {entry.product_id: entry for entry in discover_candidate_products(root)}
    findings = []
    for product_id in sorted(discovered.keys() - committed.keys()):
        findings.append(f"uncommitted product discovered: {product_id} ({discovered[product_id].path})")
    for product_id in sorted(committed.keys() - discovered.keys()):
        findings.append(f"inventory entry has no matching product artifacts: {product_id}")
    for product_id in sorted(committed.keys() & discovered.keys()):
        if committed[product_id] != discovered[product_id]:
            findings.append(
                f"inventory metadata differs for {product_id}: "
                f"committed={committed[product_id]} discovered={discovered[product_id]}"
            )
    return findings
