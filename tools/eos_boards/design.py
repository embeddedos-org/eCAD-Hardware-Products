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
    in_bom: bool = True                      # False: copper only, nothing to buy (a test pad); the footprint follows


ALL_RIGHTS_RESERVED = "All rights reserved"   # a closed board: its owner's terms file, see Board.licence_terms

# Test pads (BENCH-READY C1): KiCad's TestPoint symbol, so the pad is in the schematic and the parity
# check, on a bare round pad of at least 1.0 mm. Not a BOM line and not in the position file: there is
# nothing to buy or place (the parts review counted bare test pads as BOM noise).
TESTPOINT_SYMBOL = "Connector:TestPoint"
BOTTOM_PAD_FIELD = "Bottom side"            # why a bench test pad sits on the bottom (C1 asks for the top)
TESTPOINT_FOOTPRINTS = {1.0: "TestPoint:TestPoint_Pad_D1.0mm", 1.5: "TestPoint:TestPoint_Pad_D1.5mm"}

# Rail links (BENCH-READY C2): a solder jumper bridged as delivered, KiCad's
# SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm (its bridge is copper 0.6 mm wide and 0.5 mm long,
# a net tie). No part to buy or place, unlike a 0 ohm resistor; to measure, cut the bridge and put an
# ammeter across the two pads, then bridge them again with solder. IPC-2221's external-layer formula puts
# a 0.6 mm, 1 oz conductor at about 1.6 A for a 10 C rise: enough for every rail on these boards.
RAIL_LINK_SYMBOL = "Jumper:SolderJumper_2_Bridged"
RAIL_LINK_FOOTPRINT = "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm"


def bench_pad(ref: str, net: str, label: str, pcb: Tuple[float, float], sch: Tuple[float, float],
               diameter: float = 1.0, side: str = "F", bottom_reason: str = "") -> "Part":
    """A test pad on ``net`` at ``pcb`` (x, y mm), labelled ``label`` (its value; the generator prints it
    on the silkscreen beside the pad). ``diameter`` 1.0 or 1.5 mm. BENCH-READY C1 puts test pads on the
    top side, where the probe goes; one on the bottom (``side="B"``) needs ``bottom_reason``, which the
    build checks and the schematic carries.

    >>> bench_pad("TP2", "+3V3", "3V3", (10.0, 5.0), (100, 50)).footprint
    'TestPoint:TestPoint_Pad_D1.0mm'
    """
    if diameter not in TESTPOINT_FOOTPRINTS:
        raise ValueError(f"{ref}: test pad diameter {diameter}; use one of {sorted(TESTPOINT_FOOTPRINTS)} mm")
    if side != "F" and not bottom_reason.strip():
        raise ValueError(f"{ref}: a test pad on the bottom side needs bottom_reason (BENCH-READY C1: top side)")
    fields = {"Description": f"Test pad {label} ({net}), {diameter} mm bare copper: no part fitted"}
    if side != "F":
        fields[BOTTOM_PAD_FIELD] = bottom_reason
    return Part(ref, TESTPOINT_SYMBOL, label, TESTPOINT_FOOTPRINTS[diameter], sch, {"1": net},
                pcb=(pcb[0], pcb[1], 0.0), side=side, in_bom=False, fields=fields)


def rail_link(ref: str, source_net: str, load_net: str, pcb: Tuple[float, float, float], sch: Tuple[float, float]) -> "Part":
    """A solder jumper, bridged as delivered, between a regulator's output (``source_net``, e.g.
    ``+3V3_REG``) and its load (``load_net``, ``+3V3``): cut it to check the rail unloaded or to measure
    the load's current, then bridge it again."""
    return Part(ref, RAIL_LINK_SYMBOL, "LINK", RAIL_LINK_FOOTPRINT, sch, {"A": source_net, "B": load_net}, pcb=pcb,
                fields={"Description": f"Rail link {source_net} to {load_net}, bridged as delivered: cut to measure "
                                       f"the current into {load_net}, bridge again with solder"})


