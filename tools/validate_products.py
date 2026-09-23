#!/usr/bin/env python3
"""Structural and arithmetic validator for eCAD product design data.

Every product directory in this repository follows one shape: a datasheet, a
bill of materials, a runnable simulation, and trees for CAD and PCB artefacts.
This tool checks that shape and the internal consistency of the data inside it,
so a reviewer who does not trust the author can run one command and read a
verdict.

What this tool proves
---------------------
- The required files and directories exist for every product.
- Every BOM uses the canonical column schema.
- Reference designators are unique within a BOM.
- ``Extended Cost USD == Quantity x Unit Cost USD`` on every line item.
- The stated BOM total equals the sum of the line items.
- Datasheets carry a title, an overview section, a specification section, and
  at least one specification table.
- Simulation scripts are syntactically valid Python, and with ``--run`` they
  execute successfully and print a computed figure.

What this tool does NOT prove
-----------------------------
It checks *internal consistency only*. It cannot tell you whether a manufacturer
part number names a real component, whether that component is in production, or
whether its unit cost resembles a distributor quote today. Those claims need a
distributor API or a datasheet review and remain unverified here. A green run
means the data is self-consistent, not that it is correct about the world.

Rules are derived from what the repository actually does, not from what a
validator author imagines it should do. Each required check below records the
measured adoption that justifies it.

Known deviations
----------------
Products that predate this contract deviate from it. Rather than loosen the
rules and let new data inherit the gap, every deviation is enumerated in
``tools/product_baseline.json`` with a reason. A baselined finding is reported
as ``KNOWN`` and does not fail the run; anything else does. Adding data is
therefore held to the full contract even where older trees are not.

Usage
-----
Validate every division in the repository::

    python3 tools/validate_products.py

Validate specific divisions, executing the simulations as well::

    python3 tools/validate_products.py --run eAerospace_CAD_Design

Show every baselined finding instead of only counting them::

    python3 tools/validate_products.py --show-known

Exit status is ``0`` when no unbaselined finding is reported and ``1``
otherwise, so the tool is usable directly as a CI gate.
"""

from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

import cad_geometry

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_PATH = os.path.join(REPO_ROOT, "tools", "product_baseline.json")

# The column schema used by every product-level bom.csv written against this
# contract. Ordering is part of the contract: downstream tooling reads these by
# index as well as by name. Measured adoption: 41 of 47 product BOMs.
CANONICAL_BOM_COLUMNS = [
    "Reference",
    "Quantity",
    "Value",
    "Footprint",
    "Manufacturer",
    "MPN",
    "Description",
    "Unit Cost USD",
    "Extended Cost USD",
    "Source",
]

# Money is compared with a tolerance rather than exactly. Unit costs are quoted
# to two decimals, so a line item can legitimately round by half a cent and a
# total accumulates that error across every line.
LINE_TOLERANCE_USD = 0.011
TOTAL_TOLERANCE_USD = 0.02

# Files every product directory must contain.
REQUIRED_PRODUCT_FILES = ["product_datasheet.md", "bom.csv"]

# Directories every product directory must contain, even when empty: they mark
# where CAD and PCB artefacts land, and are kept alive by .gitkeep.
REQUIRED_PRODUCT_DIRS = ["hardware/cad", "hardware/pcb", "simulation"]

# Files every division directory must contain.
REQUIRED_DIVISION_FILES = [
    "README.md",
    "docs/business_plan.md",
    "docs/regulatory_path.md",
    "ebuild_simulation/README.md",
]

# The opening descriptive section. Measured adoption: 48 of 48 datasheets carry
# exactly one of these three spellings.
OVERVIEW_HEADING = re.compile(r"^##\s+(Product Overview|Overview|Product Family)\s*$", re.M)

# A specification section. Measured adoption: 48 of 48 datasheets. The heading
# is frequently suffixed with a part number, so the match is deliberately loose.
SPECIFICATION_HEADING = re.compile(r"^##\s+.*Specifications?\b", re.M)

# A revision stamp. Measured adoption: 41 of 48; the 7 without it are the older
# hand-authored trees and are baselined individually.
REVISION_LINE = re.compile(r"\*\*Revision:\*\*\s*v\d+\.\d+")

# A markdown table needs a header row, a delimiter row, and a body row, which
# for the narrowest useful table is twelve pipes. Measured adoption: 48 of 48.
MINIMUM_TABLE_PIPES = 12

# A division is any top-level directory matching this pattern.
DIVISION_PATTERN = re.compile(r"^e[A-Za-z0-9]+_CAD_Design$")

