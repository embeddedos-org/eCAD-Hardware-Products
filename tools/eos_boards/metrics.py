"""Fabrication numbers of a built board, read from its own files; no KiCad needed (MIT, part of the generator).

    python3 tools/eos_boards/metrics.py boards/eos/eos-motion-wing            # print them as JSON
    python3 tools/eos_boards/metrics.py boards/eos/eos-motion-wing --write    # and write metrics.json there

A build writes ``metrics.json`` into the board folder from ``hardware/<name>.kicad_pcb``,
``fab/<name>-bom.csv`` and ``build-report.json``: board size and copper layers, the stack-up, parts by
side, pads, nets, track length per layer, the track widths used and where the narrowest run, vias by
size and drill, the smallest drilled hole, plated slots, pours, the BOM's lines, parts and MPN
coverage, test points and fiducials. ``fab_problems`` names what a fab would reject: a missing or
mismatched stack-up, or a side with surface-mount parts and fewer than three fiducials.

Started from the campaign's scripts/board_metrics.py (24 Oct 2026), which read the same files.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

if __package__ in (None, ""):                      # run as a script: python3 tools/eos_boards/metrics.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from eos_boards import fabrication             # noqa: E402
    from eos_boards.sexpr import find, find_all, loads  # noqa: E402
else:
    from . import fabrication
    from .sexpr import find, find_all, loads

NARROWEST_LISTED = 20       # segments of the narrowest width listed by position; the rest are counted


def _val(node, key, i=1):
    n = find(node, key)
    return n[i] if n is not None and len(n) > i else None


def _r(x, nd=4):
    return round(float(x), nd)


def _net(item):
    n = find(item, "net")
    return str(n[-1]) if n is not None and len(n) > 1 else ""


def _ref(fp):
    return next((str(p[2]) for p in find_all(fp, "property") if str(p[1]) == "Reference"), "")


def _outline(pcb):
    xs, ys = [], []
    for kind in ("gr_line", "gr_arc", "gr_rect", "gr_circle", "gr_poly"):
        for g in find_all(pcb, kind):
            if str(_val(g, "layer")) != "Edge.Cuts":
                continue
            for key in ("start", "end", "mid", "center"):
                p = find(g, key)
                if p is not None:
                    xs.append(float(p[1]))
                    ys.append(float(p[2]))
            pts = find(g, "pts")
            for xy in find_all(pts, "xy") if pts is not None else []:
                xs.append(float(xy[1]))
                ys.append(float(xy[2]))
    return (min(xs), min(ys), max(xs), max(ys)) if xs else (0.0, 0.0, 0.0, 0.0)


def stackup(pcb) -> Dict[str, Any]:
    """The board file's stack-up: its rows, total thickness and finish; {} when it has none."""
    st = find(find(pcb, "setup"), "stackup")
    if st is None:
        return {}
    rows = []
    for layer in find_all(st, "layer"):
        row = {"name": str(layer[1]), "type": str(_val(layer, "type"))}
        for key in ("thickness", "epsilon_r"):
            if find(layer, key) is not None:
                row[key] = _r(_val(layer, key))
        if find(layer, "material") is not None:
            row["material"] = str(_val(layer, "material"))
        rows.append(row)
    copper = [r["name"] for r in rows if r["type"] == "copper"]
    return {"copper": copper, "rows": rows, "finish": str(_val(st, "copper_finish")),
            "thickness_mm": _r(sum(r.get("thickness", 0) for r in rows), 4)}


def _bom(folder: Path, name: str) -> Dict[str, Any]:
    path = folder / "fab" / f"{name}-bom.csv"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    missing = sorted(f"{r['Value']} ({r['Refs']})" for r in rows if not r.get("MPN", "").strip())
    lines, with_mpn = len(rows), len(rows) - len(missing)
    return {"bom_lines": lines, "bom_parts": sum(int(r["Qty"] or 0) for r in rows), "bom_lines_with_mpn": with_mpn,
            "bom_mpn_coverage": round(with_mpn / lines, 3) if lines else None, "bom_lines_without_mpn": missing}


