"""Write the footprints KiCad's own libraries do not have (part of the MIT generator).

EoS_Packages.pretty: NXP HLQFP-100 (SOT1570-3), which KiCad 10 does not ship, and a 2 x 49 pin header.

The LPC55S69JBD100's package has an exposed pad of only 3.21-3.61 mm (data sheet Figure 32,
"VIEW J-J"), and on this package that pad is the chip's only VSS connection (Table 3). KiCad
10.0.6 has 14 x 14 mm, 0.5 mm, 100-lead footprints only with a 5 x 5 mm (TQFP-100-1EP) or
6.9 x 6.9 mm (LQFP-100-1EP) pad, whose paste apertures reach 0.6-1.4 mm past this package's
pad and would print solder under its plastic body. So the footprint is drawn here from NXP's
own land pattern, LPC55S6x data sheet Rev. 2.5, section 15, Figures 37-39 (SOT1570-3, "PCB
design guidelines"):

* I/O pads 0.27 x 1.45 mm, 0.5 mm pitch, pad centres 7.775 mm from the package centre
  (Figure 38, "I/O pads and solderable area");
* solder-mask openings 0.37 x 1.55 mm (Figure 37), i.e. 0.05 mm per side;
* exposed pad: copper 3.21 x 3.21 mm (Figure 38), mask opening 3.31 x 3.31 mm (Figure 37),
  paste as four 1.405 mm square apertures centred 0.853 mm off each axis (Figure 39);
  I/O paste is the full pad (Figure 39);
* body 14 x 14 mm, leads to 16 x 16 mm (Figure 31).

No thermal vias are drawn: NXP's figures show none, and the eos_boards generator already puts
a 2 x 2 array of vias into any exposed pad on a plane net (pcb_build.fanout). Courtyard 0.25
mm outside the pads, as KiCad's own QFP footprints. 3D model: KiCad's LQFP-100 14 x 14 mm body
(the same 14 x 14 x 1.4 mm outline; HLQFP's 1.45 mm maximum height is within it).

It also holds a 2 x 49 (98-hole) straight 2.54 mm header, PinHeader_2x49_P2.54mm_Vertical: KiCad's
Connector_PinHeader_2.54mm library stops at 2 x 40. It is drawn exactly as KiCad's own generated pin
headers (PinHeader_2x40_P2.54mm_Vertical, KiCad 10): 1.7 mm pads on 1.0 mm drills, pad 1 square,
odd pads in the first column and even pads in the second, the silkscreen outline 1.38 mm outside the
pad centres with the pin-1 corner open, the courtyard 1.77 mm out, the fabrication outline 1.27 mm out
with a chamfer at pin 1. KiCad ships no 3D model of this length, so none is referenced.

usage: python3 tools/eos_boards/footprints/generate.py
   writes tools/eos_boards/footprints/EoS_Packages.pretty/HLQFP-100-1EP_14x14mm_P0.5mm_EP3.21x3.21mm.kicad_mod
   and tools/eos_boards/footprints/EoS_Packages.pretty/PinHeader_2x49_P2.54mm_Vertical.kicad_mod
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from eos_boards.sexpr import Sym, dumps  # noqa: E402

NAME = "HLQFP-100-1EP_14x14mm_P0.5mm_EP3.21x3.21mm"
PITCH, ROW, PAD_W, PAD_L = 0.5, 7.775, 0.27, 1.45          # Figure 38
MASK = 0.05                                                  # Figure 37: 0.37 x 1.55 openings
EP, EP_PASTE, EP_PASTE_OFF = 3.21, 1.405, 0.853              # Figures 37-39
BODY, LEADS = 7.0, 8.0                                       # Figure 31: 14 mm body, 16 mm across leads
COURT = round(ROW + PAD_L / 2 + 0.25, 2)                     # 8.75


def _font(size=1.0):
    return [Sym("effects"), [Sym("font"), [Sym("size"), size, size], [Sym("thickness"), round(size * 0.15, 2)]]]


def _prop(key, value, x, y, layer, hide=False):
    node = [Sym("property"), key, value, [Sym("at"), x, y, 0], [Sym("layer"), layer]]
    if hide:
        node.append([Sym("hide"), Sym("yes")])
    node.append(_font())
    return node


def _line(a, b, layer, width):
    return [Sym("fp_line"), [Sym("start"), *a], [Sym("end"), *b],
            [Sym("stroke"), [Sym("width"), width], [Sym("type"), Sym("solid")]], [Sym("layer"), layer]]


def _poly(points, layer, width):
    return [_line(points[i], points[(i + 1) % len(points)], layer, width) for i in range(len(points))]


def pad_xy(n: int):
    """Centre and rotation of I/O pad n (1-100): pin 1 top-left, counter-clockwise, as Figure 31."""
    k = (n - 1) % 25
    off = round(-6.0 + PITCH * k, 3)
    side = (n - 1) // 25
    if side == 0:
        return (-ROW, off, 0)          # left, top to bottom
    if side == 1:
        return (off, ROW, 90)          # bottom, left to right
    if side == 2:
        return (ROW, -off, 0)          # right, bottom to top
    return (-off, -ROW, 90)            # top, right to left


def footprint() -> list:
    fp = [Sym("footprint"), NAME, [Sym("version"), 20241229], [Sym("generator"), "eos_boards"], [Sym("layer"), "F.Cu"],
          [Sym("descr"), "NXP HLQFP-100 (SOT1570-3), 14 x 14 mm, 0.5 mm pitch, exposed pad 3.21 x 3.21 mm: land pattern "
                         "from the LPC55S6x data sheet Rev. 2.5, section 15, Figures 37-39"],
          [Sym("tags"), "HLQFP QFP SOT1570-3 LPC55S6x"],
          _prop("Reference", "REF**", 0, -9.8, "F.SilkS"),
          _prop("Value", NAME, 0, 9.8, "F.Fab"),
          _prop("Datasheet", "https://www.nxp.com/docs/en/data-sheet/LPC55S6x.pdf", 0, 0, "F.Fab", True),
          _prop("Description", "HLQFP-100 with 3.21 mm exposed pad, NXP SOT1570-3 (LPC55S6x data sheet, Figures 37-39)",
                0, 0, "F.Fab", True),
          [Sym("attr"), Sym("smd")]]
    # fabrication outline with the pin-1 chamfer, silkscreen corners clear of the pads, courtyard
    c = 1.0
    fp += _poly([(-BODY + c, -BODY), (BODY, -BODY), (BODY, BODY), (-BODY, BODY), (-BODY, -BODY + c)], "F.Fab", 0.1)
    s, e = 7.11, 6.41
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        fp.append(_line((sx * e, sy * s), (sx * s, sy * s), "F.SilkS", 0.12))
        fp.append(_line((sx * s, sy * s), (sx * s, sy * e), "F.SilkS", 0.12))
    fp.append(_line((-s, -e), (-ROW - PAD_L / 2, -e), "F.SilkS", 0.12))      # pin-1 mark along pad 1
    fp += _poly([(-COURT, -COURT), (COURT, -COURT), (COURT, COURT), (-COURT, COURT)], "F.CrtYd", 0.05)
    fp.append([Sym("fp_text"), Sym("user"), "${REFERENCE}", [Sym("at"), 0, 0, 0], [Sym("layer"), "F.Fab"], _font()])
    for n in range(1, 101):
        x, y, rot = pad_xy(n)
        size = (PAD_L, PAD_W) if rot == 0 else (PAD_W, PAD_L)       # long axis across the row, as KiCad's QFPs
        fp.append([Sym("pad"), str(n), Sym("smd"), Sym("roundrect"), [Sym("at"), x, y],
                   [Sym("size"), *size], [Sym("layers"), "F.Cu", "F.Mask", "F.Paste"],
                   [Sym("roundrect_rratio"), 0.25], [Sym("solder_mask_margin"), MASK]])
    fp.append([Sym("pad"), "101", Sym("smd"), Sym("rect"), [Sym("at"), 0, 0], [Sym("size"), EP, EP],
               [Sym("layers"), "F.Cu", "F.Mask"], [Sym("solder_mask_margin"), MASK], [Sym("zone_connect"), 2]])
    for sx in (-1, 1):
        for sy in (-1, 1):
            fp.append([Sym("pad"), "", Sym("smd"), Sym("rect"), [Sym("at"), sx * EP_PASTE_OFF, sy * EP_PASTE_OFF],
                       [Sym("size"), EP_PASTE, EP_PASTE], [Sym("layers"), "F.Paste"]])
    fp.append([Sym("embedded_fonts"), Sym("no")])
    fp.append([Sym("model"), "${KICAD10_3DMODEL_DIR}/Package_QFP.3dshapes/LQFP-100_14x14mm_P0.5mm.step",
               [Sym("offset"), [Sym("xyz"), 0, 0, 0]], [Sym("scale"), [Sym("xyz"), 1, 1, 1]],
               [Sym("rotate"), [Sym("xyz"), 0, 0, 0]]])
    return fp


def check() -> None:
    xs = [pad_xy(n) for n in range(1, 101)]
    assert len(set((x, y) for x, y, _ in xs)) == 100
    assert pad_xy(1) == (-ROW, -6.0, 0) and pad_xy(25) == (-ROW, 6.0, 0)
    assert pad_xy(26) == (-6.0, ROW, 90) and pad_xy(50) == (6.0, ROW, 90)
    assert pad_xy(51) == (ROW, 6.0, 0) and pad_xy(75) == (ROW, -6.0, 0)
    assert pad_xy(76) == (6.0, -ROW, 90) and pad_xy(100) == (-6.0, -ROW, 90)
    # paste apertures stay inside the exposed pad's copper (Figure 39 inside Figure 38)
    assert EP_PASTE_OFF + EP_PASTE / 2 <= EP / 2


HEADER_ROWS = 49
HEADER_NAME = f"PinHeader_2x{HEADER_ROWS}_P2.54mm_Vertical"


def header_2x49() -> list:
    """2 x 49 straight pin header, 2.54 mm pitch, drawn as KiCad's generated PinHeader_2xNN (see above):
    pad n at column (n - 1) % 2, row (n - 1) // 2, pad 1 at the origin."""
    p, end = 2.54, round(2.54 * (HEADER_ROWS - 1), 2)
    fp = [Sym("footprint"), HEADER_NAME, [Sym("version"), 20241229], [Sym("generator"), "eos_boards"],
          [Sym("layer"), "F.Cu"],
          [Sym("descr"), f"Through hole straight pin header, 2x{HEADER_ROWS}, 2.54mm pitch, double rows (drawn as "
                         "KiCad's generated pin headers; KiCad's library stops at 2x40)"],
          [Sym("tags"), f"Through hole pin header THT 2x{HEADER_ROWS} 2.54mm double row"],
          _prop("Reference", "REF**", 1.27, -2.38, "F.SilkS"),
          _prop("Value", HEADER_NAME, 1.27, round(end + 2.38, 2), "F.Fab"),
          [Sym("attr"), Sym("through_hole")]]
    s, c, f = 1.38, 1.77, 1.27
    fp += [_line((-s, -s), (0, -s), "F.SilkS", 0.12), _line((-s, 0), (-s, -s), "F.SilkS", 0.12),
           _line((-s, f), (-s, round(end + s, 2)), "F.SilkS", 0.12), _line((-s, f), (f, f), "F.SilkS", 0.12),
           _line((-s, round(end + s, 2)), (round(p + s, 2), round(end + s, 2)), "F.SilkS", 0.12),
           _line((f, -s), (round(p + s, 2), -s), "F.SilkS", 0.12), _line((f, f), (f, -s), "F.SilkS", 0.12),
           _line((round(p + s, 2), -s), (round(p + s, 2), round(end + s, 2)), "F.SilkS", 0.12)]
    fp += _poly([(-c, -c), (round(p + c, 2), -c), (round(p + c, 2), round(end + c, 2)), (-c, round(end + c, 2))], "F.CrtYd", 0.05)
    fp += _poly([(-f, 0), (0, -f), (round(p + f, 2), -f), (round(p + f, 2), round(end + f, 2)), (-f, round(end + f, 2))],
                "F.Fab", 0.1)
    fp.append([Sym("fp_text"), Sym("user"), "${REFERENCE}", [Sym("at"), 1.27, round(end / 2, 2), 90], [Sym("layer"), "F.Fab"],
               _font()])
    for n in range(1, 2 * HEADER_ROWS + 1):
        x, y = round(p * ((n - 1) % 2), 2), round(p * ((n - 1) // 2), 2)
        fp.append([Sym("pad"), str(n), Sym("thru_hole"), Sym("rect" if n == 1 else "circle"), [Sym("at"), x, y],
                   [Sym("size"), 1.7, 1.7], [Sym("drill"), 1.0], [Sym("layers"), "*.Cu", "*.Mask"],
                   [Sym("remove_unused_layers"), Sym("no")]])
    fp.append([Sym("embedded_fonts"), Sym("no")])
    return fp


def check_header() -> None:
    pads = [q for q in header_2x49() if isinstance(q, list) and str(q[0]) == "pad"]
    assert [str(q[1]) for q in pads] == [str(n) for n in range(1, 2 * HEADER_ROWS + 1)]
    xy = {(q[4][1], q[4][2]) for q in pads}
    assert len(xy) == 2 * HEADER_ROWS and max(y for _, y in xy) == round(2.54 * (HEADER_ROWS - 1), 2)


def main() -> int:
    out = HERE / "EoS_Packages.pretty"
    check()
    check_header()
    out.mkdir(parents=True, exist_ok=True)
    for name, fp in ((NAME, footprint()), (HEADER_NAME, header_2x49())):
        path = out / f"{name}.kicad_mod"
        path.write_text(dumps(fp) + "\n")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
