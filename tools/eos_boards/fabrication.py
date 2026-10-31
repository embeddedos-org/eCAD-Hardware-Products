"""What a fab needs written into every board, as data: the layer stack-up (part of the MIT generator).

Pure Python, and Python 3.9 compatible: ``pcb_build.py`` imports this module under KiCad's own
Python, and the unit tests import it as ``eos_boards.fabrication``.

Stack-ups. Each board's ``.kicad_pcb`` carries its layer stack-up: copper weights, dielectric
thicknesses and materials, the dielectric constant of each, the surface finish and the solder-mask
and silkscreen colours. Fabs read it from the board file and from the Gerber job file that KiCad
writes beside the Gerbers. The numbers are JLCPCB's published standard stack-ups for a 1.6 mm board,
read on 24 October 2026:

* 4 layers, JLC04161H-7628 (https://jlcpcb.com/impedance, "JLC04161H-7628 Stackup"): copper
  0.035 mm, prepreg 7628 x 1 0.2104 mm, inner copper 0.0152 mm, core 1.065 mm ("1.1mm H/HOZ with
  copper"), inner copper 0.0152 mm, prepreg 7628 x 1 0.2104 mm, copper 0.035 mm. The same page gives
  the dielectric constants: prepreg 7628 4.4, core 4.6.
* 6 layers, JLC06161H-2116B (same page, read again on 29 October 2026): copper 0.035, prepreg
  2116 x 1 0.1164, inner copper 0.0152, core 0.5, inner copper 0.0152, prepreg 1080 x 2 (0.0764 +
  0.0764), inner copper 0.0152, core 0.5, inner copper 0.0152, prepreg 2116 x 1 0.1164, copper 0.035
  mm; prepreg 2116 er 4.16, 1080 er 3.91, core 4.6. Of JLCPCB's standard six-layer stacks it is the one
  that centres the only six-layer board's pairs: the stage-1 verifier's 2D field solve (validated on TI
  SPMA056 Table 4, with JLCPCB's coated-microstrip mask model; campaign folder, work/bench-ready-p3-
  review/fix1/zsolve/) gives EoS TM4C1294's 0.15 mm Ethernet lines 0.25 mm apart about 100 ohm under
  solder mask and 107 ohm bare (100 ohm +-10 %), and its 0.13 mm device USB pair about 103 ohm under
  mask (90 ohm +-15 %, the top of the band); the thinner JLC06161H-3313 (3313, 0.0994 mm) gives about
  94 ohm, and the earlier default, JLC06161H-7628 (0.2104 mm), well above 110 ohm. Every standard
  JLCPCB six-layer stack has 0.5 oz (0.0152 mm) inner copper.
* 2 layers: JLCPCB's capabilities page (https://jlcpcb.com/capabilities/pcb-capabilities) gives the
  FR-4 dielectric constant "4.5 (2-Layer PCB)", 1 oz finished outer copper (0.035 mm) by default and
  1.6 mm board thickness. It publishes no core thickness for two layers on these pages, so the core
  is derived: 1.51 mm makes the copper, core and both 0.01 mm masks add up to 1.6 mm (KiCad's own
  default for a 1.6 mm two-layer board does the same).
* Solder mask: 0.01 mm ("Solder mask ink thickness >= 10um", capabilities page), green; silkscreen
  white. Surface finish: ENIG by default (BENCH-READY A5 asks for it wherever a pitch is 0.5 mm or
  finer or a part is a QFN, which covers nearly every board here; JLCPCB offers no HASL on six-layer
  boards). The loss tangent is not published on these pages; KiCad writes its own default, 0.02.

JLCPCB's finished thickness tolerance is +-10 % for boards of 1.0 mm and over (capabilities page),
so a stack-up must add up to the board's thickness within that.

A design file can override any of it with ``Board.stackup``: ``{"finish": "HAL lead-free"}``, other
colours, or a whole ``"layers"`` list of copper and dielectric rows for another fab's stack-up.
"""

from __future__ import annotations

import copy

STACKUP_CHECKED = "2026-10-24"
JLCPCB_IMPEDANCE = "https://jlcpcb.com/impedance"
JLCPCB_CAPABILITIES = "https://jlcpcb.com/capabilities/pcb-capabilities"

