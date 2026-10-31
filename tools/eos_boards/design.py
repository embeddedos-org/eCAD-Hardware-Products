"""A board described as data: its parts, the net on every pin, and where each part sits.

The same description writes the schematic and builds the board, so the two cannot disagree;
``kicad-cli pcb drc --schematic-parity`` proves it on every build.

Every pin of every part must be named in ``nets`` (a net, or ``NC`` for a pin deliberately
left unconnected). A pin can be named by its number, or by its name when that name is unique
or when all pins of that name join the same net (an MCU's several ``IOVDD`` pins).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .kicad_lib import Library, Pin, pins

NC = "NC"


@dataclass
class Part:
    ref: str
    lib_id: str
    value: str
    footprint: str
    sch: Tuple[float, float]                 # schematic position, mm
    nets: Dict[str, str]                     # pin number or name -> net, or NC
    pcb: Tuple[float, float, float] = (0.0, 0.0, 0.0)   # board x, y (mm) and rotation (deg)
    side: str = "F"                          # F or B copper side
    fields: Dict[str, str] = field(default_factory=dict)   # Manufacturer, MPN, Description, ...
    dnp: bool = False
    sch_rotation: int = 0                    # 0, 90, 180 or 270
    model: Optional[Tuple[str, Tuple[float, float, float]]] = None   # 3D model in place of the footprint's: path, offset (mm)
    on_board: bool = True                    # False: a BOM-only item with no footprint (a jumper shunt)


ALL_RIGHTS_RESERVED = "All rights reserved"   # a closed board: its owner's terms file, see Board.licence_terms

# HRO TYPE-C-31-M-12 (KiCad's USB_C_Receptacle_HRO_TYPE-C-31-M-12), placed facing a board edge: HRO's
# "RECOMMEND P.C.B LAYOUT" puts the PCB edge 5.79 mm from the locating pegs, which sit 2.60 mm behind
# the footprint's origin. So the origin goes 3.19 mm from the edge, and the shell stands about
# 0.46 mm proud of it: a plug's overmold then meets the shell, not the board, and seats fully.
USB_C_EDGE = 3.19


@dataclass
class Board:
    name: str
    title: str
    date: str
    company: str
    licence: str
    width: float
    height: float
    parts: List[Part]
    power_nets: Dict[str, str]               # net -> power symbol lib_id
    flagged_nets: List[str]                  # nets that need a PWR_FLAG (driven through a passive)
    revision: str = "A"                      # on the silkscreen identity line, the title blocks and the licence
    notes: List[Tuple[Tuple[float, float], str]] = field(default_factory=list)
    headings: List[Tuple[Tuple[float, float], str]] = field(default_factory=list)
    power_block: Tuple[float, float] = (40.64, 330.2)   # schematic origin of the power symbols
    netclasses: Dict[str, Dict[str, float]] = field(default_factory=dict)
    net_to_class: Dict[str, str] = field(default_factory=dict)
    mounting_holes: List[Tuple[float, float]] = field(default_factory=list)
    corner_radius: float = 1.0
    thickness: float = 1.6
    layers: int = 2
    planes: List[Tuple[str, str]] = field(default_factory=list)       # (net, inner layer): solid planes
    pours: List[Tuple[str, List[str]]] = field(default_factory=lambda: [("GND", ["F.Cu", "B.Cu"])])
    fanout_avoid: List[Tuple[float, float]] = field(default_factory=list)  # points fan-out vias move away from
    no_fanout: List[str] = field(default_factory=list)                    # parts whose pads the router joins
    fanout_pads: Dict[str, List[str]] = field(default_factory=dict)        # ...except these pads (an exposed pad)
    ground_vias: List[str] = field(default_factory=list)                   # two layers: parts whose pads on a two-sided pour get a via beside them
    fanout_first: List[str] = field(default_factory=list)                  # parts whose plane vias go in before the priority routes
    preroutes: List[Tuple[Tuple[str, str], Tuple[str, str], float]] = field(default_factory=list)  # (ref, pad), (ref, pad), width
    reference_copper: Dict[str, object] = field(default_factory=dict)   # {file, origin[, moved_vias]}: copper from a reference design
    local_footprints: List[str] = field(default_factory=list)          # footprint libraries shipped in tools/eos_boards/footprints
    router_keepouts: List[tuple] = field(default_factory=list)  # (x0, y0, x1, y1[, "B.Cu"]): areas the routers may not enter, top layer unless "B.Cu" is named
    copper_keepouts: List[Tuple[float, float, float, float]] = field(default_factory=list)  # x0, y0, x1, y1: no copper on any layer (an antenna cut-out)
    pour_keepouts: List[tuple] = field(default_factory=list)  # (x0, y0, x1, y1, "F.Cu"|"B.Cu"): no pour on that layer (under an RL78 crystal)
    credits: List[str] = field(default_factory=list)                   # notices third-party licences require (one line each)
    contact: str = ""                                                   # whom to ask for permission; an all-rights-reserved board needs it
    licence_terms: str = ""                                             # an all-rights-reserved board's terms file, relative to tools/eos_boards
    priority_routes: List[tuple] = field(default_factory=list)  # ((ref, pad), (ref, pad)[, "join"][, width_mm][, {"via": [x, y, diameter, drill]}]) routed first, in order; "join" ends at any copper of the net; width_mm overrides the net class; "via" pins a via the line passes through
    rules: Dict[str, float] = field(default_factory=dict)              # design-rule overrides, e.g. a smaller drill a module footprint needs
    escape_footprints: List[str] = field(default_factory=list)          # fine-pitch connectors whose pads keep a clear way out (maze router)
    maze_via_cost_mm: float = 1.2                                        # maze router: a via costs as much as this much track
    stackup: Dict[str, object] = field(default_factory=dict)            # overrides of the fab stack-up (fabrication.stackup_for)
    fiducials: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)  # {"F"|"B": [(x, y) x 3]}: where the automatic choice cannot fit
    shunts: Dict[str, int] = field(default_factory=dict)                # jumper header ref -> 2.54 mm shunts supplied for it (BOM lines)


def resolve(part: Part, lib: Library) -> Dict[str, Tuple[Pin, str]]:
    """Map every pin number of ``part`` to (pin, net). Raises on any unassigned or unknown pin."""
    symbol = lib.symbol(part.lib_id)
    all_pins = [p for p in pins(symbol) if p.unit in (0, 1)]
    by_number = {p.number: p for p in all_pins}
    out: Dict[str, Tuple[Pin, str]] = {}
    for key, net in part.nets.items():
        if key in by_number:
            matched = [by_number[key]]
        else:
            matched = [p for p in all_pins if p.name == key]
        if not matched:
            raise KeyError(f"{part.ref} ({part.lib_id}): no pin named or numbered {key!r}; "
                           f"pins are {sorted({p.name for p in all_pins})}")
        for p in matched:
            if p.number in out and out[p.number][1] != net:
                raise ValueError(f"{part.ref}: pin {p.number} ({p.name}) given two nets: "
                                 f"{out[p.number][1]!r} and {net!r}")
            out[p.number] = (p, net)
    missing = sorted((p.number, p.name) for p in all_pins if p.number not in out)
    if missing:
        raise ValueError(f"{part.ref} ({part.lib_id}): pins without a net: {missing}")
    return out


def netlist(board: Board, lib: Library) -> Dict[str, List[Tuple[str, str]]]:
    """net -> [(ref, pin number)], NC pins left out."""
    nets: Dict[str, List[Tuple[str, str]]] = {}
    for part in board.parts:
        for number, (_, net) in resolve(part, lib).items():
            if net != NC:
                nets.setdefault(net, []).append((part.ref, number))
    return nets