def board_metrics(folder: Path, name: str = "", report: Dict[str, Any] = None) -> Dict[str, Any]:
    """The numbers above for the built board ``name`` in ``folder`` (boards/eos/<name>; the folder's
    name by default). ``report`` is the build's report, read from build-report.json when not given."""
    folder = Path(folder)
    name = name or folder.name
    pcb = loads((folder / "hardware" / f"{name}.kicad_pcb").read_text(encoding="utf-8"))
    x0, y0, x1, y1 = _outline(pcb)
    table = [str(item[1]) for item in find(pcb, "layers")[1:] if isinstance(item, list) and str(item[1]).endswith(".Cu")]

    length, widths, narrow = defaultdict(float), Counter(), []
    for kind in ("segment", "arc"):                # an arc's chord: a lower bound for its length
        for s in find_all(pcb, kind):
            a, b = find(s, "start"), find(s, "end")
            d = math.dist((float(a[1]), float(a[2])), (float(b[1]), float(b[2])))
            w = _r(_val(s, "width"))
            length[str(_val(s, "layer"))] += d
            widths[w] += 1
            narrow.append((w, _net(s), str(_val(s, "layer")), _r(a[1], 3), _r(a[2], 3), _r(b[1], 3), _r(b[2], 3), _r(d, 3)))
    least = min(widths) if widths else None
    at_least = sorted(n for n in narrow if n[0] == least)

    vias = find_all(pcb, "via")
    holes, slots, pads, sides, fids, tps, smd = [], [], Counter(), Counter(), defaultdict(list), [], set()
    fid_flags = []                                  # fiducials not board-only or not excluded from the BOM
    for v in vias:
        holes.append(_r(_val(v, "drill")))
    for fp in find_all(pcb, "footprint"):
        side = "top" if str(_val(fp, "layer")) == "F.Cu" else "bottom"
        sides[side] += 1
        ref = _ref(fp)
        attr = [str(a) for a in find(fp, "attr")[1:]] if find(fp, "attr") is not None else []
        if str(fp[1]) == fabrication.FIDUCIAL_FOOTPRINT:
            at = find(fp, "at")
            fids[side].append([_r(at[1], 3), _r(at[2], 3)])
            missing = [a for a in ("board_only", "exclude_from_bom") if a not in attr]
            if missing:
                fid_flags.append(f"{ref} not {' or '.join(missing)}")
        elif fabrication.carries_smd_parts(
                "dnp" in attr or find(fp, "dnp") is not None, "exclude_from_pos_files" in attr,
                [(str(p[2]) == "smd", any(str(l).endswith(".Paste") for l in find(p, "layers")[1:]))
                 for p in find_all(fp, "pad")]):
            smd.add(side)                          # a side the assembler populates
        if ref.startswith("TP"):
            tps.append(ref)
        for p in find_all(fp, "pad"):
            pads[str(p[2])] += 1
            d = find(p, "drill")
            if d is None or len(d) < 2:
                continue
            nums = [float(x) for x in d[1:] if isinstance(x, (int, float))]
            if not nums:
                continue
            holes.append(_r(min(nums)))
            if "oval" in [str(x) for x in d[1:]] and len(nums) == 2 and nums[0] != nums[1] and str(p[2]) == "thru_hole":
                slots.append({"ref": ref, "pad": str(p[1]), "width_mm": _r(min(nums)), "length_mm": _r(max(nums))})

    nets = set()
    for item in find_all(pcb, "segment") + find_all(pcb, "arc") + vias + [
            p for fp in find_all(pcb, "footprint") for p in find_all(fp, "pad")]:
        n = _net(item)
        if n and not n.startswith("unconnected-"):
            nets.add(n)
    pours, rule_areas = [], Counter()
    for z in find_all(pcb, "zone"):
        if find(z, "keepout") is not None:
            rule_areas[str(_val(z, "name") or "unnamed")] += 1
            continue
        layers = [str(x) for x in find(z, "layers")[1:]] if find(z, "layers") is not None else [str(_val(z, "layer"))]
        pours.append({"net": _net(z) or str(_val(z, "net_name") or ""), "layers": layers})

    m: Dict[str, Any] = {
        "board": name,
        "size_mm": [_r(x1 - x0, 3), _r(y1 - y0, 3)],
        "copper_layers": len(table),
        "stackup": stackup(pcb),
        "footprints": sum(sides.values()), "footprints_by_side": dict(sorted(sides.items())),
        "pads": dict(sorted(pads.items())), "nets": len(nets),
        "track_segments": sum(widths.values()),
        "track_length_mm": {k: _r(v, 1) for k, v in sorted(length.items())},
        "track_length_total_mm": _r(sum(length.values()), 1),
        "track_widths_mm": {f"{w:g}": n for w, n in sorted(widths.items())},
        "narrowest_track_mm": least,
        "narrowest_track_segments": len(at_least),
        "narrowest_track_at": [{"net": n, "layer": l, "start": [ax, ay], "end": [bx, by], "length_mm": d}
                               for _, n, l, ax, ay, bx, by, d in at_least[:NARROWEST_LISTED]],
        "vias": len(vias),
        "vias_by_size_drill_mm": dict(sorted(Counter(f"{_r(_val(v, 'size')):g}/{_r(_val(v, 'drill')):g}" for v in vias).items())),
        "smallest_drill_mm": min(holes) if holes else None,
        "plated_slots": sorted(slots, key=lambda s: (s["ref"], s["pad"])),
        "pours": sorted(pours, key=lambda z: (z["net"], z["layers"])),
        "rule_areas": dict(sorted(rule_areas.items())),
        "test_points": sorted(tps, key=lambda r: (len(r), r)),
        "fiducials": {side: sorted(points) for side, points in sorted(fids.items())},
        "smd_sides": sorted(smd),
        "fiducial_flags": fid_flags,
    }
    m.update(_bom(folder, name))
    if report is None and (folder / "build-report.json").is_file():
        report = json.loads((folder / "build-report.json").read_text(encoding="utf-8"))
    if report:
        m["checks"] = {"erc": report.get("erc_violations"), "drc_errors": report.get("drc_errors"),
                       "drc_warnings": report.get("drc_warnings"), **(report.get("drc") or {})}
    return m