OUTER_CU = 0.035        # 1 oz finished outer copper
INNER_CU = 0.0152       # 0.5 oz inner copper, as JLCPCB's tables give it
MASK = 0.01             # solder mask, each side
TOLERANCE = 0.10        # finished thickness +-10 %

# Copper finishes as KiCad names them in a stack-up (the board setup's finish list).
FINISHES = ("None", "HAL SnPb", "HAL lead-free", "ENIG", "ENEPIG", "Hard gold", "Immersion tin",
            "Immersion nickel", "Immersion silver", "OSP", "HT_OSP", "User defined")


def _cu(name, thickness):
    return {"type": "copper", "name": name, "thickness": thickness}


def _dielectric(kind, thickness, material, epsilon_r):
    return {"type": kind, "thickness": thickness, "material": material, "epsilon_r": epsilon_r}


def _prepreg_7628(thickness):
    return _dielectric("prepreg", thickness, "FR4 7628", 4.4)


def _core(thickness):
    return _dielectric("core", thickness, "FR4", 4.6)


STACKUPS = {
    2: {"source": f"JLCPCB 2-layer 1.6 mm: FR-4 er 4.5, 1 oz outer copper ({JLCPCB_CAPABILITIES}, read "
                  f"{STACKUP_CHECKED}); core 1.51 mm derived so the stack adds up to 1.6 mm",
        "layers": [_cu("F.Cu", OUTER_CU), _dielectric("core", 1.51, "FR4", 4.5), _cu("B.Cu", OUTER_CU)]},
    4: {"source": f"JLCPCB JLC04161H-7628 ({JLCPCB_IMPEDANCE}, read {STACKUP_CHECKED})",
        "layers": [_cu("F.Cu", OUTER_CU), _prepreg_7628(0.2104), _cu("In1.Cu", INNER_CU), _core(1.065),
                   _cu("In2.Cu", INNER_CU), _prepreg_7628(0.2104), _cu("B.Cu", OUTER_CU)]},
    6: {"source": f"JLCPCB JLC06161H-2116B ({JLCPCB_IMPEDANCE}, read 2026-10-29)",
        "layers": [_cu("F.Cu", OUTER_CU), _dielectric("prepreg", 0.1164, "FR4 2116", 4.16), _cu("In1.Cu", INNER_CU),
                   _core(0.5), _cu("In2.Cu", INNER_CU), _dielectric("prepreg", 0.1528, "FR4 1080 x 2", 3.91),
                   _cu("In3.Cu", INNER_CU), _core(0.5), _cu("In4.Cu", INNER_CU),
                   _dielectric("prepreg", 0.1164, "FR4 2116", 4.16), _cu("B.Cu", OUTER_CU)]},
}
# impedance_controlled: the board asks the fab to hold impedance (USB, Ethernet pairs). KiCad then writes
# each dielectric's er and loss tangent and "ImpedanceControlled" into the Gerber job file; without it the
# job file carries thickness and material only.
DEFAULTS = {"finish": "ENIG", "mask_color": "Green", "silk_color": "White", "mask_thickness": MASK,
            "impedance_controlled": False}


def copper_names(layers):
    """KiCad's copper layer names, top to bottom: F.Cu, In1.Cu ... B.Cu."""
    return ["F.Cu"] + [f"In{i}.Cu" for i in range(1, layers - 1)] + ["B.Cu"]