# Sub-directories of a division that hold documentation rather than a product.
NON_PRODUCT_DIRS = {"docs", "ebuild_simulation", "3d_models", "app_architecture"}


@dataclass
class Result:
    """Findings for one validated target.

    Attributes:
        target: Repository-relative path of the product or division checked.
        failures: Unbaselined defects. Each is a one-line message. Any entry
            here fails the run.
        known: Defects matched against the baseline. Reported, but tolerated.
        skips: Checks that could not run, each with the reason why.
    """

    target: str
    failures: list[str] = field(default_factory=list)
    known: list[str] = field(default_factory=list)
    skips: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when nothing unbaselined failed."""
        return not self.failures


def load_baseline(path: str = BASELINE_PATH) -> dict[str, dict[str, str]]:
    """Load the accepted-deviation baseline.

    Args:
        path: Location of the baseline JSON file.

    Returns:
        A mapping of target path to a mapping of finding text to the reason it
        is accepted. An absent file yields an empty baseline, so the validator
        works in a checkout that has not adopted one.

    Raises:
        ValueError: If the file exists but is not valid JSON, since silently
            ignoring a corrupt baseline would hide real failures.

    Example:
        >>> isinstance(load_baseline(), dict)
        True
    """
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"baseline {path} is not valid JSON: {exc}") from exc
    return {
        target: {entry["finding"]: entry["reason"] for entry in entries}
        for target, entries in raw.get("accepted", {}).items()
    }


def _parse_money(raw: str | None) -> float | None:
    """Parse a currency cell into a float, tolerating ``$`` and thousands commas.

    Args:
        raw: The raw cell text, possibly None or empty.

    Returns:
        The parsed amount, or None when the cell is empty or holds no number,
        so callers can distinguish "absent" from "zero".

    Example:
        >>> _parse_money("$1,312.65")
        1312.65
        >>> _parse_money("") is None
        True
    """
    if raw is None:
        return None
    text = raw.strip().replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _is_blank_row(row: dict[str, str | None]) -> bool:
    """True when every cell in the row is empty or whitespace.

    Args:
        row: A parsed CSV row.

    Returns:
        Whether the row carries no data at all.

    Example:
        >>> _is_blank_row({"a": "", "b": None})
        True
    """
    return all(not (value or "").strip() for value in row.values())


def validate_bom(path: str) -> Result:
    """Validate one bill of materials for schema and arithmetic consistency.

    Checks the column schema, then per line item: a non-empty unique reference,
    a positive integer quantity, a present manufacturer and MPN, parseable
    costs, and extended cost equal to quantity times unit cost. Finally compares
    the stated total against the sum of the line items.

    Two total conventions exist and both are accepted: a row whose Reference is
    ``TOTAL``, and a row whose Description opens with ``TOTAL BOM COST``. Both
    put the figure in the ``Unit Cost USD`` column.

    Args:
        path: Path to a bom.csv.

    Returns:
        A Result naming every defect found. An unreadable or empty file is a
        failure, not an exception.

    Example:
        >>> validate_bom("eAerospace_CAD_Design/avionics/bom.csv").ok
        True
    """
    result = Result(target=path)
    try:
        with open(path, newline="", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        result.failures.append(f"cannot read file: {exc}")
        return result

    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        result.failures.append("BOM contains a header but no rows")
        return result

    columns = list(rows[0].keys())
    if columns != CANONICAL_BOM_COLUMNS:
        missing = [c for c in CANONICAL_BOM_COLUMNS if c not in columns]
        extra = [c for c in columns if c not in CANONICAL_BOM_COLUMNS]
        detail = []
        if missing:
            detail.append(f"missing {missing}")
        if extra:
            detail.append(f"unexpected {extra}")
        if not detail:
            detail.append("columns are out of canonical order")
        result.failures.append("non-canonical BOM schema: " + "; ".join(detail))
        return result

    stated_total: float | None = None
    line_sum = 0.0
    seen_references: dict[str, int] = {}

    for offset, row in enumerate(rows):
        line_no = offset + 2  # +1 for the header, +1 for 1-based numbering
        if _is_blank_row(row):
            continue

        reference = (row["Reference"] or "").strip()
        description = (row["Description"] or "").strip()
        if reference.upper() == "TOTAL" or description.upper().startswith("TOTAL BOM COST"):
            value = _parse_money(row["Unit Cost USD"])
            if value is None:
                value = _parse_money(row["Extended Cost USD"])
            if value is None:
                result.failures.append(
                    f"line {line_no}: TOTAL row carries no parseable figure"
                )
            elif stated_total is not None:
                result.failures.append(f"line {line_no}: BOM states more than one total")
            else:
                stated_total = value
            continue

        # Trailing commercial rows such as "Target MSRP" carry no reference and
        # are not part of the BOM. Skip them rather than failing.
        if not reference:
            if description:
                continue
            result.failures.append(f"line {line_no}: row has no reference designator")
            continue

        if reference in seen_references:
            result.failures.append(
                f"line {line_no}: duplicate reference {reference!r} "
                f"(first seen on line {seen_references[reference]})"
            )
        else:
            seen_references[reference] = line_no

        quantity_raw = (row["Quantity"] or "").strip()
        try:
            quantity = int(quantity_raw)
        except ValueError:
            result.failures.append(
                f"line {line_no} ({reference}): quantity {quantity_raw!r} is not an integer"
            )
            continue
        if quantity <= 0:
            result.failures.append(
                f"line {line_no} ({reference}): quantity {quantity} is not positive"
            )
            continue

        for column in ("Manufacturer", "MPN"):
            if not (row[column] or "").strip():
                result.failures.append(f"line {line_no} ({reference}): {column} is empty")

        unit_cost = _parse_money(row["Unit Cost USD"])
        extended_cost = _parse_money(row["Extended Cost USD"])
        if unit_cost is None:
            result.failures.append(
                f"line {line_no} ({reference}): unit cost "
                f"{(row['Unit Cost USD'] or '').strip()!r} is not a number"
            )
            continue
        if extended_cost is None:
            result.failures.append(
                f"line {line_no} ({reference}): extended cost "
                f"{(row['Extended Cost USD'] or '').strip()!r} is not a number"
            )
            continue

        expected = quantity * unit_cost
        if abs(expected - extended_cost) > LINE_TOLERANCE_USD:
            result.failures.append(
                f"line {line_no} ({reference}): extended cost {extended_cost:.2f} "
                f"!= {quantity} x {unit_cost:.2f} = {expected:.2f}"
            )
        line_sum += extended_cost

    if stated_total is None:
        result.failures.append("BOM has no TOTAL row")
    elif abs(stated_total - line_sum) > TOTAL_TOLERANCE_USD:
        result.failures.append(
            f"stated total {stated_total:.2f} != sum of line items {line_sum:.2f} "
            f"(difference {stated_total - line_sum:+.2f})"
        )

    return result


def validate_datasheet(path: str) -> Result:
    """Validate a product datasheet for its title, sections, and tables.

    Args:
        path: Path to a product_datasheet.md.

    Returns:
        A Result naming every missing element.

    Example:
        >>> validate_datasheet("eAerospace_CAD_Design/avionics/product_datasheet.md").ok
        True
    """
    result = Result(target=path)
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        result.failures.append(f"cannot read file: {exc}")
        return result

    if not re.search(r"^#\s+\S.*$", text, re.MULTILINE):
        result.failures.append("no level-1 title heading")
    if not REVISION_LINE.search(text):
        result.failures.append("no '**Revision:** vX.Y' line")
    if not OVERVIEW_HEADING.search(text):
        result.failures.append(
            "no '## Product Overview', '## Overview' or '## Product Family' section"
        )
    if not SPECIFICATION_HEADING.search(text):
        result.failures.append("no '## ... Specifications' section")
    if text.count("|") < MINIMUM_TABLE_PIPES:
        result.failures.append("datasheet carries no specification table")

    return result


def validate_simulation(path: str, run: bool = False) -> Result:
    """Validate one simulation script.

    Always checks that the file compiles. With ``run=True`` also executes it in
    a subprocess and requires a zero exit status and a printed figure. A script
    that fails on a missing third-party module is reported as a skip rather
    than a failure: that is an environment gap, not a defect in the data.

    Args:
        path: Path to a simulation script.
        run: Execute the script as well as compiling it.

    Returns:
        A Result naming the compile or execution failure, if any.

    Example:
        >>> validate_simulation(
        ...     "eAerospace_CAD_Design/avionics/simulation/power_budget_sim.py"
        ... ).ok
        True
    """
    result = Result(target=path)
    try:
        with tempfile.TemporaryDirectory() as cache_dir:
            py_compile.compile(
                path, cfile=os.path.join(cache_dir, "out.pyc"), doraise=True
            )
    except py_compile.PyCompileError as exc:
        result.failures.append(f"does not compile: {exc.msg.strip()}")
        return result
    except OSError as exc:
        result.failures.append(f"cannot read file: {exc}")
        return result

    if not run:
        result.skips.append("execution not requested (pass --run)")
        return result

    # Some simulations write plots next to themselves, resolving the output
    # directory from __file__. Running a copy in a temporary directory keeps
    # those writes out of the repository: validating must never dirty the
    # working tree, or a validation run becomes indistinguishable from an edit.
    environment = dict(os.environ, MPLBACKEND="Agg")
    try:
        with tempfile.TemporaryDirectory() as workspace:
            sandbox = os.path.join(workspace, "simulation")
            os.makedirs(sandbox)
            shutil.copy2(path, os.path.join(sandbox, os.path.basename(path)))
            completed = subprocess.run(
                [sys.executable, os.path.basename(path)],
                cwd=sandbox,
                capture_output=True,
                text=True,
                timeout=180,
                env=environment,
            )
    except subprocess.TimeoutExpired:
        result.failures.append("execution exceeded the 180s timeout")
        return result
    except OSError as exc:
        result.failures.append(f"cannot execute: {exc}")
        return result

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        module = re.search(r"ModuleNotFoundError: No module named '([^']+)'", stderr)
        if module:
            result.skips.append(
                f"not executed: requires the {module.group(1)!r} module, "
                "which is not installed here"
            )
            return result
        # A simulation that runs to completion and exits non-zero is usually
        # reporting that the design missed one of its own specifications. That
        # reason is on stdout, not stderr, so surface it: "exited 1: no stderr"
        # tells a reader nothing about what actually failed.
        detail = stderr.splitlines()[-1].strip() if stderr.splitlines() else ""
        if not detail:
            spec_lines = [
                line.strip()
                for line in (completed.stdout or "").splitlines()
                if "FAIL" in line.upper()
            ]
            detail = spec_lines[-1] if spec_lines else "no diagnostic output"
        result.failures.append(f"exited {completed.returncode}: {detail}")
        return result

    # Requiring a particular word in the output would be brittle: some scripts
    # report a summed power budget, others a duty-cycled average and a battery
    # life. What every useful simulation has in common is that it prints a
    # computed number, so that is what is checked.
    if not re.search(r"\d", completed.stdout):
        result.failures.append("ran successfully but printed no computed figure")

    return result


def catalog_managed_slugs() -> dict[str, set[str]]:
    """Return the product slugs each division's catalog declares it manages.

    Membership is read from ``tools/catalog/divisions/*.json`` rather than
    inferred from what happens to be on disk. A catalog-managed product must
    carry the full CAD artefact set; a hand-authored product predating the
    catalog is exempted explicitly rather than by accident.

    Returns:
        Mapping of division directory name to the set of slugs it manages.
        An unreadable or absent catalog directory yields an empty mapping,
        which makes every product exempt rather than failing the run.

    Example:
        >>> isinstance(catalog_managed_slugs(), dict)
        True
    """
    managed: dict[str, set[str]] = {}
    pattern = os.path.join(REPO_ROOT, "tools", "catalog", "divisions", "*.json")
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        division = record.get("division")
        if not division:
            continue
        managed.setdefault(division, set()).update(
            product["slug"] for product in record.get("products", []) if "slug" in product
        )
    return managed


def _bom_references(path: str) -> set[str]:
    """Return the reference designators listed in a BOM, excluding the total row.

    Args:
        path: Path to a bom.csv.

    Returns:
        The set of reference designators, empty if the file cannot be read.

    Example:
        >>> isinstance(_bom_references("nonexistent.csv"), set)
        True
    """
    try:
        with open(path, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except OSError:
        return set()
    references = set()
    for row in rows:
        ref = (row.get("Reference") or "").strip()
        if not ref or ref.upper() == "TOTAL":
            continue
        # A BOM line reads "C1-C180"; the board and netlist carry C1 .. C180
        # individually. Expand so the three can be compared as equals.
        references.update(cad_geometry.expand_display_reference(ref))
    return references


def validate_cad(path: str, slug: str, render: bool = False) -> Result:
    """Validate the CAD artefacts for one catalog-managed product.

    Parses the KiCad board with kiutils, the outline with ezdxf, and -- when
    ``render`` is set and OpenSCAD is available -- renders the enclosure to a
    solid. The netlist's component list is cross-checked against the BOM, so
    the two cannot drift apart unnoticed.

    A missing third-party parser is reported as a skip rather than a failure:
    that is an environment gap, not a defect in the data.

    Args:
        path: Path to a product directory.
        slug: The product's catalog slug, used to locate the named files.
        render: Render the enclosure with OpenSCAD as well as reading it.

    Returns:
        A Result naming every defect found.

    Example:
        >>> validate_cad("eAerospace_CAD_Design/flight_control",
        ...              "flight_control").ok
        True
    """
    result = Result(target=path)
    pcb_dir = os.path.join(path, "hardware", "pcb")
    cad_dir = os.path.join(path, "hardware", "cad")

    board_path = os.path.join(pcb_dir, f"{slug}.kicad_pcb")
    net_path = os.path.join(pcb_dir, f"{slug}.net")
    dxf_path = os.path.join(cad_dir, f"{slug}_board_outline.dxf")
    scad_path = os.path.join(cad_dir, f"{slug}_enclosure.scad")

    required = {
        board_path: "KiCad board",
        net_path: "netlist",
        os.path.join(pcb_dir, "stackup.md"): "stackup document",
        os.path.join(pcb_dir, "fabrication_notes.md"): "fabrication notes",
        dxf_path: "DXF board outline",
        scad_path: "enclosure model",
    }
    for target, label in required.items():
        if not os.path.isfile(target):
            result.failures.append(
                f"missing {label} {os.path.relpath(target, path)}"
            )

    # --- KiCad board -------------------------------------------------------
    if os.path.isfile(board_path):
        try:
            from kiutils.board import Board
        except ImportError:
            result.skips.append("kicad board not parsed: kiutils is not installed")
        else:
            try:
                board = Board().from_file(board_path)
            except Exception as exc:  # kiutils raises bare Exception subclasses
                result.failures.append(f"{os.path.basename(board_path)}: kiutils cannot parse it: {exc}")
            else:
                copper = [layer for layer in board.layers if layer.type == "signal"]
                declared = _declared_layer_count(path)
                if declared is not None and len(copper) != declared:
                    result.failures.append(
                        f"{os.path.basename(board_path)}: board has {len(copper)} copper "
                        f"layers but the datasheet declares {declared}"
                    )
                edge_items = [
                    item for item in board.graphicItems
                    if getattr(item, "layer", None) == "Edge.Cuts"
                ]
                if not edge_items:
                    result.failures.append(
                        f"{os.path.basename(board_path)}: no Edge.Cuts outline geometry"
                    )

                # Three-way reconciliation: the board, the netlist and the BOM
                # must name exactly the same parts. Any two agreeing while the
                # third differs is the drift this whole pipeline exists to stop.
                # kiutils exposes footprint properties as a plain dict; older
                # revisions used objects carrying key/value. Handle both so the
                # check does not silently find nothing on a different version.
                board_refs = set()
                for footprint in board.footprints:
                    properties = getattr(footprint, "properties", None)
                    if isinstance(properties, dict):
                        reference = properties.get("Reference")
                        if reference:
                            board_refs.add(reference)
                    else:
                        for prop in properties or []:
                            if getattr(prop, "key", None) == "Reference":
                                board_refs.add(prop.value)
                bom_refs = _bom_references(os.path.join(path, "bom.csv"))
                if not board_refs:
                    result.failures.append(
                        f"{os.path.basename(board_path)}: no placed footprints"
                    )
                elif bom_refs:
                    # Assembly-level items (battery pack, enclosure, the bare
                    # board) are on the BOM but correctly absent from the board.
                    # So the board must be a strict subset, and every BOM part
                    # must be either placed or explicitly counted as excluded --
                    # which stops a part going missing without anyone noticing.
                    phantom = sorted(board_refs - bom_refs)[:8]
                    if phantom:
                        result.failures.append(
                            f"{os.path.basename(board_path)}: placed parts that are "
                            f"not on the BOM: {phantom}"
                        )
                    excluded = _excluded_assembly_count(pcb_dir)
                    if excluded is not None and len(board_refs) + excluded != len(bom_refs):
                        result.failures.append(
                            f"{os.path.basename(board_path)}: {len(bom_refs)} BOM parts "
                            f"but {len(board_refs)} placed + {excluded} excluded as "
                            f"assembly-level; {len(bom_refs) - len(board_refs) - excluded} "
                            "unaccounted for"
                        )

    # --- Placement feasibility --------------------------------------------
    report_path = os.path.join(pcb_dir, "placement_report.md")
    if not os.path.isfile(report_path):
        result.failures.append("missing placement report hardware/pcb/placement_report.md")
    else:
        try:
            with open(report_path, encoding="utf-8") as handle:
                report = handle.read()
        except OSError as exc:
            result.failures.append(f"placement_report.md: cannot read: {exc}")
        else:
            if "DOES NOT FIT" in report:
                unplaced = re.search(r"(\d+) part\(s\) unplaced", report)
                count = unplaced.group(1) if unplaced else "some"
                result.failures.append(
                    f"placement_report.md: {count} component(s) do not fit inside "
                    "the board outline"
                )

    # --- Netlist versus BOM ------------------------------------------------
    if os.path.isfile(net_path):
        try:
            with open(net_path, encoding="utf-8") as handle:
                net_text = handle.read()
        except OSError as exc:
            result.failures.append(f"{os.path.basename(net_path)}: cannot read: {exc}")
        else:
            # Strip quoted strings before counting, so a parenthesis inside a
            # component description is not mistaken for structure.
            outside_strings = re.sub(r'"(?:[^"\\]|\\.)*"', "", net_text)
            opens = outside_strings.count("(")
            closes = outside_strings.count(")")
            if opens != closes:
                result.failures.append(
                    f"{os.path.basename(net_path)}: unbalanced s-expression "
                    f"parentheses ({opens} open, {closes} close)"
                )
            net_refs = set(re.findall(r'\(comp \(ref "([^"]+)"\)', net_text))
            bom_refs = _bom_references(os.path.join(path, "bom.csv"))
            if bom_refs and net_refs != bom_refs:
                missing = sorted(bom_refs - net_refs)
                extra = sorted(net_refs - bom_refs)
                detail = []
                if missing:
                    detail.append(f"absent from netlist: {missing}")
                if extra:
                    detail.append(f"not in BOM: {extra}")
                result.failures.append(
                    f"{os.path.basename(net_path)}: netlist and BOM disagree; "
                    + "; ".join(detail)
                )

    # --- DXF outline -------------------------------------------------------
    if os.path.isfile(dxf_path):
        try:
            import ezdxf
        except ImportError:
            result.skips.append("dxf not parsed: ezdxf is not installed")
        else:
            try:
                document = ezdxf.readfile(dxf_path)
                entities = list(document.modelspace())
            except Exception as exc:
                result.failures.append(
                    f"{os.path.basename(dxf_path)}: ezdxf cannot parse it: {exc}"
                )
            else:
                if not entities:
                    result.failures.append(
                        f"{os.path.basename(dxf_path)}: contains no geometry"
                    )

    # --- Enclosure ---------------------------------------------------------
    if os.path.isfile(scad_path) and render:
        openscad = _find_openscad()
        if not openscad:
            result.skips.append("enclosure not rendered: openscad is not installed")
        else:
            with tempfile.TemporaryDirectory() as workspace:
                output = os.path.join(workspace, "out.stl")
                try:
                    completed = subprocess.run(
                        [openscad, "-o", output, os.path.abspath(scad_path)],
                        capture_output=True,
                        text=True,
                        timeout=180,
                    )
                except (subprocess.TimeoutExpired, OSError) as exc:
                    result.failures.append(
                        f"{os.path.basename(scad_path)}: render failed: {exc}"
                    )
                else:
                    if completed.returncode != 0:
                        stderr = (completed.stderr or "").strip().splitlines()
                        detail = stderr[-1] if stderr else "no stderr"
                        result.failures.append(
                            f"{os.path.basename(scad_path)}: openscad exited "
                            f"{completed.returncode}: {detail}"
                        )
                    elif not os.path.isfile(output) or os.path.getsize(output) < 200:
                        result.failures.append(
                            f"{os.path.basename(scad_path)}: rendered to an empty solid"
                        )

    return result


def _excluded_assembly_count(pcb_dir: str) -> int | None:
    """Read how many BOM parts the placement report excluded as assembly-level.

    Args:
        pcb_dir: Path to a product's ``hardware/pcb`` directory.

    Returns:
        The excluded count, or None when the report is absent or does not
        state one.

    Example:
        >>> _excluded_assembly_count("nonexistent") is None
        True
    """
    report = os.path.join(pcb_dir, "placement_report.md")
    try:
        with open(report, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return None
    match = re.search(r"Assembly-level items excluded \|\s*(\d+)\s*\|", text)
    return int(match.group(1)) if match else None


def _declared_layer_count(path: str) -> int | None:
    """Read the copper layer count a product's datasheet declares.

    Args:
        path: Path to a product directory.

    Returns:
        The declared layer count, or None when it cannot be read.

    Example:
        >>> _declared_layer_count("eAerospace_CAD_Design/flight_control")
        12
    """
    datasheet = os.path.join(path, "product_datasheet.md")
    try:
        with open(datasheet, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return None
    match = re.search(r"^\|\s*\*\*Layers\*\*\s*\|\s*(\d+)\s*\|", text, re.MULTILINE)
    return int(match.group(1)) if match else None


def _find_openscad() -> str | None:
    """Locate an OpenSCAD executable.

    Returns:
        The path to openscad, or None when it is not installed.

    Example:
        >>> _find_openscad() is None or isinstance(_find_openscad(), str)
        True
    """
    found = shutil.which("openscad")
    if found:
        return found
    fallback = os.path.expanduser("~/.local/bin/openscad")
    return fallback if os.path.isfile(fallback) and os.access(fallback, os.X_OK) else None


def validate_product(
    path: str,
    run: bool = False,
    managed: dict[str, set[str]] | None = None,
    render: bool = False,
) -> Result:
    """Validate one product directory end to end.

    Aggregates the structural check with the BOM, datasheet, and simulation
    checks, prefixing nested findings with the file they came from. Every
    Python file under ``simulation/`` is validated, and at least one must exist.

    Args:
        path: Path to a product directory.
        run: Execute simulations as well as compiling them.

    Returns:
        A single Result covering the whole product.

    Example:
        >>> validate_product("eAerospace_CAD_Design/avionics").ok
        True
    """
    result = Result(target=path)
    managed = catalog_managed_slugs() if managed is None else managed

    for relative in REQUIRED_PRODUCT_FILES:
        if not os.path.isfile(os.path.join(path, relative)):
            result.failures.append(f"missing required file {relative}")
    for relative in REQUIRED_PRODUCT_DIRS:
        if not os.path.isdir(os.path.join(path, relative)):
            result.failures.append(f"missing required directory {relative}/")

    for relative, validator in (
        ("bom.csv", validate_bom),
        ("product_datasheet.md", validate_datasheet),
    ):
        full = os.path.join(path, relative)
        if not os.path.exists(full):
            continue
        nested = validator(full)
        result.failures.extend(f"{relative}: {item}" for item in nested.failures)
        result.skips.extend(f"{relative}: {item}" for item in nested.skips)

    scripts = sorted(glob.glob(os.path.join(path, "simulation", "*.py")))
    if os.path.isdir(os.path.join(path, "simulation")) and not scripts:
        result.failures.append("simulation/ contains no Python script")
    for script in scripts:
        nested = validate_simulation(script, run=run)
        label = os.path.relpath(script, path)
        result.failures.extend(f"{label}: {item}" for item in nested.failures)
        result.skips.extend(f"{label}: {item}" for item in nested.skips)

    # CAD artefacts are required only of products a catalog declares it manages.
    # The sixteen hand-authored trees predate the catalog and are exempt, which
    # is stated here rather than inferred from whether files happen to exist.
    division, slug = os.path.split(path.rstrip("/"))
    division = os.path.basename(division)
    if slug in managed.get(division, set()):
        nested = validate_cad(path, slug, render=render)
        result.failures.extend(f"hardware: {item}" for item in nested.failures)
        result.skips.extend(f"hardware: {item}" for item in nested.skips)
    else:
        result.skips.append("hardware: CAD not checked (hand-authored, not catalog-managed)")

    return result


def validate_division(path: str) -> Result:
    """Validate the division-level documentation for one CAD design division.

    Args:
        path: Path to a ``*_CAD_Design`` directory.

    Returns:
        A Result naming any missing division-level document.

    Example:
        >>> validate_division("eAerospace_CAD_Design").ok
        True
    """
    result = Result(target=path)
    for relative in REQUIRED_DIVISION_FILES:
        if not os.path.isfile(os.path.join(path, relative)):
            result.failures.append(f"missing required file {relative}")
    return result


def discover_divisions(root: str = ".") -> list[str]:
    """Return every division directory under ``root``, sorted by name.

    Args:
        root: Directory to scan.

    Returns:
        Paths of directories matching ``e*_CAD_Design``.

    Example:
        >>> "eAerospace_CAD_Design" in discover_divisions()
        True
    """
    return sorted(
        entry
        for entry in os.listdir(root)
        if DIVISION_PATTERN.match(entry) and os.path.isdir(os.path.join(root, entry))
    )


def discover_products(division: str) -> list[str]:
    """Return every product directory inside a division, sorted by name.

    A product directory is any sub-directory that is not documentation and that
    contains a bom.csv. Requiring the BOM keeps hand-authored trees such as
    ``ePAM_CAD_Design/AeroSwift`` from being reported as malformed products when
    they deliberately use a different layout.

    Args:
        division: Path to a division directory.

    Returns:
        Paths of the product directories found.

    Example:
        >>> "eAerospace_CAD_Design/avionics" in discover_products("eAerospace_CAD_Design")
        True
    """
    products = []
    for entry in sorted(os.listdir(division)):
        candidate = os.path.join(division, entry)
        if not os.path.isdir(candidate) or entry in NON_PRODUCT_DIRS:
            continue
        if os.path.isfile(os.path.join(candidate, "bom.csv")):
            products.append(candidate)
    return products


def apply_baseline(result: Result, baseline: dict[str, dict[str, str]]) -> Result:
    """Move baselined findings out of ``failures`` and into ``known``.

    Args:
        result: The result to filter, modified in place.
        baseline: Mapping from load_baseline().

    Returns:
        The same Result, for chaining.

    Example:
        >>> r = Result("x", failures=["boom"])
        >>> apply_baseline(r, {"x": {"boom": "pre-existing"}}).ok
        True
    """
    result.target = result.target.replace("\\", "/")
    accepted = baseline.get(result.target, {})
    if not accepted:
        return result

    def match(finding: str) -> str | None:
        """Return the reason accepting this finding, or None.

        An entry ending in ``*`` matches by prefix. That exists for findings
        whose text carries a measured value that legitimately varies between
        runs -- without it, a flaky finding could never be baselined and would
        have to be silenced by weakening the check instead.
        """
        if finding in accepted:
            return accepted[finding]
        for pattern, reason in accepted.items():
            if pattern.endswith("*") and finding.startswith(pattern[:-1]):
                return reason
        return None

    remaining = []
    for finding in result.failures:
        reason = match(finding)
        if reason is not None:
            result.known.append(f"{finding}  [accepted: {reason}]")
        else:
            remaining.append(finding)
    result.failures = remaining
    return result


def main(argv: list[str] | None = None) -> int:
    """Run the validator over the requested divisions and print a report.

    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.

    Returns:
        ``0`` when every unbaselined check passed, ``1`` otherwise.

    Example:
        >>> main(["eAerospace_CAD_Design", "--quiet"])
        0
    """
    parser = argparse.ArgumentParser(
        description="Validate eCAD product design data for structural and arithmetic consistency."
    )
    parser.add_argument(
        "divisions",
        nargs="*",
        help="Division directories to check. Defaults to every e*_CAD_Design directory.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute each simulation instead of only compiling it.",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help=(
            "Render every enclosure model with OpenSCAD. Thorough but slow "
            "(minutes for the full tree), so it is separate from --run."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only failures and the summary line.",
    )
    parser.add_argument(
        "--show-known",
        action="store_true",
        help="List every baselined finding instead of only counting them.",
    )
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Ignore the baseline and report every finding as a failure.",
    )
    args = parser.parse_args(argv)

    divisions = [d.rstrip("/") for d in (args.divisions or discover_divisions())]
    missing = [d for d in divisions if not os.path.isdir(d)]
    if missing:
        print(f"error: no such division directory: {', '.join(missing)}", file=sys.stderr)
        return 1

    try:
        baseline = {} if args.no_baseline else load_baseline()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    managed = catalog_managed_slugs()
    results: list[Result] = []
    for division in divisions:
        results.append(validate_division(division))
        results.extend(
            validate_product(p, run=args.run, managed=managed, render=args.render)
            for p in discover_products(division)
        )
    results = [apply_baseline(r, baseline) for r in results]

    failed = [r for r in results if not r.ok]
    known_count = sum(len(r.known) for r in results)

    for result in results:
        if result.ok and args.quiet and not (args.show_known and result.known):
            continue
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.target}")
        for item in result.failures:
            print(f"         - {item}")
        if args.show_known:
            for item in result.known:
                print(f"         K {item}")
        if not args.quiet:
            for item in result.skips:
                print(f"         ~ {item}")

    print(
        f"\n{len(results) - len(failed)}/{len(results)} targets passed "
        f"across {len(divisions)} division(s)."
    )
    if known_count:
        suffix = "" if args.show_known else " (use --show-known to list)"
        print(f"{known_count} baselined finding(s) tolerated{suffix}.")
    if failed:
        print(f"{len(failed)} target(s) FAILED.")
    return 1 if failed else 0


if __name__ == "__main__":
    contract_commands = {"discover", "capabilities", "validate", "verify-bundle"}
    if len(sys.argv) > 1 and sys.argv[1] in contract_commands:
        from ecad_validation.cli import main as contract_main

        sys.exit(contract_main(sys.argv[1:]))
    sys.exit(main())
