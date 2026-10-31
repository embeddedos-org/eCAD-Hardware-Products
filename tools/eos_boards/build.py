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
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from eos_boards import kicad_env, schematic  # noqa: E402
from eos_boards.design import ALL_RIGHTS_RESERVED, NC, Board, resolve  # noqa: E402
from eos_boards.kicad_lib import Library  # noqa: E402
from eos_boards.sexpr import find, find_all  # noqa: E402

RULES = {"track": 0.15, "clearance": 0.15, "via": 0.6, "drill": 0.3, "min_track": 0.1,
         "min_clearance": 0.15, "min_via": 0.5, "min_drill": 0.25, "edge_clearance": 0.3,
         "hole_clearance": 0.25}
# How far a board may move a reference via to keep it off a pad: a nudge, not a different layout.
MAX_VIA_MOVE = 0.25


def run(cmd: List[str], **kw: Any) -> subprocess.CompletedProcess:
    print("$", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


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
    report, as {net, pos}: the via if one is involved, else the shorter track. That is the item to
    lift and route again. A clash with a pad or a zone is left for the build to fail on."""
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
        out.append({"net": item["description"].split("[", 1)[1].split("]", 1)[0],
                    "pos": [item["pos"]["x"], item["pos"]["y"]]})
    return out


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
    vias = {(round(d["x"], 6), round(d["y"], 6)) for d in ref["vias"]}
    for old, new in board.reference_copper.get("moved_vias", []):
        if (round(old[0], 6), round(old[1], 6)) not in vias:
            raise SystemExit(f"{board.name}: moved via {list(old)} is not a via in the reference copper")
        if math.dist(old, new) > MAX_VIA_MOVE:
            raise SystemExit(f"{board.name}: moved via {list(old)} -> {list(new)} goes more than "
                             f"{MAX_VIA_MOVE} mm from the reference")


def board_rules(board: Board) -> Dict[str, Any]:
    """The design rules the board is built with: the defaults, the board's own, and the floor a
    reference design's pad clearances need."""
    rules = dict(RULES)
    if board.layers >= 4:
        rules["min_track"] = 0.09      # standard 4-layer capability; the router necks down at fine-pitch pins
    rules.update(board.rules)
    if board.reference_copper:
        # Reference footprints can carry their own pad clearance (Raspberry Pi's VREG capacitors
        # use 0.125 mm); the floor drops so it applies. Net classes keep 0.15 mm everywhere else.
        rules["min_clearance"] = 0.1
    return rules


def check_priority_routes(board: Board, rules: Dict[str, Any]) -> None:
    for route in board.priority_routes:
        check_route_options(board.name, route, rules)


def _number(x: Any) -> bool:
    """A finite int or float; bool is an int to Python, but True is not a width."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def check_route_options(name: str, route: tuple, rules: Dict[str, Any]) -> None:
    """Refuse a priority route's options before KiCad starts. After the two pads a route may carry,
    once each: "join"; a track width in mm, at least the board's min_track; and
    {"via": [x, y, diameter, drill]}, within the board's via rules. "join" and a pinned via
    exclude each other."""
    where = f"{name}: priority route {route[:2]}"
    seen = set()
    for extra in route[2:]:
        if isinstance(extra, str) and extra == "join":
            kind = "join"
        elif _number(extra):
            if extra < rules["min_track"]:
                raise SystemExit(f"{where}: width {extra} mm is below the board's min_track "
                                 f"({rules['min_track']} mm)")
            kind = "width"
        elif isinstance(extra, dict):
            via = extra.get("via")
            if set(extra) != {"via"} or not isinstance(via, (list, tuple)) or len(via) != 4 \
                    or not all(_number(n) for n in via):
                raise SystemExit(f"{where}: {extra!r} is not " '{"via": [x, y, diameter, drill]}')
            if via[2] < rules["min_via"] or via[3] < rules["min_drill"] or via[3] >= via[2]:
                raise SystemExit(f"{where}: pinned via {via[2]}/{via[3]} mm is outside the board's via rules "
                                 f"(min via {rules['min_via']} mm, min drill {rules['min_drill']} mm)")
            kind = "via"
        else:
            raise SystemExit(f"{where}: unknown option {extra!r}")
        if kind in seen:
            raise SystemExit(f"{where}: {kind} given twice")
        seen.add(kind)
    if {"join", "via"} <= seen:
        raise SystemExit(f'{where}: "join" and a pinned via together')


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
    parts, nets = [], set()
    for part in board.parts:
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
        in_bom = not (flag is not None and str(flag[1]) == "no")      # as the schematic writes it
        parts.append({"ref": part.ref, "value": part.value, "footprint": part.footprint, "in_bom": in_bom,
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
    rules = board_rules(board)
    check_priority_routes(board, rules)
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
            "reference_copper": ({"file": str(HERE / board.reference_copper["file"]), "origin": list(board.reference_copper["origin"]),
                                  "moved_vias": [[list(a), list(b)] for a, b in board.reference_copper.get("moved_vias", [])]}
                                 if board.reference_copper else None),
            "local_footprints": {lib: str(HERE / "footprints" / f"{lib}.pretty") for lib in board.local_footprints},
            "router_keepouts": [list(k) for k in board.router_keepouts],
            "copper_keepouts": [list(k) for k in board.copper_keepouts],
            "pour_keepouts": [list(k) for k in board.pour_keepouts],
            "priority_routes": [[list(r[0]), list(r[1]), *r[2:]] for r in board.priority_routes],
            "escape_footprints": board.escape_footprints,
            "maze_via_cost_mm": board.maze_via_cost_mm,
            "zones": [{"net": board_net(board, n), "layers": layers} for n, layers in board.pours], "texts": texts}


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
    texts = getattr(module, "TEXTS", [])
    check_priority_routes(board, board_rules(board))      # a mistyped route option stops here, before KiCad runs
    lib = Library(kicad_env.symbols(), (HERE / "symbols",))
    out = args.out or HERE.parents[1] / "boards" / "eos" / board.name
    hw, fab, img = out / "hardware", out / "fab", out / "images"
    for d in (hw, fab, img):
        d.mkdir(parents=True, exist_ok=True)
    cli = kicad_env.cli()
    report: Dict[str, Any] = {"board": board.name, "kicad": run([cli, "version"]).stdout.strip()}

    # 1. schematic + ERC
    sch, pcb = hw / f"{board.name}.kicad_sch", hw / f"{board.name}.kicad_pcb"
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
    run([cli, "sch", "erc", "--format", "json", "--severity-all", "-o", out / "erc.json", sch])
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
    r = run([kicad_env.python(), HERE / "pcb_build.py", "place", spec, pcb, dsn])
    print(r.stdout[-2000:], r.stderr[-2000:])
    if r.returncode:
        raise SystemExit("placement failed")
    run([cli, "pcb", "drc", "--format", "json", "--severity-error", "-o", work / "place-drc.json", pcb])
    placed = json.loads((work / "place-drc.json").read_text())
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
    java = os.environ.get("JAVA", "/opt/homebrew/opt/openjdk/bin/java")
    jar = os.environ.get("FREEROUTING_JAR", str(Path.home() / "Desktop/task/tools/freerouting/freerouting-2.4.1.jar"))
    r = run([java, "-Djava.awt.headless=true", "-jar", jar, "-de", dsn, "-do", ses, "-mp", args.passes,
             "--gui.enabled=false"], timeout=3600)
    (work / "freerouting.log").write_text(r.stdout + r.stderr)
    if not ses.is_file():
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit("Freerouting produced no session file")
    r = run([kicad_env.python(), HERE / "pcb_build.py", "finish", spec, pcb, ses])
    print(r.stdout[-2000:], r.stderr[-2000:])
    if r.returncode:
        raise SystemExit("finishing failed")

    # 5. DRC with schematic parity; close what the autorouter left open, then check again
    for attempt in range(6):
        run([cli, "pcb", "drc", "--schematic-parity", "--format", "json", "--severity-all",
             "-o", out / "drc.json", pcb])
        drc = json.loads((out / "drc.json").read_text())
        pairs = []
        for u in drc.get("unconnected_items", []):
            items = u.get("items", [])
            if len(items) == 2 and all("pos" in i for i in items) \
                    and not any(i["description"].startswith("Zone") for i in items):
                net = items[0]["description"].split("[", 1)[-1].split("]", 1)[0]
                pairs.append({"net": net, "a": [items[0]["pos"]["x"], items[0]["pos"]["y"]],
                              "b": [items[1]["pos"]["x"], items[1]["pos"]["y"]]})
        clashes = clearance_clashes(drc)
        if not (pairs or clashes) or attempt == 5:
            break
        if clashes:
            # the autorouter can leave a via or track inside another net's clearance: lift that
            # net's copper there, so this round's DRC lists it as open and the repair re-routes it
            (work / "clashes.json").write_text(json.dumps(clashes, indent=1))
            r = run([kicad_env.python(), HERE / "pcb_build.py", "ripup", spec, pcb, work / "clashes.json"])
            print(r.stdout[-1500:])
            continue
        (work / "open.json").write_text(json.dumps(pairs, indent=1))
        r = run([kicad_env.python(), HERE / "pcb_build.py", "repair", spec, pcb, work / "open.json"])
        print(r.stdout[-1500:])
    report["repair_rounds"] = attempt
    report["drc"] = {k: len(drc.get(k, [])) for k in ("violations", "unconnected_items", "schematic_parity")}
    report["drc_errors"] = sum(1 for v in drc.get("violations", []) if v.get("severity") == "error")
    report["drc_warnings"] = sum(1 for v in drc.get("violations", []) if v.get("severity") == "warning")
    if report["drc_errors"] or any(report["drc"][k] for k in ("unconnected_items", "schematic_parity")):
        # a failed build must not overwrite fabrication files from a good one
        (work / "build-report.json").write_text(json.dumps(report, indent=1) + "\n")
        print(json.dumps({k: report[k] for k in ("erc_violations", "drc", "drc_errors", "drc_warnings")}, indent=1))
        raise SystemExit(f"DRC failed; fabrication outputs left as they were, hardware/ holds this attempt. "
                         f"See {out / 'drc.json'} and {work / 'build-report.json'}")

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
    run([cli, "sch", "export", "bom", "--fields", "Reference,Value,Footprint,Manufacturer,MPN,Description,${QUANTITY},${DNP}",
         "--labels", "Refs,Value,Footprint,Manufacturer,MPN,Description,Qty,DNP", "--group-by", "Value,Footprint,MPN",
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
    report["outputs"] = sorted(str(p.relative_to(out)) for p in out.rglob("*")
                               if p.is_file() and ".build" not in p.parts)
    (out / "build-report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("erc_violations", "drc", "drc_errors", "drc_warnings")}, indent=1))
    return 0 if report["drc_errors"] == 0 and not any(report["drc"][k] for k in ("unconnected_items", "schematic_parity")) else 1


if __name__ == "__main__":
    sys.exit(main())