def stackup_for(layers, thickness, override=None):
    """The stack-up a board of ``layers`` copper layers and ``thickness`` mm gets: JLCPCB's standard
    one for 1.6 mm, with ``override`` (``Board.stackup``) on top. Raises ValueError when there is no
    published stack-up for the board, or when the result is not a valid stack for it.

    >>> [r["name"] for r in stackup_for(4, 1.6)["layers"] if r["type"] == "copper"]
    ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
    """
    override = dict(override or {})
    unknown = sorted(set(override) - {"layers", "source", *DEFAULTS})
    if unknown:
        raise ValueError(f"stack-up: unknown option(s) {unknown}")
    if "layers" in override:
        if not override.get("source"):
            raise ValueError("stack-up: a design's own layer list needs a source (the fab's published stack-up)")
        out = {"source": override["source"], "layers": copy.deepcopy(override["layers"])}
    elif layers in STACKUPS and abs(thickness - 1.6) < 1e-9:
        out = copy.deepcopy(STACKUPS[layers])
    else:
        raise ValueError(f"stack-up: no published standard stack-up for {layers} layers at {thickness} mm; "
                         "give one with the design's stackup option")
    for key, value in DEFAULTS.items():
        out[key] = override.get(key, value)
    if "source" in override and "layers" not in override:
        out["source"] = override["source"]
    check_stackup(out, layers, thickness)
    return out


def check_stackup(stackup, layers, thickness):
    """Refuse a stack-up whose copper is not this board's, top to bottom, with one dielectric between
    each pair of copper layers, or whose total misses the board's thickness by more than the fab's
    tolerance."""
    rows = stackup["layers"]
    copper = [r.get("name") for r in rows if r.get("type") == "copper"]
    if copper != copper_names(layers):
        raise ValueError(f"stack-up: copper layers {copper}, but the board has {copper_names(layers)}")
    kinds = ["copper" if r.get("type") == "copper" else "dielectric" for r in rows]
    if kinds != ["copper", "dielectric"] * (layers - 1) + ["copper"]:
        raise ValueError(f"stack-up: rows must alternate copper and dielectric, top and bottom copper: {kinds}")
    for r in rows:
        if r["type"] not in ("copper", "core", "prepreg"):
            raise ValueError(f"stack-up: row type {r['type']!r}; use copper, core or prepreg")
        if not r.get("thickness", 0) > 0:
            raise ValueError(f"stack-up: row {r} has no thickness")
        if r["type"] != "copper" and not (r.get("material") and r.get("epsilon_r", 0) > 1):
            raise ValueError(f"stack-up: dielectric row {r} needs a material and its epsilon_r")
    if not isinstance(stackup["impedance_controlled"], bool):
        raise ValueError(f"stack-up: impedance_controlled {stackup['impedance_controlled']!r}; give True or False")
    if stackup["finish"] not in FINISHES:
        raise ValueError(f"stack-up: finish {stackup['finish']!r} is not one of KiCad's: {FINISHES}")
    total = stackup_thickness(stackup)
    if abs(total - thickness) > TOLERANCE * thickness:
        raise ValueError(f"stack-up: adds up to {total:.4f} mm, outside {thickness} mm +-{TOLERANCE:.0%}")


def stackup_thickness(stackup):
    """Copper, dielectrics and both solder masks, in mm."""
    return sum(r["thickness"] for r in stackup["layers"]) + 2 * stackup["mask_thickness"]


def _num(value):
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def _q(text):
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def stackup_text(stackup):
    """The board setup's ``(stackup ...)`` node, as KiCad writes it (it reformats the node when it
    next saves the board)."""
    mask = _num(stackup["mask_thickness"])
    lines = ["(stackup",
             f'\t(layer "F.SilkS" (type "Top Silk Screen") (color {_q(stackup["silk_color"])}))',
             '\t(layer "F.Paste" (type "Top Solder Paste"))',
             f'\t(layer "F.Mask" (type "Top Solder Mask") (color {_q(stackup["mask_color"])}) (thickness {mask}))']
    n = 0
    for r in stackup["layers"]:
        if r["type"] == "copper":
            lines.append(f'\t(layer {_q(r["name"])} (type "copper") (thickness {_num(r["thickness"])}))')
        else:
            n += 1
            lines.append(f'\t(layer "dielectric {n}" (type {_q(r["type"])}) (thickness {_num(r["thickness"])}) '
                         f'(material {_q(r["material"])}) (epsilon_r {_num(r["epsilon_r"])}))')
    lines += [f'\t(layer "B.Mask" (type "Bottom Solder Mask") (color {_q(stackup["mask_color"])}) (thickness {mask}))',
              '\t(layer "B.Paste" (type "Bottom Solder Paste"))',
              f'\t(layer "B.SilkS" (type "Bottom Silk Screen") (color {_q(stackup["silk_color"])}))',
              f'\t(copper_finish {_q(stackup["finish"])})',
              f'\t(dielectric_constraints {"yes" if stackup["impedance_controlled"] else "no"})',
              ")"]
    return "\n".join(lines)


