"""Build one EmbeddedOS board end to end, from its design file to fabrication outputs.

    python3 tools/eos_boards/build.py eos_learn_rp2350 [--out DIR] [--passes N]

1. Write the schematic and project, and run ``kicad-cli sch erc``: any violation stops the build.
2. Place the board with KiCad's Python (``pcb_build.py place``) and export a Specctra DSN.
3. Route it with Freerouting, headless.
4. Import the routes, refill the ground pours (``pcb_build.py finish``).
5. Run ``kicad-cli pcb drc --schematic-parity``; anything left unconnected goes to
   ``pcb_build.py repair`` and DRC runs again. Any error, unrouted net or schematic mismatch
   that remains stops the build before step 6, so a failed build never overwrites good outputs.
6. Export Gerbers, drill files, placement, BOM, STEP, schematic PDF and SVG, board renders,
   and ``build-report.json`` with every check's result.

Needs KiCad 8 or later (``KICAD_APP`` selects an installation), Java 25 or later
(``JAVA``) and the Freerouting jar (``FREEROUTING_JAR``).
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from eos_boards import fabrication, kicad_env, metrics, schematic  # noqa: E402
from eos_boards.design import (ALL_RIGHTS_RESERVED, BOTTOM_PAD_FIELD, NC, RAIL_LINK_SYMBOL, TESTPOINT_SYMBOL, Board, Part,  # noqa: E402
                               resolve)
from eos_boards.kicad_lib import Library  # noqa: E402
from eos_boards.sexpr import find, find_all  # noqa: E402

RULES = {"track": 0.15, "clearance": 0.15, "via": 0.6, "drill": 0.3, "min_track": 0.1,
         "min_clearance": 0.15, "min_via": 0.5, "min_drill": 0.25, "edge_clearance": 0.3,
         "hole_clearance": 0.25}


def run(cmd: List[str], **kw: Any) -> subprocess.CompletedProcess:
    print("$", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


def pcb_step(mode: str, *args: Any, tail: int = 2000) -> subprocess.CompletedProcess:
    """Run one ``pcb_build.py`` step (place, finish, repair or ripup) with KiCad's Python and stop the
    build if it did not finish. KiCad 10's bindings can crash such a step (exit 139, or -11 from a
    signal); unchecked, a crashed repair or rip-up round would pass for one that found nothing to do,
    and the next DRC round would see the same problems without a word (issue #70)."""
    r = run([kicad_env.python(), HERE / "pcb_build.py", mode, *args])
    print(r.stdout[-tail:], r.stderr[-tail:])
    if r.returncode:
        raise SystemExit(f"pcb_build.py {mode} failed (exit {r.returncode}); see the output above. "
                         "The board file holds what the last finished step saved.")
    return r


def board_net(board: Board, net: str) -> str:
    """The net's name as KiCad gives it: a power symbol's net is global, a label's is local
    to its sheet and gets the sheet path, ``/``."""
    return net if net in board.power_nets else f"/{net}"


GENERIC_FOOTPRINTS = {"EoS_Packages"}   # footprints/generate.py writes them; MIT like the generator
KICAD_LIBRARIES = ("Footprints, symbols and 3D models from KiCad's libraries: CC BY-SA 4.0, with the KiCad "
                   "libraries' exception for designs that use them and files generated from those designs "
                   "(kicad.org/libraries/license)")


def licence_text(board, module=""):
    """The board's licence file: the designer's copyright under the board's licence, then the
    notices that third-party material on the board requires. ``module`` is the design file's
    module, as the build loaded it: an all-rights-reserved licence names that file."""
    credits = list(board.credits)
    heading = "Third-party material on this board, under its own licence:"
    if board.licence == "MIT":
        mit = (HERE.parents[1] / "LICENSE").read_text().split("\n\n", 2)[2]   # the permission text, after the title and copyright
        text = f"MIT License\n\nCopyright (c) {board.date[:4]} {board.company}\n\n{mit}"
    elif board.licence == ALL_RIGHTS_RESERVED:
        if not board.contact.strip() or not board.licence_terms or not module:
            raise SystemExit(f"{board.name}: an all-rights-reserved board needs a contact, its licence terms and its "
                             "design file, or no one can tell what is reserved or whom to ask")
        # the owner's own footprint libraries; a library with a .LICENSE.txt is third-party and listed below
        libraries = "".join(f"- tools/eos_boards/footprints/{name}.pretty, a footprint library drawn\n"
                            f"  for these boards (see {name}.NOTICE.txt);\n" for name in board.local_footprints
                            if not (HERE / "footprints" / f"{name}.LICENSE.txt").exists()
                            and name not in GENERIC_FOOTPRINTS)
        # The terms are the owner's, not the generator's: each closed board names its own file.
        text = (HERE / board.licence_terms).read_text(encoding="utf-8").format(
            year=board.date[:4], owner=board.company, contact=board.contact.strip(), title=board.title,
            revision=board.revision, name=board.name, module=module, libraries=libraries)
        ours = sorted({p.lib_id.split(":", 1)[0] for p in board.parts} & {s.stem for s in (HERE / "symbols").glob("*.kicad_sym")})
        if ours:   # copied into hardware/symbols by the build: the generator's MIT symbols, not the owner's
            credits.append("Schematic symbols in hardware/symbols (" + ", ".join(f"{s}.kicad_sym" for s in ours)
                           + "): written by this repository's generator, tools/eos_boards/symbols, MIT licence")
        generic = sorted(set(board.local_footprints) & GENERIC_FOOTPRINTS)
        if generic:   # written by footprints/generate.py, part of the MIT generator
            credits.append("Footprint libraries in hardware/footprints (" + ", ".join(f"{g}.pretty" for g in generic)
                           + "): written by this repository's generator, tools/eos_boards/footprints, MIT licence")
        credits.append(KICAD_LIBRARIES)   # the libraries' exception is what lets a design that uses them stay closed
        heading = "Material on this board that this licence does not cover (section 4):"
    else:
        raise SystemExit(f"{board.name}: no licence text for {board.licence!r}")
    if credits:
        text += f"\n{heading}\n\n" + "".join(f"- {c}\n" for c in credits)
        notices = [f"hardware/footprints/{name}.LICENSE.txt" for name in board.local_footprints
                   if (HERE / "footprints" / f"{name}.LICENSE.txt").exists()]
        if notices:
            text += "\nFull notices: " + ", ".join(notices) + "\n"
    return text


def clearance_clashes(drc):
    """The clearance errors between two pieces of routed copper (track or via), from KiCad's DRC
    report, as {net, pos, via, length, other}: the via if one is involved, else the shorter track. That
    is the item to lift and route again (``via`` says which kind it is and ``length`` a track's length
    in mm, so rip-up can tell whether it is locked copper); ``other`` (the same keys) is the item it
    clashes with, which rip-up lifts instead when the first is fixed copper (a locked fan-out via). A
    clash with a pad or a zone is left for the build to fail on."""
    out = []
    for v in drc.get("violations", []):
        items = v.get("items", [])
        if v.get("type") != "clearance" or v.get("severity") != "error" or len(items) != 2:
            continue
        if not all(i["description"].startswith(("Via [", "Track [")) for i in items):
            continue
        def length(i):
            m = re.search(r"length ([0-9.]+) mm", i["description"])
            return float(m.group(1)) if m else 0.0       # a via has no length: lift it first
        item = min(items, key=length)
        other = items[1] if item is items[0] else items[0]
        def named(i):
            return {"net": i["description"].split("[", 1)[1].split("]", 1)[0], "pos": [i["pos"]["x"], i["pos"]["y"]],
                    "via": i["description"].startswith("Via ["), "length": length(i)}
        out.append(dict(named(item), other=named(other)))
    return out


def dangling_via_problems(drc: Dict[str, Any]) -> List[str]:
    """DRC via_dangling findings: a via that joins nothing on one side. KiCad grades them as warnings;
    the build treats them as errors (no committed board has one), since the fan-out's locked vias are
    no longer pruned by the router."""
    return [f"via_dangling: {i['description']}" for v in drc.get("violations", []) if v.get("type") == "via_dangling"
            for i in v.get("items", [])[:1]]


def one_revision(board: Board, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The texts with every other hand-drawn name line, one ending in "rev <letter or number>" (a front
    name line beside the identity line on the back, say), given the board's revision, so the board
    never shows two (PR #74 review). The rest of each line stays as drawn."""
    return [dict(t, text=re.sub(r"\brev [A-Z0-9]+$", f"rev {board.revision}", t["text"]))
            if re.search(r"\brev [A-Z0-9]+$", t["text"]) else t for t in texts]


def identity_texts(board: Board, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The design's silkscreen texts with the board's identity line, "<title>  rev <revision>  <year>",
    beside its ownership line ("(c) <year> <owner>"), on the same layer and mirrored as it is. A design
    line on that layer ending in "rev <letter or number>" (the name line every design drew by hand, of
    any revision) is replaced in place; otherwise the line goes 2 mm above the ownership line. The line
    is marked ``identity``; it and the two ownership lines ("(c) ...", "All rights reserved") are at
    least fabrication.SILK_MIN_TEXT high and marked ``fit``: the placement step moves them (and shortens
    the identity line, fabrication.identity_variants) until they clear every pad, the board edge and any
    silkscreen their design lines did not already touch, or stops the build. A design without an
    ownership line is refused: there is nowhere to put the identity beside it."""
    year = board.date[:4]
    owner = f"(c) {year} {board.company}"
    found = [t for t in texts if t["text"] == owner]
    if len(found) != 1:
        raise SystemExit(f"{board.name}: needs one ownership line {owner!r} in TEXTS (found {len(found)}) to put "
                         "the board's identity beside")
    own = found[0]
    layer = own.get("layer", "F_SilkS")
    variants = fabrication.identity_variants(board.title, board.revision, year)
    old = [t for t in texts if t.get("layer", "F_SilkS") == layer and re.search(r"\brev [A-Z0-9]+$", t["text"])]
    if len(old) > 1:
        raise SystemExit(f"{board.name}: {len(old)} name lines ending in 'rev <revision>' on {layer}; keep one")
    line = dict(old[0]) if old else {"x": own["x"], "y": round(own["y"] - 2.0, 4), "size": 1.0, "bold": True,
                                     "layer": layer, "mirror": own.get("mirror", False)}
    # the design's own line (text, size) is what its designer checked against the silkscreen round it
    line.update(text=variants[0], identity=True, fit=True, variants=variants,
                design_text=old[0]["text"] if old else "", design_size=line["size"],
                size=max(line["size"], fabrication.SILK_MIN_TEXT))
    out = []
    for t in texts:
        if old and t is old[0]:
            out.append(line)
        elif t.get("layer", "F_SilkS") == layer and t["text"] in (owner, "All rights reserved"):
            # the ownership lines go up to the legible minimum, fitted like the identity line (no shortening)
            out.append(dict(t, fit=True, design_text=t["text"], design_size=t["size"],
                            size=max(t["size"], fabrication.SILK_MIN_TEXT)))
        else:
            out.append(t)
    return out if old else out + [line]


# The shunt a 2.54 mm jumper header ships with (BENCH-READY B3): Samtec SNT-100-BK-G, a 2-position
# 2.54 mm shunt with gold contacts, "Active" at DigiKey (read 24 Oct 2026). Second source (B1, a
# single-source part names a fallback): Sullins QPC02SXGN-RC, 2-position 2.54 mm, gold, open top,
# "Active" at DigiKey (read 29 Oct 2026). On the schematic it is a BOM-only symbol (KiCad's pinless
# Mechanical:Housing, on_board no): a BOM line, no footprint, so the board and its parity check are
# unchanged. Its BOM line says it is loose (the Assembly column), so an assembler matching BOM lines to
# placement rows does not look for it on the board.
SHUNT_FIELDS = {"Manufacturer": "Samtec", "MPN": "SNT-100-BK-G",
                "Assembly": "Loose: supplied with the board, not placed"}
SHUNT_SECOND_SOURCE = "Sullins QPC02SXGN-RC"
SHUNT_SYMBOL = "Mechanical:Housing"
JUMPER_SYMBOLS = ("Jumper:Jumper_2_", "Jumper:Jumper_3_")     # header jumpers, which take a shunt
BOM_FIELDS = ("Reference,Value,Footprint,Manufacturer,MPN,Description,Assembly,${QUANTITY},${DNP}",
              "Refs,Value,Footprint,Manufacturer,MPN,Description,Assembly,Qty,DNP")


def _takes_shunt(part: Part) -> bool:
    """A 2.54 mm pin header: what the generator's 2.54 mm shunt fits."""
    return "PinHeader" in part.footprint and "P2.54mm" in part.footprint


def check_shunts(board: Board) -> None:
    """Refuse a ``shunts`` entry for a part the board does not have, with a count that is not a whole
    number of shunts, or with shunts for anything but a 2.54 mm pin header (0, "none supplied", is
    accepted for any part); and a jumper symbol drawn on a pin header of another pitch that the entry
    does not settle: no 2.54 mm shunt fits it, so the design must say ``shunts={ref: 0}`` and name its
    shunt in the README (PR #74 review: the automatic count skipped the pitch check)."""
    by_ref = {p.ref: p for p in board.parts}
    for ref, n in board.shunts.items():
        if ref not in by_ref:
            raise SystemExit(f"{board.name}: shunts names {ref}, which the board does not have")
        if not isinstance(n, int) or isinstance(n, bool) or n < 0 or (n and not _takes_shunt(by_ref[ref])):
            raise SystemExit(f"{board.name}: shunts {ref}: {n!r}; give a count of 2.54 mm shunts for a 2.54 mm pin header")
    for p in board.parts:
        if p.lib_id.startswith(JUMPER_SYMBOLS) and "PinHeader" in p.footprint and not _takes_shunt(p) \
                and p.ref not in board.shunts:
            raise SystemExit(f"{board.name}: {p.ref} is a jumper on {p.footprint}, which no 2.54 mm shunt fits; "
                             f"give shunts={{{p.ref!r}: 0}} and name its shunt in the README")


def shunt_parts(board: Board) -> List[Part]:
    """The jumper shunts supplied with the board, as BOM-only parts JS1, JS2 ...: one for each
    ``Jumper:Jumper_2_*``/``Jumper_3_*`` symbol drawn on a 2.54 mm pin header, and the number the
    design's ``shunts`` option gives for any other jumper header (a 2 x 2 header taking two, say;
    0 for none)."""
    check_shunts(board)
    count = {}
    for part in board.parts:
        if part.lib_id.startswith(JUMPER_SYMBOLS) and _takes_shunt(part):
            count[part.ref] = 1
    count.update(board.shunts)
    taken = sorted(p.ref for p in board.parts if re.fullmatch(r"JS\d+", p.ref))
    if taken and any(count.values()):
        raise SystemExit(f"{board.name}: {taken} use the JS references the generator gives jumper shunts")
    headers = [ref for ref in sorted(count, key=lambda r: (len(r), r)) if count[ref]]
    description = ("Jumper shunt, 2.54 mm, 2 positions, gold, supplied for "
                   + ", ".join(f"{ref} ({count[ref]})" for ref in headers) + "; where to fit them: the README. "
                   + f"Second source: {SHUNT_SECOND_SOURCE}")
    px, py = board.power_block
    out = []
    for ref in headers:
        for _ in range(count[ref]):
            n = len(out)
            out.append(Part(f"JS{n + 1}", SHUNT_SYMBOL, "Shunt 2.54 mm", "", (round(px + 15.24 * n, 2), round(py + 30.48, 2)),
                            {}, fields=dict(SHUNT_FIELDS, Description=description), on_board=False))
    return out


def generated_silk_problems(drc: Dict[str, Any], texts: List[Dict[str, Any]]) -> List[str]:
    """DRC findings that name silkscreen the generator placed or sized (the identity line and, since
    stage 2, the ownership lines it fits at 1.0 mm) over copper, at the board edge or over other
    silkscreen (PR #74 review: a moved name line could land on the ownership line). KiCad grades them as
    warnings; the build treats them as errors, so a clipped or overprinted board name or ownership
    line never reaches a fab."""
    ours = [t["text"] for t in texts if t.get("identity") or t.get("fit")]
    out = []
    for v in drc.get("violations", []):
        if v.get("type") not in ("silk_over_copper", "silk_edge_clearance", "silk_overlap"):
            continue
        for i in v.get("items", []):
            if any(f"'{text}'" in i.get("description", "") for text in ours):
                out.append(f"{v['type']}: {i['description']}")
    return out


def check_bench(board: Board) -> None:
    """Refuse bench data that does not match the design (BENCH-READY C1, C2, C5, A4, D8): a rail on a
    net no part has; a rail without a test point, or a test point that is not a test pad or connector pin
    on that rail's net (a pin counts only on a connector); a bench test pad on the bottom side with no
    reason given; fewer than two test points on GND; a supply net (``power_nets``) missing from the
    rail list; a rail link that is not a link from that rail to another net; bring-up data without
    rails; pin labels for pins the board does not have; a temperature range that is empty or names a part
    the board does not have. Pins are read from each part's ``nets`` (by number or name), so this runs
    without KiCad's libraries."""
    by_ref = {p.ref: p for p in board.parts}
    nets = {n for p in board.parts for n in p.nets.values() if n != NC}

    def fail(message):
        raise SystemExit(f"{board.name}: {message}")

    def net_at(point):
        ref, _, pad = point.partition(".")
        part = by_ref.get(ref)
        if part is None:
            return None
        if not pad:                                     # a test pad, by its reference
            return part.nets.get("1") if part.lib_id == TESTPOINT_SYMBOL else None
        # a pin a probe or clip can take: a connector's (stage-2 review n4: U1.5 is not a test point)
        return part.nets.get(pad) if part.lib_id.startswith("Connector") else None

    if board.bringup is not None and not board.rails:
        fail("bring-up data needs the rail list (rails)")
    for part in board.parts:            # BENCH-READY C1: test pads on the top side, where the probe goes
        if part.lib_id == TESTPOINT_SYMBOL and not part.in_bom and part.side != "F" \
                and not part.fields.get(BOTTOM_PAD_FIELD, "").strip():
            fail(f"test pad {part.ref} is on the bottom side with no reason; give bench_pad(..., bottom_reason=...)")
    seen = set()
    for rail in board.rails:
        if rail.net not in nets:
            fail(f"rail {rail.net}: no part has that net")
        if rail.net in seen:
            fail(f"rail {rail.net} listed twice")
        seen.add(rail.net)
        if not rail.test_points:
            fail(f"rail {rail.net}: no test point (BENCH-READY C1)")
        for point in rail.test_points:
            if net_at(point) != rail.net:
                fail(f"rail {rail.net}: test point {point} is not a test pad or connector pin on {rail.net}")
        if rail.link:
            link = by_ref.get(rail.link)
            link_nets = set(link.nets.values()) if link else set()
            if link is None or link.lib_id != RAIL_LINK_SYMBOL or rail.net not in link_nets or len(link_nets - {rail.net, NC}) != 1:
                fail(f"rail {rail.net}: link {rail.link} is not a rail link from {rail.net} to one other net")
        elif not rail.link_note and rail.net != "GND":
            fail(f"rail {rail.net}: no link, and no note saying why or how to measure its current (BENCH-READY C2)")
    if board.rails:
        ground = [r for r in board.rails if r.net == "GND"]
        if not ground or len(ground[0].test_points) < 2:
            fail("GND needs at least two test points (BENCH-READY C1: one near the input, one near the main IC)")
        missing = sorted(set(board.power_nets) - seen)
        if missing:
            fail(f"supply nets not in the rail list: {missing}")
    for ref, labels in board.pin_labels.items():
        part = by_ref.get(ref)
        if part is None:
            fail(f"pin labels for {ref}, which the board does not have")
        unknown = sorted(set(labels) - set(part.nets))
        if unknown:
            fail(f"pin labels for {ref} pins {unknown}, which it does not have")
    if board.temperature_range is not None:
        lo, hi, ref, why = board.temperature_range
        if not lo < hi or ref not in by_ref or not why.strip():
            fail(f"temperature_range {board.temperature_range!r}: (min, max, the limiting part, its rating and source)")


BRINGUP_BEGIN = ("<!-- bring-up: written by tools/eos_boards from the design file's rails and bring-up data; "
                 "change those, not this section -->")
BRINGUP_END = "<!-- /bring-up -->"


def _degrees(t: float) -> str:
    return f"{t:g}".replace("-", "\u2212")


def unlabelled_pads(board: Board, labels_skipped: List[str]) -> List[str]:
    """The test pads a build left with no silkscreen label at all (neither the rail name nor the
    reference had room), from its ``labels_skipped`` ("TP5.1 3V3"), in the design's order."""
    skipped = {s.split(".", 1)[0] for s in labels_skipped}
    return [p.ref for p in board.parts if p.lib_id == TESTPOINT_SYMBOL and p.ref in skipped]


def bringup_markdown(board: Board, unlabelled: Sequence[str] = ()) -> str:
    """The README's "Bench bring-up" section (BENCH-READY C5), written from the design's ``rails``,
    ``bringup`` and ``temperature_range``: checks before power, each rail's resistance to GND, first
    power with its current limit and expected idle current, each rail's voltage, rail links, clocks,
    programming, the peripheral tests, and a results table to fill in."""
    b = board.bringup
    out = [BRINGUP_BEGIN, "## Bench bring-up", "",
           "These steps check a built board on the bench, in order; stop at the first that fails. They are written "
           "from the design file. A board is shown to work only by doing them and filling in the results table.", ""]
    if board.temperature_range is not None:
        lo, hi, ref, why = board.temperature_range
        out += [f"Rated operating range: {_degrees(lo)} to {_degrees(hi)} \u00b0C, the narrowest of its parts: "
                f"{ref}, {why}.", ""]
    pads = [p for p in board.parts if p.lib_id == TESTPOINT_SYMBOL and p.pcb]
    if pads:      # where to find them, and each reference keyed to its rail (stage-2 review n3)
        out += ["Test pads (reference, rail, centre in mm from the board's top-left corner, on its "
                + ("top" if all(p.side == "F" for p in pads) else "marked") + " side): "
                + ", ".join(f"{p.ref} {p.value} ({p.nets.get('1', '')}) at ({p.pcb[0]:g}, {p.pcb[1]:g}"
                            + ("" if p.side == "F" else ", bottom") + ")" for p in pads)
                + "."]
        bare = [r for r in unlabelled if any(p.ref == r for p in pads)]
        if len(bare) < len(pads):
            out[-1] += (" On the silkscreen " + ("each" if not bare else "each of the others")
                        + " carries its rail name, or its reference where the name has no room.")
        if bare:     # BENCH-READY C1's label, as a named exception: no room for even the reference
            names = " and ".join([", ".join(bare[:-1]), bare[-1]] if len(bare) > 1 else bare)
            if len(bare) == len(pads):
                out[-1] += (" None of them is labelled on the silkscreen: on this board neither the rail name nor "
                            "the reference fits beside any of them, so this list is how to find them.")
            else:
                out += [f"{names} {'have' if len(bare) > 1 else 'has'} no label: on this board neither the rail name "
                        "nor the reference fits beside the pad, so this list is how to find "
                        f"{'them' if len(bare) > 1 else 'it'}."]
        out += [""]
    polar = [p.ref for p in board.parts if p.on_board and (p.ref[:1] in "UDQ" or "Polarized" in p.lib_id)]
    out += ["### 1. Before power", "",
            "1. Look at the board: the orientation (pin 1 or polarity) of " + (", ".join(polar) if polar else "every polarised part")
            + "; no solder bridges between fine-pitch pins; nothing missing or loose."]
    out += [f"{i}. {step}" for i, step in enumerate(b.before_power, 2)]
    out += ["", "### 2. Resistance to GND, unpowered", "",
            "Meter on resistance, black lead on GND, red lead on each rail's test point. Under 10 \u03a9 is a short: stop.", "",
            "| Rail | Measure at | Expected |", "|---|---|---|"]
    out += [f"| {r.net} | {' or '.join(r.test_points)} | {r.to_gnd} |" for r in board.rails if r.net != "GND"]
    ground = next((r for r in board.rails if r.net == "GND"), None)
    out += ["", f"GND test points: {', '.join(ground.test_points)}." if ground else "", "",
            "### 3. First power", "",
            f"{b.supply}, from a bench supply limited to {b.current_limit_ma:g} mA. Expected current: {b.idle_current} "
            f"({b.idle_source}). Much more than that: switch off and look for the cause.", "",
            "### 4. Rail voltages", "",
            "| Rail | From | Measure at | Nominal | Accept |", "|---|---|---|---|---|"]
    out += [f"| {r.net} | {r.source} | {' or '.join(r.test_points)} | {r.nominal} | {r.tolerance} |"
            for r in board.rails if r.net != "GND"]
    links = [r for r in board.rails if r.net != "GND" and (r.link or r.link_note)]
    if links:
        out += ["", "### 5. Rail links and current", ""]
        for r in links:
            if r.link:
                out.append(f"- {r.net}: {r.link} joins it to its source. To check the rail unloaded or to measure the "
                           f"current into {r.net}, cut {r.link}'s bridge, put an ammeter across its two pads, and bridge it "
                           "again with solder afterwards." + (f" {r.link_note}" if r.link_note else ""))
            else:
                out.append(f"- {r.net}: {r.link_note}")
    out += ["", "### 6. Clocks", "", b.clock, "", "### 7. Programming", "", b.programming, "",
            "### 8. Peripheral tests", "", "| Peripheral | Test | Pass |", "|---|---|---|"]
    out += [f"| {t.peripheral} | {t.test} | {t.passes} |" for t in b.tests]
    out += ["", "### Results", "", "| Step | Measured | Expected | PASS/FAIL |", "|---|---|---|---|",
            "| Before power: orientation, bridges | | as in step 1 | |"]
    out += [f"| {r.net} to GND, unpowered | | {r.to_gnd} | |" for r in board.rails if r.net != "GND"]
    out += [f"| First power, current at {b.current_limit_ma:g} mA limit | | {b.idle_current} | |"]
    out += [f"| {r.net} voltage | | {r.tolerance} | |" for r in board.rails if r.net != "GND"]
    out += ["| Clocks | | as in step 6 | |", "| Programming | | as in step 7 | |"]
    out += [f"| {t.peripheral}: {t.test} | | {t.passes} | |" for t in b.tests]
    out += ["", BRINGUP_END]
    return "\n".join(line for line in out) + "\n"


def update_readme(text: str, section: str) -> str:
    """The README ``text`` with its bring-up section replaced by ``section``; a README without one
    gets it before its "## Rebuild" heading, or at the end."""
    if BRINGUP_BEGIN in text:
        head, rest = text.split(BRINGUP_BEGIN, 1)
        if BRINGUP_END not in rest:
            raise SystemExit("README: bring-up section has no end marker")
        return head + section.rstrip("\n") + rest.split(BRINGUP_END, 1)[1]
    if "\n## Rebuild" in text:
        head, rest = text.split("\n## Rebuild", 1)
        return head.rstrip("\n") + "\n\n" + section + "\n## Rebuild" + rest
    return text.rstrip("\n") + "\n\n" + section


def pin_label_pads(board: Board, lib: Library) -> Dict[str, Dict[str, str]]:
    """``pin_labels`` with every pin (named by number or name) turned into its pad number: a pin with
    stacked pads is labelled at its first."""
    out = {}
    for ref, labels in board.pin_labels.items():
        part = next(p for p in board.parts if p.ref == ref)
        pins = resolve(part, lib)
        out[ref] = {}
        for key, label in labels.items():
            number = key if key in pins else next(n for n, (pin, _) in pins.items() if pin.name == key)
            out[ref][pad_numbers(number)[0]] = label
    return out


def title_block(board: Board) -> Dict[str, Any]:
    """The board file's title block: what the schematic's says (title, date, revision, owner, copyright
    and licence), and for an all-rights-reserved board whom to ask for permission."""
    comments = [f"Copyright (c) {board.date[:4]} {board.company}. Licence: {board.licence}",
                "Generated by tools/eos_boards from the board's design file"]
    if board.licence == ALL_RIGHTS_RESERVED:
        comments.append(f"All rights reserved: see LICENSE.txt; permission from {board.contact.strip()}")
    return {"title": board.title, "date": board.date, "rev": board.revision, "company": board.company,
            "comments": comments}


def check_reference(board, lib, parts):
    """Refuse to build when a part placed from a reference design would have a pad on another net
    than the one the reference copper expects: that copper would short two of our nets."""
    ref = json.loads((HERE / board.reference_copper["file"]).read_text())
    by_ref = {p["ref"]: p for p in parts}
    for name, fp in ref["footprints"].items():
        part = by_ref.get(name)
        if part is None:
            raise SystemExit(f"reference part {name} is not on {board.name}")
        if part["footprint"] != fp["footprint"]:
            raise SystemExit(f"{name}: footprint {part['footprint']} but the reference copper is drawn for {fp['footprint']}")
        ours = {pad: net for pad, net in part["pads"].items()}
        bad = {pad: (ours.get(pad), net) for pad, net in fp["pads"].items() if ours.get(pad) != net}
        if bad:
            raise SystemExit(f"{name}: pads on other nets than the reference copper expects (ours, reference): {bad}")


def kicad_net_text(text: str) -> str:
    """Text as KiCad writes it inside a net name: a slash would read as a sheet path, so KiCad
    spells it {slash}."""
    return text.replace("/", "{slash}")


def unconnected_net(ref: str, pin_name: str, pad: str) -> str:
    """The net KiCad gives a no-connect pin's pad: unconnected-(U4-~{RI}{slash}CLK-Pad1). A pin with
    no name ("" or KiCad's "~") leaves the name out: unconnected-(J2-Pad3)."""
    name = "" if pin_name in ("", "~") else f"-{kicad_net_text(pin_name)}"
    return f"unconnected-({ref}{name}-Pad{pad})"


def pad_numbers(number: str) -> List[str]:
    """The pads one symbol pin lands on. KiCad's stacked notation, "[1,15,38,39]" or "[1-4,7]", puts
    several pads on one pin (a module's ground pins, say); any other number names a single pad."""
    if not (number.startswith("[") and number.endswith("]")):
        return [number]
    out = []
    for item in number[1:-1].split(","):
        first, _, last = item.strip().partition("-")
        if not first or (last and not (first.isdigit() and last.isdigit() and int(first) <= int(last))):
            raise ValueError(f"stacked pin number {number!r}: cannot read {item.strip()!r}")
        out += [str(n) for n in range(int(first), int(last) + 1)] if last else [first]
    return out


def spec_for(board: Board, lib: Library, footprint_dir: Path, texts: List[Dict[str, Any]]) -> Dict[str, Any]:
    check_shunts(board)
    check_bench(board)
    parts, nets = [], set()
    for part in board.parts:
        if not part.in_bom and not part.lib_id.startswith((TESTPOINT_SYMBOL, "Mechanical:")):
            # stage-2 review n4: only a bare test pad or a mechanical item may stay out of the BOM; any
            # other part left out would never be bought
            raise SystemExit(f"{board.name}: {part.ref} ({part.lib_id}) is left out of the BOM (in_bom=False); "
                             f"only a test pad ({TESTPOINT_SYMBOL}) or a Mechanical: symbol may be")
        if not part.on_board:
            if resolve(part, lib):         # a part with pins left off the board would vanish from it silently
                raise SystemExit(f"{board.name}: {part.ref} has pins, so it cannot be a BOM-only part (on_board=False)")
            continue                       # a BOM-only item (a jumper shunt): no footprint
        pads = {}
        for num, (pin, net) in resolve(part, lib).items():
            for pad in pad_numbers(num):
                # KiCad names a no-connect pin's net after the pin, and gives the pad that net.
                pads[pad] = board_net(board, net) if net != NC else unconnected_net(part.ref, pin.name, pad)
        nets.update(pads.values())
        symbol = lib.symbol(part.lib_id)
        fields = {str(p[1]): str(p[2]) for p in find_all(symbol, "property")
                  if str(p[1]) not in ("Reference", "Value", "Footprint", "private")
                  and not str(p[1]).startswith("ki_")}
        fields.update(part.fields)
        flag = find(symbol, "in_bom")
        in_bom = part.in_bom and not (flag is not None and str(flag[1]) == "no")      # as the schematic writes it
        parts.append({"ref": part.ref, "value": part.value, "footprint": part.footprint, "in_bom": in_bom,
                      "test_pad": part.lib_id == TESTPOINT_SYMBOL,
                      "x": part.pcb[0], "y": part.pcb[1], "rot": part.pcb[2], "side": part.side,
                      "pads": pads, "uuid": schematic._u(f"{board.name}/sym/{part.ref}"), "dnp": part.dnp,
                      "fields": fields, "model": list(part.model) if part.model else None})
    for k in board.router_keepouts:
        if len(k) not in (4, 5) or (len(k) == 5 and k[4] not in ("F.Cu", "B.Cu")) or not (k[0] < k[2] and k[1] < k[3]):
            raise SystemExit(f'{board.name}: router keep-out {k!r}: x0 < x1, y0 < y1, then optionally "F.Cu" or "B.Cu"')
    for k in board.pour_keepouts:
        if len(k) != 5 or k[4] not in ("F.Cu", "B.Cu") or not (k[0] < k[2] and k[1] < k[3]):
            raise SystemExit(f'{board.name}: pour keep-out {k!r}: x0 < x1, y0 < y1, then "F.Cu" or "B.Cu"')
    for option in ("ground_vias", "fanout_first"):
        unknown = sorted(set(getattr(board, option)) - {p.ref for p in board.parts})
        if unknown:
            raise SystemExit(f"{board.name}: {option} names parts the board does not have: {unknown}")
    if board.reference_copper:
        check_reference(board, lib, parts)
    rules = dict(RULES)
    if board.layers >= 4:
        rules["min_track"] = 0.09      # standard 4-layer capability; the router necks down at fine-pitch pins
    rules.update(board.rules)
    try:
        stackup = fabrication.stackup_for(board.layers, board.thickness, board.stackup)
    except ValueError as e:
        raise SystemExit(f"{board.name}: {e}")
    for side, points in board.fiducials.items():
        if side not in ("F", "B") or len(points) not in (2, 3) or not all(len(p) == 2 for p in points):
            raise SystemExit(f'{board.name}: fiducials {side!r}: {points!r}; give "F" or "B" and three (x, y) '
                             "positions, or two diagonally opposite ones")
    for r in board.priority_routes:
        try:
            _, width = fabrication.route_options(r)
        except ValueError as e:
            raise SystemExit(f"{board.name}: {e}")
        if width is not None and width < rules["min_track"]:
            raise SystemExit(f"{board.name}: priority route {r!r}: {width} mm is under the board's "
                             f"{rules['min_track']} mm minimum track")
    if board.reference_copper:
        # Reference footprints can carry their own pad clearance (Raspberry Pi's VREG capacitors
        # use 0.125 mm); the floor drops so it applies. Net classes keep 0.15 mm everywhere else.
        rules["min_clearance"] = 0.1
    return {"name": board.name, "width": board.width, "height": board.height, "thickness": board.thickness,
            "corner_radius": board.corner_radius, "layers": board.layers, "rules": rules,
            "netclasses": board.netclasses,
            "net_to_class": {board_net(board, n): c for n, c in board.net_to_class.items()}, "parts": parts,
            "nets": sorted(nets), "footprint_dir": str(footprint_dir),
            "planes": [{"net": board_net(board, n), "layer": layer} for n, layer in board.planes],
            "fanout_avoid": board.fanout_avoid, "no_fanout": board.no_fanout, "fanout_pads": board.fanout_pads,
            "ground_vias": board.ground_vias,
            "fanout_first": board.fanout_first,
            "preroutes": [{"a": list(a), "b": list(b), "width": w} for a, b, w in board.preroutes],
            "reference_copper": ({"file": str(HERE / board.reference_copper["file"]), "origin": list(board.reference_copper["origin"])}
                                 if board.reference_copper else None),
            "local_footprints": {lib: str(HERE / "footprints" / f"{lib}.pretty") for lib in board.local_footprints},
            "router_keepouts": [list(k) for k in board.router_keepouts],
            "copper_keepouts": [list(k) for k in board.copper_keepouts],
            "pour_keepouts": [list(k) for k in board.pour_keepouts],
            "priority_routes": [[list(r[0]), list(r[1]), *r[2:]] for r in board.priority_routes],
            "escape_footprints": board.escape_footprints,
            "maze_via_cost_mm": board.maze_via_cost_mm,
            "zones": [{"net": board_net(board, n), "layers": layers} for n, layers in board.pours], "texts": texts,
            "stackup": stackup, "title_block": title_block(board),
            "fiducials": {side: [list(p) for p in points] for side, points in board.fiducials.items()},
            "pin_labels": pin_label_pads(board, lib)}


ROUTE_ATTEMPTS = 3      # Freerouting runs at most, when the repair rounds leave repairable connections open

# Freerouting 2.4.1 routes a DSN the same way every time (the same board after every pass), and takes
# no seed. A retry therefore changes the auto-router's own costs (its CLI sets any router setting as
# --router.<path>=<value>): run 2 doubles the cost of a via (default 50), run 3 triples the cost of
# ripping up routed copper to start a route (default 100). On EoS Learn RP2350's placement the four
# runs (default, via cost 100, via cost 25, start rip-up 300) wrote four different sessions, and the
# via-cost-100 run left 4 connections open on +3V3 where the default left 5 on +3V3 and /GPIO5
# (campaign folder work/bench-ready-p3/fr-retry/, 29 Oct 2026).
RETRY_SETTINGS = ([], ["--router.scoring.via_costs=100"], ["--router.scoring.start_ripup_costs=300"])


def freerouting_args(attempt: int) -> List[str]:
    """Freerouting options for run ``attempt`` (0 first): Freerouting's defaults, then RETRY_SETTINGS."""
    return list(RETRY_SETTINGS[attempt])


def freeroute(dsn: Path, ses: Path, passes: int, attempt: int, work: Path) -> None:
    """One headless Freerouting run, DSN in, session file out; its log in .build/freerouting.log
    (freerouting-2.log, -3 for retries)."""
    java = os.environ.get("JAVA", "/opt/homebrew/opt/openjdk/bin/java")
    jar = os.environ.get("FREEROUTING_JAR", str(Path.home() / "Desktop/task/tools/freerouting/freerouting-2.4.1.jar"))
    if ses.exists():
        ses.unlink()                       # never import an earlier run's session
    r = run([java, "-Djava.awt.headless=true", "-jar", jar, "-de", dsn, "-do", ses, "-mp", passes,
             *freerouting_args(attempt), "--gui.enabled=false"], timeout=3600)
    (work / ("freerouting.log" if attempt == 0 else f"freerouting-{attempt + 1}.log")).write_text(r.stdout + r.stderr)
    if not ses.is_file():
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit("Freerouting produced no session file")


def kicad_check(cmd: List[Any], report: Path) -> Dict[str, Any]:
    """Run a kicad-cli check (ERC or DRC) that writes a JSON report, and read it. The old report is
    deleted first and the exit code checked: a kicad-cli that crashed before writing would otherwise
    leave the last good build's clean report in place, and the build would pass its gate unchecked."""
    report.unlink(missing_ok=True)
    r = run([*cmd[:-1], "-o", report, cmd[-1]])          # the input file last
    if r.returncode or not report.is_file():
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit(f"{' '.join(str(c) for c in cmd[1:3])} failed (exit {r.returncode}"
                         f"{'' if report.is_file() else ', no report written'}); the board was not checked")
    return json.loads(report.read_text())


def run_drc(cli: str, pcb: Path, out: Path) -> Dict[str, Any]:
    """KiCad's DRC with schematic parity, every severity, as JSON (also left in out/drc.json)."""
    return kicad_check([cli, "pcb", "drc", "--schematic-parity", "--format", "json", "--severity-all", pcb], out / "drc.json")


def repairable_opens(drc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The open connections the repair step works on: two located items, neither a zone. A zone island
    left unconnected is not a routing gap; no repair or new route closes it."""
    pairs = []
    for u in drc.get("unconnected_items", []):
        items = u.get("items", [])
        if len(items) == 2 and all("pos" in i for i in items) \
                and not any(i["description"].startswith("Zone") for i in items):
            net = items[0]["description"].split("[", 1)[-1].split("]", 1)[0]
            pairs.append({"net": net, "a": [items[0]["pos"]["x"], items[0]["pos"]["y"]],
                          "b": [items[1]["pos"]["x"], items[1]["pos"]["y"]]})
    return pairs


def check_and_repair(cli: str, spec: Path, pcb: Path, work: Path, out: Path):
    """DRC; close what the autorouter left open (repair) or lift what it left too close (ripup), and
    check again, up to six rounds. Returns (the last DRC report, the rounds run)."""
    for attempt in range(6):
        drc = run_drc(cli, pcb, out)
        pairs = repairable_opens(drc)
        clashes = clearance_clashes(drc)
        if not (pairs or clashes) or attempt == 5:
            break
        if clashes:
            # the autorouter can leave a via or track inside another net's clearance: lift that
            # net's copper there, so this round's DRC lists it as open and the repair re-routes it
            (work / "clashes.json").write_text(json.dumps(clashes, indent=1))
            pcb_step("ripup", spec, pcb, work / "clashes.json", tail=1500)
            continue
        (work / "open.json").write_text(json.dumps(pairs, indent=1))
        pcb_step("repair", spec, pcb, work / "open.json", tail=1500)
    return drc, attempt


def route(cli: str, spec: Path, pcb: Path, dsn: Path, ses: Path, work: Path, out: Path, passes: int,
          attempts: int = ROUTE_ATTEMPTS):
    """Route with Freerouting, finish, then DRC and repair. When the repair rounds still leave
    anything unconnected, start again from the placed board with Freerouting's costs changed
    (RETRY_SETTINGS), up to ``attempts`` runs, and keep the run that left the fewest connections open
    (the earliest on a tie). A pour island counts: a route can cut a pad's patch of pour off from the
    rest (EoS Feather RP2040, stage 2: J6.2's 1 x 2 mm of top ground, too small for a via), and another
    route may not. Returns (its DRC report, its repair rounds, the runs made, the run kept, 1 first)."""
    placed, kept = work / "placed.kicad_pcb", work / "best-routed.kicad_pcb"
    shutil.copyfile(pcb, placed)
    best = None
    for attempt in range(attempts):
        if attempt:
            shutil.copyfile(placed, pcb)
            print(f"routing again, run {attempt + 1} of {attempts} ({' '.join(freerouting_args(attempt))}): "
                  f"{len(drc.get('unconnected_items', []))} connection(s) were still open, "
                  f"{len(repairable_opens(drc))} of them repairable", flush=True)
        freeroute(dsn, ses, passes, attempt, work)
        pcb_step("finish", spec, pcb, ses)
        drc, rounds = check_and_repair(cli, spec, pcb, work, out)
        opens = len(drc.get("unconnected_items", []))
        if best is None or opens < best[0]:
            best = (opens, attempt, drc, rounds)
            shutil.copyfile(pcb, kept)
            shutil.copyfile(ses, work / "best-routed.ses")
        if not opens:
            break
    runs = attempt + 1
    if best[1] != attempt:                 # an earlier run did better: its board and session, checked again
        shutil.copyfile(kept, pcb)
        shutil.copyfile(work / "best-routed.ses", ses)    # .build/<name>.ses must be the kept board's (review n2)
        print(f"keeping run {best[1] + 1}: {best[0]} connection(s) open, against {opens} in run {runs}", flush=True)
        drc = run_drc(cli, pcb, out)
    return drc, best[3], runs, best[1] + 1


def project_file(name: str) -> str:
    return json.dumps({"meta": {"filename": f"{name}.kicad_pro", "version": 1},
                       "board": {"design_settings": {}}, "schematic": {}}, indent=2) + "\n"


def violations(report: Path) -> List[Dict[str, Any]]:
    data = json.loads(report.read_text())
    items = [v for sheet in data.get("sheets", []) for v in sheet.get("violations", [])]
    items += data.get("violations", []) + data.get("unconnected_items", []) + data.get("schematic_parity", [])
    return items


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("board")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--passes", type=int, default=60)
    ap.add_argument("--place-only", action="store_true",
                    help="stop after placement and report overlaps, for iterating on the floorplan")
    args = ap.parse_args()

    module = importlib.import_module(f"eos_boards.boards.{args.board}")
    board: Board = module.BOARD
    texts = one_revision(board, identity_texts(board, getattr(module, "TEXTS", [])))
    lib = Library(kicad_env.symbols(), (HERE / "symbols",))
    out = args.out or HERE.parents[1] / "boards" / "eos" / board.name
    hw, fab, img = out / "hardware", out / "fab", out / "images"
    for d in (hw, fab, img):
        d.mkdir(parents=True, exist_ok=True)
    cli = kicad_env.cli()
    report: Dict[str, Any] = {"board": board.name, "kicad": run([cli, "version"]).stdout.strip()}

    # 1. schematic + ERC
    sch, pcb = hw / f"{board.name}.kicad_sch", hw / f"{board.name}.kicad_pcb"
    board.parts = board.parts + shunt_parts(board)      # BOM lines for the jumper shunts (BENCH-READY B3)
    sch.write_text(schematic.write(board, lib))
    (hw / f"{board.name}.kicad_pro").write_text(project_file(board.name))
    (out / "LICENSE.txt").write_text(licence_text(board, args.board))
    local_syms = sorted({part.lib_id.split(":", 1)[0] for part in board.parts if lib.is_local(part.lib_id.split(":", 1)[0])})
    if local_syms:
        # ship the project's own symbol libraries beside it, with a project library table
        (hw / "symbols").mkdir(exist_ok=True)
        rows = []
        for name in local_syms:
            shutil.copy(lib.path(name), hw / "symbols" / f"{name}.kicad_sym")
            rows.append(f'  (lib (name "{name}") (type "KiCad") (uri "${{KIPRJMOD}}/symbols/{name}.kicad_sym") (options "") (descr ""))')
        (hw / "sym-lib-table").write_text("(sym_lib_table\n  (version 7)\n" + "\n".join(rows) + "\n)\n")
    if board.local_footprints:
        # ship the project's own footprint libraries beside it, with a project library table
        rows = []
        for name in board.local_footprints:
            src = HERE / "footprints" / f"{name}.pretty"
            dst = hw / "footprints" / f"{name}.pretty"
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            licence = HERE / "footprints" / f"{name}.LICENSE.txt"
            if licence.exists():
                shutil.copy(licence, hw / "footprints" / licence.name)
            rows.append(f'  (lib (name "{name}") (type "KiCad") (uri "${{KIPRJMOD}}/footprints/{name}.pretty") (options "") (descr ""))')
        (hw / "fp-lib-table").write_text("(fp_lib_table\n  (version 7)\n" + "\n".join(rows) + "\n)\n")
    kicad_check([cli, "sch", "erc", "--format", "json", "--severity-all", sch], out / "erc.json")
    erc = violations(out / "erc.json")
    report["erc_violations"] = len(erc)
    if erc:
        print(json.dumps(erc[:10], indent=1))
        raise SystemExit(f"ERC: {len(erc)} violation(s); see {out / 'erc.json'}")

    # 2-4. place, route, finish
    work = out / ".build"
    work.mkdir(exist_ok=True)
    spec = work / "spec.json"
    spec.write_text(json.dumps(spec_for(board, lib, kicad_env.footprints(), texts), indent=1))
    dsn, ses = work / f"{board.name}.dsn", work / f"{board.name}.ses"
    pcb_step("place", spec, pcb, dsn)
    placed = kicad_check([cli, "pcb", "drc", "--format", "json", "--severity-error", pcb], work / "place-drc.json")
    placed_spec = json.loads(spec.read_text())       # place records its fiducials, and why a side has two
    report["fiducials"] = placed_spec.get("fiducials_placed", [])
    report["fiducial_notes"] = placed_spec.get("fiducial_notes", {})
    report["identity_line"] = placed_spec.get("identity_fit", "")
    report["silk_fits"] = placed_spec.get("silk_fits", [])
    report["labels_placed"] = placed_spec.get("labels_placed", 0)
    report["labels_skipped"] = placed_spec.get("labels_skipped", [])
    report["labels_on_back"] = placed_spec.get("labels_on_back", [])
    report["labels_as_ref"] = placed_spec.get("labels_as_ref", [])
    for t in texts:                        # the identity line as placed (it may have been shortened)
        if t.get("identity") and placed_spec.get("identity_text"):
            t["text"] = placed_spec["identity_text"]
    if board.reference_copper:
        # nets the reference copper completes on its own, which the router must leave alone
        ref = json.loads((HERE / board.reference_copper["file"]).read_text())
        ref_nets = {i["net"] for key in ("tracks", "vias", "zones") for i in ref[key]}
        open_nets = {i["description"].split("[", 1)[-1].split("]", 1)[0]
                     for u in placed.get("unconnected_items", []) for i in u.get("items", [])}
        data = json.loads(spec.read_text())
        plane_nets = {board_net(board, n) for n, _ in board.planes}
        data["complete_nets"] = sorted(ref_nets - open_nets - plane_nets)
        spec.write_text(json.dumps(data, indent=1))
        print(f"complete before routing: {data['complete_nets']}")
    if args.place_only:
        found = [v for v in placed.get("violations", [])
                 if v["type"] in ("courtyards_overlap", "clearance", "shorting_items", "pth_inside_courtyard",
                                  "solder_mask_bridge", "copper_edge_clearance", "hole_clearance")]
        for v in found:
            print(f"  {v['type']}: {[i['description'] for i in v['items']]}")
        print(f"placement: {len(found)} overlap/clearance problem(s)")
        return 1 if found else 0
    drc, rounds, runs, kept = route(cli, spec, pcb, dsn, ses, work, out, args.passes)
    report["repair_rounds"] = rounds
    report["routing_runs"] = runs
    report["routing_run_kept"] = kept
    report["drc"] = {k: len(drc.get(k, [])) for k in ("violations", "unconnected_items", "schematic_parity")}
    report["drc_errors"] = sum(1 for v in drc.get("violations", []) if v.get("severity") == "error")
    report["drc_warnings"] = sum(1 for v in drc.get("violations", []) if v.get("severity") == "warning")
    if report["drc_errors"] or any(report["drc"][k] for k in ("unconnected_items", "schematic_parity")):
        # a failed build must not overwrite fabrication files from a good one
        (work / "build-report.json").write_text(json.dumps(report, indent=1) + "\n")
        print(json.dumps({k: report[k] for k in ("erc_violations", "drc", "drc_errors", "drc_warnings")}, indent=1))
        raise SystemExit(f"DRC failed; fabrication outputs left as they were, hardware/ holds this attempt. "
                         f"See {out / 'drc.json'} and {work / 'build-report.json'}")
    # what a fab or an assembler would reject, read back from the saved board: its stack-up, and three
    # fiducials on each side with surface-mount parts
    problems = metrics.fab_problems(metrics.board_metrics(out, board.name, report), board.width, board.height,
                                    board.corner_radius) + generated_silk_problems(drc, texts) + dangling_via_problems(drc)
    report["fab_problems"] = problems
    if problems:
        (work / "build-report.json").write_text(json.dumps(report, indent=1) + "\n")
        raise SystemExit("fabrication check failed; outputs left as they were: " + "; ".join(problems))

    # 6. outputs
    gerbers = fab / "gerbers"
    if gerbers.exists():
        shutil.rmtree(gerbers)
    gerbers.mkdir()
    # the layers a fab needs, and no others
    copper = ["F.Cu"] + [f"In{i}.Cu" for i in range(1, board.layers - 1)] + ["B.Cu"]
    fab_layers = copper + ["F.Mask", "B.Mask", "F.Paste", "B.Paste", "F.Silkscreen", "B.Silkscreen", "Edge.Cuts"]
    run([cli, "pcb", "export", "gerbers", "--no-protel-ext", "--layers", ",".join(fab_layers), "-o", str(gerbers) + "/", pcb])
    run([cli, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
         "--generate-map", "--map-format", "pdf", "-o", str(gerbers) + "/", pcb])
    run([cli, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
         "-o", fab / f"{board.name}-placement.csv", pcb])
    run([cli, "sch", "export", "bom", "--fields", BOM_FIELDS[0], "--labels", BOM_FIELDS[1], "--group-by", "Value,Footprint,MPN",
         "--exclude-dnp", "-o", fab / f"{board.name}-bom.csv", sch])
    run([cli, "pcb", "export", "step", "--subst-models", "--force", "-o", fab / f"{board.name}.step", pcb])
    run([cli, "sch", "export", "pdf", "-o", out / f"{board.name}-schematic.pdf", sch])
    run([cli, "sch", "export", "svg", "-o", img, sch])
    for side in ("top", "bottom"):
        run([cli, "pcb", "render", "--side", side, "--quality", "high", "--width", "2400", "--height", "1400",
             "--background", "opaque", "-o", img / f"{board.name}-{side}.png", pcb])
    run([cli, "pcb", "render", "--side", "top", "--rotate", "-45,0,30", "--perspective", "--quality", "high",
         "--width", "2400", "--height", "1600", "--background", "opaque", "-o", img / f"{board.name}-iso.png", pcb])
    run([cli, "pcb", "export", "svg", "--layers", "F.Cu,B.Cu,F.SilkS,Edge.Cuts", "--mode-single",
         "--exclude-drawing-sheet", "-o", img / f"{board.name}-copper.svg", pcb])
    metrics.write(out, board.name, report)        # metrics.json: the board's fabrication numbers
    readme = out / "README.md"
    if board.bringup is not None and readme.is_file():      # the bench bring-up section, from the design file
        section = bringup_markdown(board, unlabelled_pads(board, report.get("labels_skipped", [])))
        readme.write_text(update_readme(readme.read_text(encoding="utf-8"), section), encoding="utf-8")
        report["readme_bringup"] = True
    report["outputs"] = sorted(str(p.relative_to(out)) for p in out.rglob("*")
                               if p.is_file() and ".build" not in p.parts)
    (out / "build-report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("erc_violations", "drc", "drc_errors", "drc_warnings")}, indent=1))
    return 0 if report["drc_errors"] == 0 and not any(report["drc"][k] for k in ("unconnected_items", "schematic_parity")) else 1


if __name__ == "__main__":
    sys.exit(main())