def fab_problems(m: Dict[str, Any], width: float, height: float, corner_radius: float) -> List[str]:
    """What a fab or an assembler would reject in a board's metrics, as sentences ([] when nothing):
    no stack-up or one whose copper is not the board's; a side with surface-mount pads and fewer than
    three fiducials (or two diagonally apart), fiducials too near the edge or in a line, or a fiducial
    that is not a board-only footprint excluded from the BOM."""
    out = list(f"fiducial {f}" for f in m.get("fiducial_flags", []))
    st = m.get("stackup") or {}
    if not st:
        out.append("no stack-up in the board file")
    elif len(st["copper"]) != m["copper_layers"]:
        out.append(f"stack-up has {len(st['copper'])} copper layers, the board {m['copper_layers']}")
    for side in m.get("smd_sides", []):
        problems = fabrication.fiducial_problems([tuple(p) for p in m["fiducials"].get(side, [])],
                                                 width, height, corner_radius, [])
        out += [f"{side}: {p}" for p in problems]
    return out


def write(folder: Path, name: str = "", report: Dict[str, Any] = None) -> Dict[str, Any]:
    """Compute the metrics and write them to <folder>/metrics.json (sorted, LF, UTF-8)."""
    m = board_metrics(folder, name, report)
    Path(folder, "metrics.json").write_text(json.dumps(m, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                                            encoding="utf-8")
    return m


def main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.split("\n\n")[1])
        return 0 if argv else 2
    folder = Path(argv[0])
    m = write(folder) if "--write" in argv else board_metrics(folder)
    print(json.dumps(m, indent=1, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