def insert_stackup(board_text, stackup):
    """``board_text`` (a saved ``.kicad_pcb``) with ``stackup`` as the first item of its setup.
    KiCad 10's Python does not wrap the board's stack-up object (its BOARD_STACKUP comes back as an
    opaque pointer), so the generator writes the node into the saved file; KiCad keeps it through every
    later load and save."""
    if board_text.count("(setup\n") != 1 or "(stackup" in board_text:
        raise ValueError("expected one (setup and no (stackup in the saved board")
    head, tail = board_text.split("(setup\n", 1)
    indent = tail[:len(tail) - len(tail.lstrip("\t"))]
    block = "\n".join(indent + line for line in stackup_text(stackup).split("\n"))
    return head + "(setup\n" + block + "\n" + tail


# ---- Fiducials (BENCH-READY A2) --------------------------------------------------------------------
# Three global fiducials on every side that the assembler populates, for the placement machine's
# camera: KiCad's Fiducial_1mm_Mask2mm (a 1 mm copper dot in a 2 mm solder-mask opening, which keeps
# 0.6 mm of copper clearance round the dot itself). They are board-only footprints: not in the
# schematic or the BOM, but in the placement file. They sit near three corners, as far apart as the
# free spots allow and not in a line, so the machine can find the board's position, rotation and scale.
# Clearance: IPC-7351B asks for a clear area round the mark, "devoid of any other circuit features or
# markings", of at least twice the mark's radius (as quoted by Tom Hausherr, PCB Libraries forum topic
# 3428, 1 Oct 2024; the standard itself was not read). The copper-free square here keeps other copper
# 1.5 mm from the centre: 1.0 mm beyond the 1 mm dot's edge, outside the 2 mm mask opening.
# Where three do not fit, two diagonally opposite ones (BENCH-READY A2, corrected 29 Oct 2026), and the
# board's README says why.
FIDUCIAL_FOOTPRINT = "Fiducial:Fiducial_1mm_Mask2mm"
FIDUCIAL_MASK_RADIUS = 1.0      # the 2 mm mask opening
FIDUCIAL_EDGE = 3.0             # board edge to the edge of the mask opening, at least (centre >= 4 mm in)
FIDUCIAL_CLEAR = 1.5            # half the copper-free square round each dot: no track, via or pour in it
FIDUCIAL_SPREAD = 5.0           # three: each at least this far from the line through the other two;
                                # two: at least this far apart in x and in y
FIDUCIAL_STEP = 0.25            # search grid, mm
FIDUCIAL_NEAREST = 25           # free spots per corner that the three are chosen from
CORNERS = (("top-left", False, False), ("top-right", True, False), ("bottom-left", False, True),
           ("bottom-right", True, True))


def carries_smd_parts(dnp, excluded_from_pos, pads):
    """True when the assembler places this footprint on its side: it is fitted (not DNP), it is in the
    position file, and it has a surface-mount pad that gets solder paste. ``pads`` are (surface-mount,
    has paste) pairs. A paste-less, unfitted test pad (EoS STM32 64's TP1/TP2) does not count, so its
    side gets no fiducials. The one definition used by the placement step, metrics.py and the tests."""
    return not dnp and not excluded_from_pos and any(smd and paste for smd, paste in pads)


def inside_outline(x, y, width, height, corner_radius, margin):
    """True when (x, y) mm lies inside the rounded-rectangle outline by at least ``margin``."""
    if not (margin <= x <= width - margin and margin <= y <= height - margin):
        return False
    r = corner_radius
    cx = r if x < r else width - r if x > width - r else None
    cy = r if y < r else height - r if y > height - r else None
    if cx is None or cy is None:
        return True
    return r > margin and (x - cx) ** 2 + (y - cy) ** 2 <= (r - margin) ** 2