@dataclass
class Rail:
    """One supply rail for the bench (BENCH-READY C1, C5)."""
    net: str                       # the net, as the design names it ("+3V3", "GND")
    source: str                    # what supplies it: a part and pin ("U5 AP2112K-3.3 VOUT") or a connector pin
    nominal: str                   # "3.3 V"; "0 V" for ground
    tolerance: str                 # the range to read, with its source ("3.25-3.35 V: AP2112K +-1.5 %, DS39724")
    test_points: List[str]         # test pads (TP refs) or connector pins ("J1.4") on this net
    to_gnd: str                    # resistance to GND unpowered, as a class ("> 100 kohm", "about 10 kohm", "open")
    link: str = ""                 # the rail link that splits it from its regulator, if any
    link_note: str = ""            # what the link is for, or why the rail has none


@dataclass
class BringUpTest:
    """One peripheral test with its pass criterion."""
    peripheral: str
    test: str
    passes: str


@dataclass
class BringUp:
    """What a bench bring-up needs beyond the rails (BENCH-READY C5); the README section is written from it."""
    supply: str                    # where first power goes in, and at what voltage
    current_limit_ma: float        # bench supply current limit for first power
    idle_current: str              # what it should draw, e.g. "about 0.25 mA"
    idle_source: str               # where that number comes from, or "estimate"
    clock: str                     # how to check the clocks, or "N/A: <why>"
    programming: str               # how to program it, or "N/A: <why>"
    tests: List[BringUpTest] = field(default_factory=list)
    before_power: List[str] = field(default_factory=list)   # board-specific checks before first power

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
    reference_copper: Dict[str, object] = field(default_factory=dict)   # {file, origin}: copper from a reference design
    local_footprints: List[str] = field(default_factory=list)          # footprint libraries shipped in tools/eos_boards/footprints
    router_keepouts: List[tuple] = field(default_factory=list)  # (x0, y0, x1, y1[, "B.Cu"]): areas the routers may not enter, top layer unless "B.Cu" is named
    copper_keepouts: List[Tuple[float, float, float, float]] = field(default_factory=list)  # x0, y0, x1, y1: no copper on any layer (an antenna cut-out)
    pour_keepouts: List[tuple] = field(default_factory=list)  # (x0, y0, x1, y1, "F.Cu"|"B.Cu"): no pour on that layer (under an RL78 crystal)
    credits: List[str] = field(default_factory=list)                   # notices third-party licences require (one line each)
    contact: str = ""                                                   # whom to ask for permission; an all-rights-reserved board needs it
    licence_terms: str = ""                                             # an all-rights-reserved board's terms file, relative to tools/eos_boards
    priority_routes: List[tuple] = field(default_factory=list)  # ((ref, pad), (ref, pad)[, "join"]) routed first, in order, before the autorouter; "join" ends at any copper of the net
    rules: Dict[str, float] = field(default_factory=dict)              # design-rule overrides, e.g. a smaller drill a module footprint needs
    escape_footprints: List[str] = field(default_factory=list)          # fine-pitch connectors whose pads keep a clear way out (maze router)
    maze_via_cost_mm: float = 1.2                                        # maze router: a via costs as much as this much track
    stackup: Dict[str, object] = field(default_factory=dict)            # overrides of the fab stack-up (fabrication.stackup_for)
    fiducials: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)  # {"F"|"B": [(x, y) x 3]}: where the automatic choice cannot fit
    shunts: Dict[str, int] = field(default_factory=dict)                # jumper header ref -> 2.54 mm shunts supplied for it (BOM lines)
    rails: List[Rail] = field(default_factory=list)                      # supply rails, GND included, for the bench (C1, C5)
    bringup: Optional[BringUp] = None                                    # bench bring-up data; the README section is written from it
    pin_labels: Dict[str, Dict[str, str]] = field(default_factory=dict)  # connector ref -> {pad: label} on the silkscreen (A4)
    temperature_range: Optional[Tuple[float, float, str, str]] = None    # (min C, max C, limiting part ref, its rating and source) (D8)


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
