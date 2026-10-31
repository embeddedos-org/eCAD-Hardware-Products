"""Write a board's schematic as a KiCad ``.kicad_sch``.

Each part is placed where the design puts it. Every connected pin gets a short wire and a
local label naming its net; unused pins get a no-connect flag. Power nets get one power
symbol each (plus ``PWR_FLAG`` where a net is driven through a passive part, such as the
RP2350 core supply through its inductor), so ``kicad-cli sch erc`` can check the drivers.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Any, Dict, List, Tuple

from .design import NC, Board, Part, resolve
from .kicad_lib import Library
from .sexpr import Sym, dumps, find, find_all

GRID = 1.27
STUB = 2.54
SCH_VERSION = 20231120  # KiCad 8 format: read by KiCad 8, 9 and 10


def _u(seed: str) -> str:
    """A stable UUID, so a rebuild of an unchanged design writes an identical file."""
    return str(uuidlib.uuid5(uuidlib.NAMESPACE_URL, f"eos-boards/{seed}"))


def _snap(v: float) -> float:
    return round(round(v / GRID) * GRID, 4)


def _rotate(x: float, y: float, rot: int) -> Tuple[float, float]:
    """Rotate a library-coordinate offset (y up) by a symbol rotation (degrees, CCW)."""
    for _ in range((rot // 90) % 4):
        x, y = -y, x
    return x, y


def _effects(size: float = 1.27, justify: List[str] = (), hide: bool = False) -> List[Any]:
    eff: List[Any] = [Sym("effects"), [Sym("font"), [Sym("size"), size, size]]]
    if justify:
        eff.append([Sym("justify"), *[Sym(j) for j in justify]])
    if hide:
        eff.append([Sym("hide"), Sym("yes")])
    return eff


def _label(net: str, x: float, y: float, outward: Tuple[int, int], seed: str) -> List[Any]:
    # outward is in schematic coordinates (y down)
    angle, justify = {(1, 0): (0, "left"), (-1, 0): (180, "right"),
                      (0, -1): (90, "left"), (0, 1): (270, "right")}[outward]
    return [Sym("label"), net, [Sym("at"), x, y, angle], [Sym("fields_autoplaced"), Sym("yes")],
            _effects(justify=[justify, "bottom"]), [Sym("uuid"), _u(seed)]]


def _wire(x1: float, y1: float, x2: float, y2: float, seed: str) -> List[Any]:
    return [Sym("wire"), [Sym("pts"), [Sym("xy"), x1, y1], [Sym("xy"), x2, y2]],
            [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]], [Sym("uuid"), _u(seed)]]


def _instance(board: Board, root: str, ref: str) -> List[Any]:
    return [Sym("instances"), [Sym("project"), board.name,
                               [Sym("path"), f"/{root}", [Sym("reference"), ref], [Sym("unit"), 1]]]]


def _place_symbol(board: Board, root: str, lib: Library, lib_id: str, ref: str, value: str,
                  footprint: str, x: float, y: float, rot: int, fields: Dict[str, str],
                  dnp: bool, in_bom: bool, on_board: bool) -> List[Any]:
    symbol = lib.symbol(lib_id)
    # A symbol's own in_bom / on_board flags win (a mounting hole is not a BOM line).
    for key in ("in_bom", "on_board"):
        flag = find(symbol, key)
        if flag is not None and str(flag[1]) == "no":
            in_bom = False if key == "in_bom" else in_bom
            on_board = False if key == "on_board" else on_board
    node: List[Any] = [Sym("symbol"), [Sym("lib_id"), lib_id], [Sym("at"), x, y, rot], [Sym("unit"), 1],
                       [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes" if in_bom else "no")],
                       [Sym("on_board"), Sym("yes" if on_board else "no")],
                       [Sym("dnp"), Sym("yes" if dnp else "no")], [Sym("uuid"), _u(f"{board.name}/sym/{ref}")]]
    values = {"Reference": ref, "Value": value, "Footprint": footprint}
    for prop in find_all(symbol, "property"):
        key = str(prop[1])
        # Keywords, footprint filters and private (library-checker) properties stay in
        # lib_symbols, as KiCad does when it places a symbol.
        if key.startswith("ki_") or (isinstance(prop[1], Sym) and key == "private"):
            continue
        at = find(prop, "at") or [Sym("at"), 0, 0, 0]
        px, py = _rotate(float(at[1]), float(at[2]), rot)
        hidden = key not in ("Reference", "Value")
        node.append([Sym("property"), key, values.get(key, str(prop[2])),
                     [Sym("at"), _snap(x + px), _snap(y - py), 0], _effects(hide=hidden)])
    for key, val in fields.items():
        node.append([Sym("property"), key, val, [Sym("at"), x, y, 0], _effects(hide=True)])
    for pin_number in sorted({str(find(p, "number")[1]) for s in find_all(symbol, "symbol")
                              for p in find_all(s, "pin")}, key=lambda n: (len(n), n)):
        node.append([Sym("pin"), pin_number, [Sym("uuid"), _u(f"{board.name}/pin/{ref}/{pin_number}")]])
    node.append(_instance(board, root, ref))
    return node


def write(board: Board, lib: Library) -> str:
    """The schematic text for ``board``."""
    root = _u(f"{board.name}/root")
    items: List[Any] = []
    used: Dict[str, List[Any]] = {}

    def use(lib_id: str) -> None:
        used.setdefault(lib_id, lib.symbol(lib_id))

    ends: Dict[Tuple[float, float], str] = {}     # wire ends and labels, sheet-wide: one net per point

    def claim(point: Tuple[float, float], net: str, who: str) -> None:
        # Two symbols drawn so close that one's label lands on another's would join their
        # nets without a word in the design: refuse it here rather than leave it to ERC.
        if ends.setdefault(point, net) != net:
            raise ValueError(f"{who}: connection point {point} already carries {ends[point]!r}, not {net!r}; "
                             "move the symbol in the design file")

    for part in board.parts:
        use(part.lib_id)
        x, y = _snap(part.sch[0]), _snap(part.sch[1])
        items.append(_place_symbol(board, root, lib, part.lib_id, part.ref, part.value, part.footprint,
                                   x, y, part.sch_rotation, part.fields, part.dnp, True, part.on_board))
        drawn: Dict[Tuple[float, float], str] = {}
        for number, (pin, net) in resolve(part, lib).items():
            px, py = _rotate(pin.x, pin.y, part.sch_rotation)
            ox, oy = _rotate(*pin.outward, part.sch_rotation)
            ax, ay = _snap(x + px), _snap(y - py)
            out = (int(round(ox)), -int(round(oy)))
            # Stacked pins share one connection point: draw it once, and refuse two nets on it.
            if (ax, ay) in drawn:
                if drawn[(ax, ay)] != net:
                    raise ValueError(f"{part.ref}: stacked pins at ({ax}, {ay}) given "
                                     f"{drawn[(ax, ay)]!r} and {net!r}")
                continue
            drawn[(ax, ay)] = net
            if net == NC:
                items.append([Sym("no_connect"), [Sym("at"), ax, ay], [Sym("uuid"), _u(f"{board.name}/nc/{part.ref}/{number}")]])
                continue
            ex, ey = _snap(ax + out[0] * STUB), _snap(ay + out[1] * STUB)
            claim((ax, ay), net, f"{part.ref} pin {number}")
            claim((ex, ey), net, f"{part.ref} pin {number}")
            items.append(_wire(ax, ay, ex, ey, f"{board.name}/w/{part.ref}/{number}"))
            items.append(_label(net, ex, ey, out, f"{board.name}/l/{part.ref}/{number}"))

    # One power symbol per power net, and a PWR_FLAG where a passive part drives the net.
    px0, py0 = board.power_block
    for i, (net, lib_id) in enumerate(sorted(board.power_nets.items())):
        use(lib_id)
        x, y = _snap(px0 + i * 15.24), _snap(py0)
        items.append(_place_symbol(board, root, lib, lib_id, f"#PWR0{i + 1:02d}", net, "", x, y, 0,
                                   {}, False, False, False))
        items.append(_wire(x, y, x, _snap(y + STUB), f"{board.name}/pw/{net}"))
        items.append(_label(net, x, _snap(y + STUB), (0, 1), f"{board.name}/pl/{net}"))
    for i, net in enumerate(sorted(board.flagged_nets)):
        use("power:PWR_FLAG")
        x, y = _snap(px0 + i * 15.24), _snap(py0 + 15.24)
        items.append(_place_symbol(board, root, lib, "power:PWR_FLAG", f"#FLG0{i + 1:02d}", "PWR_FLAG", "",
                                   x, y, 0, {}, False, False, False))
        items.append(_wire(x, y, x, _snap(y + STUB), f"{board.name}/fw/{net}"))
        items.append(_label(net, x, _snap(y + STUB), (0, 1), f"{board.name}/fl/{net}"))

    for i, ((x, y), text) in enumerate(board.headings):
        items.append([Sym("text"), text, [Sym("exclude_from_sim"), Sym("no")], [Sym("at"), x, y, 0],
                      [Sym("effects"), [Sym("font"), [Sym("size"), 2.54, 2.54], [Sym("bold"), Sym("yes")]],
                       [Sym("justify"), Sym("left"), Sym("bottom")]], [Sym("uuid"), _u(f"{board.name}/head/{i}")]])
    for i, ((x, y), text) in enumerate(board.notes):
        items.append([Sym("text"), text, [Sym("exclude_from_sim"), Sym("no")], [Sym("at"), x, y, 0],
                      _effects(size=1.524, justify=["left", "top"]), [Sym("uuid"), _u(f"{board.name}/note/{i}")]])

    sch: List[Any] = [Sym("kicad_sch"), [Sym("version"), SCH_VERSION], [Sym("generator"), "eos_boards"],
                      [Sym("generator_version"), "1.0"], [Sym("uuid"), root], [Sym("paper"), "A2"],
                      [Sym("title_block"), [Sym("title"), board.title], [Sym("date"), board.date],
                       [Sym("rev"), board.revision], [Sym("company"), board.company],
                       [Sym("comment"), 1, f"Copyright (c) {board.date[:4]} {board.company}. Licence: {board.licence}"],
                       [Sym("comment"), 2, "Generated by tools/eos_boards from the board's design file"],
                       *[[Sym("comment"), 3 + i, line] for i, line in enumerate(board.credits[:7])]],
                      [Sym("lib_symbols"), *used.values()], *items,
                      [Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]]]
    return dumps(sch) + "\n"