def fiducial_box(x, y):
    """The copper-free square round a fiducial at (x, y): (x0, y0, x1, y1) mm."""
    return (x - FIDUCIAL_CLEAR, y - FIDUCIAL_CLEAR, x + FIDUCIAL_CLEAR, y + FIDUCIAL_CLEAR)


def _overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _spread(points):
    """The smallest distance from one of three points to the line through the other two."""
    out = float("inf")
    for i in range(3):
        (ax, ay), (bx, by), (px, py) = points[(i + 1) % 3], points[(i + 2) % 3], points[i]
        base = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        out = min(out, abs((bx - ax) * (ay - py) - (ax - px) * (by - ay)) / base if base else 0.0)
    return out


def _diagonal(pair):
    """How diagonal two points are: the smaller of their x and y separations."""
    (ax, ay), (bx, by) = pair
    return min(abs(ax - bx), abs(ay - by))


def _min_distance(points):
    return min(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for i, a in enumerate(points) for b in points[i + 1:])


def fiducial_problems(points, width, height, corner_radius, obstacles):
    """What is wrong with fiducials at ``points`` (mm) on one side, as sentences ([] when nothing):
    fewer than two, two that are not diagonally apart, three in a line, a mask opening within
    FIDUCIAL_EDGE of the board edge, or a copper-free square that meets an obstacle (a courtyard, pad,
    hole, silkscreen text or keep-out on that side, as boxes)."""
    out = []
    if len(points) < 2:
        out.append(f"{len(points)} fiducial(s); three are needed (two diagonally opposite where three do not fit)")
    elif len(points) == 2 and _diagonal(points) < FIDUCIAL_SPREAD:
        out.append(f"two fiducials {list(points)} are not diagonally apart (under {FIDUCIAL_SPREAD} mm in x or y)")
    for x, y in points:
        if not inside_outline(x, y, width, height, corner_radius, FIDUCIAL_EDGE + FIDUCIAL_MASK_RADIUS):
            out.append(f"fiducial at ({x}, {y}): its mask opening is under {FIDUCIAL_EDGE} mm from the board edge")
        hit = [o for o in obstacles if _overlaps(fiducial_box(x, y), o)]
        if hit:
            out.append(f"fiducial at ({x}, {y}): its copper-free square meets {len(hit)} item(s), e.g. {hit[0]}")
    if len(points) >= 3 and _spread(points[:3]) < FIDUCIAL_SPREAD:
        out.append(f"fiducials {points[:3]} are within {FIDUCIAL_SPREAD} mm of a line")
    return out


def choose_fiducials(width, height, corner_radius, obstacles):
    """Fiducial positions (mm) for one side, and a note (empty, or why there are only two).

    Three when they fit: for each corner, the FIDUCIAL_NEAREST free spots nearest to it in its quarter
    of the board (0.25 mm grid), then the trio from three different corners whose closest two are
    furthest apart, each at least FIDUCIAL_SPREAD off the line through the other two. Where fewer than
    three corners have room, two diagonally opposite ones: the free spots nearest to two opposite
    corners, searched over the whole board, at least FIDUCIAL_SPREAD apart in x and in y. ``obstacles``
    are the side's (x0, y0, x1, y1) boxes. Raises ValueError when neither fits: the design then gives
    positions with the ``fiducials`` option.

    >>> choose_fiducials(30.0, 20.0, 1.0, [])
    ([(4.0, 4.0), (26.0, 4.0), (4.0, 16.0)], '')
    """
    margin = FIDUCIAL_EDGE + FIDUCIAL_MASK_RADIUS
    nx, ny = int(width / FIDUCIAL_STEP), int(height / FIDUCIAL_STEP)
    grid = [(round(i * FIDUCIAL_STEP, 4), round(j * FIDUCIAL_STEP, 4)) for i in range(nx + 1) for j in range(ny + 1)]

    def free(p):
        return inside_outline(p[0], p[1], width, height, corner_radius, margin) and \
            not any(_overlaps(fiducial_box(*p), o) for o in obstacles)

    def nearest(points, right, bottom, k):
        cx, cy = (width if right else 0.0), (height if bottom else 0.0)
        out = []
        for p in sorted(points, key=lambda p: ((p[0] - cx) ** 2 + (p[1] - cy) ** 2, p)):
            if free(p):
                out.append(p)
                if len(out) == k:
                    break
        return out

    spots = {}
    for name, right, bottom in CORNERS:
        quarter = [p for p in grid if (p[0] > width / 2) == right and (p[1] > height / 2) == bottom]
        found = nearest(quarter, right, bottom, FIDUCIAL_NEAREST)
        if found:
            spots[name] = found
    best = None
    names = [n for n, *_ in CORNERS if n in spots]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            for k in range(j + 1, len(names)):
                for a in spots[names[i]]:
                    for b in spots[names[j]]:
                        for c in spots[names[k]]:
                            trio = [a, b, c]
                            if _spread(trio) < FIDUCIAL_SPREAD:
                                continue
                            score = _min_distance(trio)
                            # nearest-to-the-corners trios come first; a later one must spread wider by
                            # FIDUCIAL_STEP x 2 to win, so free corners keep their corner spots
                            if best is None or score > best[0] + 2 * FIDUCIAL_STEP:
                                best = (score, trio)
    if best is not None:
        return best[1], ""
    pairs = []
    for (n1, r1, b1), (n2, r2, b2) in ((CORNERS[0], CORNERS[3]), (CORNERS[1], CORNERS[2])):
        a, b = nearest(grid, r1, b1, 1), nearest(grid, r2, b2, 1)
        if a and b and _diagonal((a[0], b[0])) >= FIDUCIAL_SPREAD:
            pairs.append((_diagonal((a[0], b[0])), [a[0], b[0]], f"{n1} and {n2}"))
    if pairs:
        _, pair, which = max(pairs, key=lambda q: q[0])
        return pair, (f"two diagonally opposite fiducials ({which}): only {len(spots)} corner quarter(s) "
                      f"have room for one ({', '.join(sorted(spots)) or 'none'})")
    raise ValueError(f"fiducials: room near only {len(spots)} corner(s) ({sorted(spots)}) and no two diagonally "
                     "opposite free spots; give positions with the design's fiducials option")


# ---- Priority routes ------------------------------------------------------------------------------


def route_options(route):
    """A priority route's options after its two pads: ``"join"`` (end at any copper the net already
    has) and a number, the route's own track width in mm (wider than its net class for a supply
    branch, say). Returns (join, width or None); raises ValueError on anything else.

    >>> route_options((("U1", "1"), ("C1", "2"), "join", 0.4))
    (True, 0.4)
    """
    extra = list(route[2:])
    widths = [x for x in extra if isinstance(x, (int, float)) and not isinstance(x, bool)]
    bad = [x for x in extra if x != "join" and not (isinstance(x, (int, float)) and not isinstance(x, bool))]
    if bad or extra.count("join") > 1 or len(widths) > 1 or any(w <= 0 for w in widths):
        raise ValueError(f"priority route {route!r}: after the two pads give \"join\" and/or one width in mm")
    return "join" in extra, (float(widths[0]) if widths else None)


def lift_with_fallback(clash, lift, fixed=lambda item: False):
    """Rip-up of one clearance clash (build.clearance_clashes): lift the named item's copper with
    ``lift(net, pos)`` (which returns how many items it took off); when the named item is fixed copper
    such as a locked fan-out via (``fixed(clash)``; PR #74 review: lifting its net's other copper
    nearby leaves the clash), or lifting takes nothing, lift the item it clashes with instead.
    Returns the number of items lifted.

    >>> lift_with_fallback({"net": "GND", "pos": [1, 2], "other": {"net": "/A", "pos": [1, 3]}},
    ...                    lambda net, pos: 0 if net == "GND" else 2)
    2
    >>> lift_with_fallback({"net": "GND", "pos": [1, 2], "other": {"net": "/A", "pos": [1, 3]}},
    ...                    lambda net, pos: 5 if net == "GND" else 2, lambda item: item["net"] == "GND")
    2
    """
    n = 0 if fixed(clash) else lift(clash["net"], clash["pos"])
    if not n and clash.get("other"):
        n = lift(clash["other"]["net"], clash["other"]["pos"])
    return n
