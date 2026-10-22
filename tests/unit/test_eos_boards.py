"""tools/eos_boards: the board generator's pure-Python parts, and the exactness of the copper
reused from Raspberry Pi's RP2350A minimal design on the built EoS Learn RP2350.

None of this needs KiCad: symbols come from a small library written here, and the built board
is read as text. The exactness check compares in integer nanometres (KiCad's own unit), so a
1 nm move of any reused footprint, track end, via or zone corner fails it.
"""

from __future__ import annotations

import importlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from eos_boards import build, design, schematic  # noqa: E402
from eos_boards.design import NC, Board, Part  # noqa: E402
from eos_boards.kicad_lib import Library, pins  # noqa: E402
from eos_boards.reference import extract_rpi_minimal as extract  # noqa: E402
from eos_boards.sexpr import Sym, dumps, find, find_all, loads  # noqa: E402

BOARD_DIR = REPO_ROOT / "boards" / "eos" / "eos-learn-rp2350"
PCB = BOARD_DIR / "hardware" / "eos-learn-rp2350.kicad_pcb"
CORE = REPO_ROOT / "tools" / "eos_boards" / "reference" / "rp2350a_minimal_r4_core.json"
MCU = (26.3, 30.3)

SYMBOLS = """(kicad_symbol_lib (version 20231120) (generator "test")
  (symbol "R" (pin_names (offset 0)) (in_bom yes) (on_board yes)
    (property "Reference" "R" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "R" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (symbol "R_1_1"
      (pin passive line (at 0 3.81 270) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 0 -3.81 90) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))))
  (symbol "U" (in_bom yes) (on_board yes)
    (property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "U" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (symbol "U_1_1"
      (pin power_in line (at -7.62 2.54 0) (length 2.54) (name "VDD" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin power_in line (at -7.62 0 0) (length 2.54) (name "VDD" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin bidirectional line (at 7.62 0 180) (length 2.54) (name "IO" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))))
  (symbol "M" (in_bom yes) (on_board yes)
    (property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "M" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (symbol "M_1_1"
      (pin power_in line (at -7.62 2.54 0) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "[1,3-4]" (effects (font (size 1.27 1.27)))))
      (pin bidirectional line (at 7.62 0 180) (length 2.54) (name "A/B" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27))))))))
"""


def nm(value) -> int:
    return round(float(value) * 1_000_000)


class _Lib(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        Path(self.tmp.name, "T.kicad_sym").write_text(SYMBOLS)
        self.lib = Library(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def board(self, parts, **kw):
        return Board(name="t", title="T", revision="A", date="2026-10-11", company="Kartikeydheer Srivastava",
                     licence="MIT", width=10, height=10, parts=parts, power_nets={}, flagged_nets=[], **kw)


class SexprTest(unittest.TestCase):
    def test_round_trip_keeps_order_and_quoted_brackets(self):
        text = '(a "x ( y" (b 1 2.5) (c "q\\"r") d)'
        node = loads(text)
        self.assertEqual(str(node[0]), "a")
        self.assertEqual(node[1], "x ( y")                 # a quoted bracket is text, not structure
        self.assertEqual([str(x[0]) for x in node[2:4]], ["b", "c"])
        self.assertEqual(loads(dumps(node)), node)

    def test_find_and_find_all(self):
        node = loads("(r (p 1) (q 2) (p 3))")
        self.assertEqual(find(node, "q")[1], 2)
        self.assertEqual([p[1] for p in find_all(node, "p")], [1, 3])
        self.assertIsNone(find(node, "z"))


class Batch3SymbolTest(unittest.TestCase):
    """Critical package pins from the manufacturer pin tables, read from the shipped symbols."""

    def test_supply_and_debug_pin_numbers(self):
        # Renesas R01DS0367 Table 1.17, R01DS0131 section 1.3.11;
        # TI SPRS945H Table 5-1, 100 PZ column. A shifted supply pin can damage hardware.
        expected = {
            "R7FA4M2AD3CFP": (100, {
                "9": ("VCL", "power_out"), "15": ("VCC", "power_in"),
                "26": ("VSS_USB", "power_in"), "29": ("VCC_USB", "power_in"),
                "38": ("~{RES}", "input"), "88": ("AVCC0", "power_in"),
                "89": ("AVSS0/VREFL", "power_in"), "90": ("VREFL0", "power_in"),
            }),
            "R5F100LEAFB": (64, {
                "5": ("P40/TOOL0", "bidirectional"), "6": ("~{RESET}", "input"),
                "12": ("REGC", "power_out"), "13": ("VSS", "power_in"),
                "14": ("EVSS0", "power_in"), "15": ("VDD", "power_in"),
                "16": ("EVDD0", "power_in"),
            }),
            "TMS320F280049CPZ": (100, {
                "2": ("~{XRS}", "open_collector"), "4": ("VDD", "power_in"),
                "46": ("VDD", "power_in"), "69": ("X1", "bidirectional"),
                "71": ("VDD", "power_in"), "73": ("VREGENZ", "input"),
                "80": ("VDDIO_SW", "power_in"), "82": ("VSS_SW", "power_in"),
                "87": ("VDD", "power_in"),
            }),
        }
        library = Library(REPO_ROOT / "tools" / "eos_boards" / "symbols")
        for name, (count, critical) in expected.items():
            with self.subTest(symbol=name):
                actual = pins(library.symbol(f"EoS_MCU:{name}"))
                self.assertEqual(sorted(int(p.number) for p in actual), list(range(1, count + 1)))
                by_number = {p.number: (p.name, p.etype) for p in actual}
                self.assertEqual({n: by_number[n] for n in critical}, critical)


class ResolveTest(_Lib):
    def test_pins_by_number_and_by_shared_name(self):
        part = Part("U1", "T:U", "U", "fp", (0, 0), {"VDD": "+3V3", "3": "SIG"})
        out = design.resolve(part, self.lib)
        self.assertEqual({k: v[1] for k, v in out.items()}, {"1": "+3V3", "2": "+3V3", "3": "SIG"})

    def test_missing_pin_is_refused(self):
        with self.assertRaisesRegex(ValueError, "pins without a net"):
            design.resolve(Part("U1", "T:U", "U", "fp", (0, 0), {"VDD": "+3V3"}), self.lib)

    def test_unconnected_net_names_spell_a_slash_as_kicad_does(self):
        self.assertEqual(build.kicad_net_text("~{RI}/CLK"), "~{RI}{slash}CLK")      # a CP2102N pin, as KiCad names its net
        self.assertEqual(build.kicad_net_text("GPIO.3"), "GPIO.3")
        self.assertEqual(build.unconnected_net("U4", "~{RI}/CLK", "1"), "unconnected-(U4-~{RI}{slash}CLK-Pad1)")
        self.assertEqual(build.unconnected_net("J2", "", "3"), "unconnected-(J2-Pad3)")   # a barrel jack's unnamed pin
        self.assertEqual(build.unconnected_net("U2", "~{FLT}", "3"), "unconnected-(U2-~{FLT}-Pad3)")

    def test_stacked_pin_numbers_name_every_pad(self):
        self.assertEqual(build.pad_numbers("[1,15,38,39]"), ["1", "15", "38", "39"])   # KiCad's ESP32-WROOM-32E GND
        self.assertEqual(build.pad_numbers("[1-3,7]"), ["1", "2", "3", "7"])
        self.assertEqual(build.pad_numbers("A5"), ["A5"])
        for bad in ("[3-1]", "[A1-A3]", "[1,,2]"):                 # never drop a pin's pads silently
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "cannot read"):
                build.pad_numbers(bad)

    def test_unknown_pin_is_refused(self):
        with self.assertRaisesRegex(KeyError, "no pin named or numbered"):
            design.resolve(Part("R1", "T:R", "1k", "fp", (0, 0), {"1": "A", "2": "B", "9": "C"}), self.lib)

    def test_two_nets_on_one_pin_is_refused(self):
        with self.assertRaisesRegex(ValueError, "given two nets"):
            design.resolve(Part("U1", "T:U", "U", "fp", (0, 0), {"VDD": "+3V3", "1": "GND", "3": NC}), self.lib)


class SchematicTest(_Lib):
    def test_rebuild_is_identical_and_carries_copyright_and_credits(self):
        parts = [Part("R1", "T:R", "1k", "fp", (50, 50), {"1": "A", "2": NC})]
        board = self.board(parts, credits=["Core layout (c) 2026 Raspberry Pi Ltd, MIT"])
        first = schematic.write(board, self.lib)
        self.assertEqual(first, schematic.write(board, self.lib))          # stable UUIDs
        self.assertIn('"Copyright (c) 2026 Kartikeydheer Srivastava. Licence: MIT"', first)
        self.assertIn('"Core layout (c) 2026 Raspberry Pi Ltd, MIT"', first)
        self.assertIn("(no_connect", first)


class SpecTest(_Lib):
    def test_stacked_pins_and_slashed_no_connects_reach_the_board_spec(self):
        board = self.board([Part("U1", "T:M", "M", "fp", (50, 50), {"GND": "GND", "A/B": NC})])
        pads = build.spec_for(board, self.lib, Path(self.tmp.name), [])["parts"][0]["pads"]
        self.assertEqual(pads, {"1": "/GND", "3": "/GND", "4": "/GND",              # one stacked pin, three pads
                                "2": "unconnected-(U1-A{slash}B-Pad2)"})            # the net KiCad gives it

    def test_a_footprint_follows_its_symbols_bom_flag(self):
        # a library test point: the symbol says (in_bom no) or yes, and the footprint must agree,
        # or KiCad's parity check reports "Exclude from bill of materials settings differ"
        Path(self.tmp.name, "T.kicad_sym").write_text(SYMBOLS.replace('(symbol "R" (pin_names (offset 0)) (in_bom yes)',
                                                                      '(symbol "R" (pin_names (offset 0)) (in_bom no)'))
        lib = Library(Path(self.tmp.name))
        board = self.board([Part("TP1", "T:R", "TP", "fp", (50, 50), {"1": "A", "2": NC}),
                            Part("U1", "T:M", "M", "fp", (80, 50), {"GND": "GND", "A/B": NC})])
        flags = {p["ref"]: p["in_bom"] for p in build.spec_for(board, lib, Path(self.tmp.name), [])["parts"]}
        self.assertEqual(flags, {"TP1": False, "U1": True})

    def test_layered_keepouts_and_ground_vias_reach_the_board_spec(self):
        board = self.board([Part("U1", "T:M", "M", "fp", (5, 5), {"GND": "GND", "A/B": NC})],
                           router_keepouts=[(1, 1, 2, 2), (3, 3, 4, 4, "B.Cu")], ground_vias=["U1"])
        spec = build.spec_for(board, self.lib, Path(self.tmp.name), [])
        self.assertEqual(spec["router_keepouts"], [[1, 1, 2, 2], [3, 3, 4, 4, "B.Cu"]])
        self.assertEqual(spec["ground_vias"], ["U1"])
        board = self.board([Part("U1", "T:M", "M", "fp", (5, 5), {"GND": "GND", "A/B": NC})],
                           pour_keepouts=[(3, 3, 4, 4, "B.Cu")])
        self.assertEqual(build.spec_for(board, self.lib, Path(self.tmp.name), [])["pour_keepouts"], [[3, 3, 4, 4, "B.Cu"]])

    def test_a_mistyped_keepout_layer_or_ground_via_part_is_refused(self):
        # "B_Cu" is how the same file names silk layers ("B_SilkS"): taken silently, it would
        # keep the top layer clear instead of the bottom
        parts = [Part("U1", "T:M", "M", "fp", (5, 5), {"GND": "GND", "A/B": NC})]
        for kw in ({"router_keepouts": [(3, 3, 4, 4, "B_Cu")]}, {"router_keepouts": [(4, 3, 3, 4)]},
                   {"ground_vias": ["C99"]}, {"fanout_first": ["C99"]}, {"pour_keepouts": [(3, 3, 4, 4)]},
                   {"pour_keepouts": [(3, 3, 4, 4, "In1.Cu")]}):
            with self.subTest(**{k: str(v) for k, v in kw.items()}), self.assertRaises(SystemExit):
                build.spec_for(self.board(parts, **kw), self.lib, Path(self.tmp.name), [])


class ClashTest(unittest.TestCase):
    def test_clearance_clashes_pick_the_via_then_the_shorter_track_and_leave_pads(self):
        def item(desc, x):
            return {"description": desc, "pos": {"x": x, "y": 1.0}}
        drc = {"violations": [
            {"type": "clearance", "severity": "error",           # EoS STM32 64, first build
             "items": [item("Via [/PH0] on F.Cu - B.Cu", 30.09), item("Track [/PA1] on B.Cu, length 5.2445 mm", 30.08)]},
            {"type": "clearance", "severity": "error",
             "items": [item("Track [/A] on F.Cu, length 9.0 mm", 1.0), item("Track [/B] on F.Cu, length 0.4 mm", 2.0)]},
            {"type": "clearance", "severity": "error",           # a pad can't be moved: the build fails instead
             "items": [item("Pad 3 [/C] of U1 on F.Cu", 3.0), item("Track [/D] on F.Cu, length 1.0 mm", 4.0)]},
            {"type": "silk_edge_clearance", "severity": "warning", "items": [item("Track [/E] on F.Cu, length 1 mm", 5.0)] * 2},
        ]}
        self.assertEqual(build.clearance_clashes(drc), [{"net": "/PH0", "pos": [30.09, 1.0]}, {"net": "/B", "pos": [2.0, 1.0]}])


class LicenceTest(_Lib):
    def test_mit_with_owner_and_third_party_notice(self):
        board = self.board([], credits=["Core layout: Copyright (c) 2026 Raspberry Pi Ltd, MIT licence"])
        text = build.licence_text(board)
        self.assertTrue(text.startswith("MIT License\n\nCopyright (c) 2026 Kartikeydheer Srivastava\n"))
        self.assertIn("Permission is hereby granted", text)
        self.assertIn("- Core layout: Copyright (c) 2026 Raspberry Pi Ltd, MIT licence", text)

    def closed(self, **kw):
        board = self.board([], **kw)
        board.licence = design.ALL_RIGHTS_RESERVED
        return board

    def test_all_rights_reserved_names_board_owner_contact_and_embeddedos(self):
        board = self.closed(credits=["Core layout: Copyright (c) 2026 Raspberry Pi Ltd, MIT licence"],
                            contact="someone@example.org", licence_terms="boards/licence_terms.txt")
        text = build.licence_text(board, "t")
        self.assertTrue(text.startswith('All Rights Reserved Board Licence\n\nT, revision A\n'
                                        'Copyright (c) 2026 Kartikeydheer Srivastava ("the copyright holder").\n'
                                        'All rights reserved.\n'))
        self.assertIn("- everything in boards/eos/t/:", text)                    # names the board's own files
        self.assertIn("tools/eos_boards/boards/t.py", text)
        self.assertIn("To ask,\n   write to someone@example.org.", text)
        self.assertIn("EmbeddedOS may not sell boards made from the Design", text)
        self.assertIn("It ends thirty days after that notice.", text)            # what withdrawal means
        self.assertNotIn("Permission is hereby granted", text)                   # not the MIT grant
        self.assertNotIn("{", text)                                               # every field filled in
        self.assertIn("- Core layout: Copyright (c) 2026 Raspberry Pi Ltd, MIT licence", text)
        self.assertIn("- " + build.KICAD_LIBRARIES, text)

    def test_all_rights_reserved_needs_a_contact_and_terms(self):
        terms = "boards/licence_terms.txt"
        for kw, module in (({"contact": "  ", "licence_terms": terms}, "t"), ({"contact": "a@example.org"}, "t"),
                           ({"contact": "a@example.org", "licence_terms": terms}, "")):
            with self.subTest(module=module, **kw), self.assertRaisesRegex(SystemExit, "needs a contact, its licence terms"):
                build.licence_text(self.closed(**kw), module)

    def test_other_licences_are_not_guessed(self):
        board = self.board([])
        board.licence = "CERN-OHL-S-2.0"
        with self.assertRaisesRegex(SystemExit, "no licence text"):
            build.licence_text(board)


class CheckReferenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ref = Path(self.tmp.name, "ref.json")
        self.ref.write_text(json.dumps({"footprints": {"C1": {"footprint": "L:cap", "x": 0, "y": 0, "rot": 0,
                                                              "pads": {"1": "+3V3", "2": "GND"}}},
                                        "tracks": [], "vias": [], "zones": []}))
        self.board = Board(name="t", title="T", revision="A", date="2026-10-11", company="X", licence="MIT",
                           width=1, height=1, parts=[], power_nets={}, flagged_nets=[],
                           reference_copper={"file": str(self.ref), "origin": (0, 0)})

    def tearDown(self):
        self.tmp.cleanup()

    def test_matching_part_passes(self):
        build.check_reference(self.board, None, [{"ref": "C1", "footprint": "L:cap", "pads": {"1": "+3V3", "2": "GND"}}])

    def test_pad_on_another_net_is_refused(self):
        with self.assertRaisesRegex(SystemExit, "other nets than the reference copper expects"):
            build.check_reference(self.board, None, [{"ref": "C1", "footprint": "L:cap", "pads": {"1": "+1V1", "2": "GND"}}])

    def test_other_footprint_is_refused(self):
        with self.assertRaisesRegex(SystemExit, "drawn for"):
            build.check_reference(self.board, None, [{"ref": "C1", "footprint": "L:other", "pads": {"1": "+3V3", "2": "GND"}}])

    def test_missing_part_is_refused(self):
        with self.assertRaisesRegex(SystemExit, "is not on"):
            build.check_reference(self.board, None, [])


class ExtractorTest(unittest.TestCase):
    def test_footprint_keeps_four_fields_and_unrotates(self):
        fp = loads('(footprint "Lib:part" (layer "F.Cu") (uuid "u") (at 10 20 90)'
                   ' (property "Reference" "C5" (at 0 -1 90)) (property "Value" "4.7u" (at 0 1 90))'
                   ' (property "lcsc_pn" "C123" (at 0 0 90)) (path "/x")'
                   ' (pad "1" smd rect (at -0.5 0 90) (size 0.5 0.5) (layers "F.Cu") (net "+3V3") (uuid "p")))')
        name, text = extract.footprint(fp, {})
        node = loads(text)
        self.assertEqual(name, "part")
        self.assertEqual({str(p[1]): p[2] for p in find_all(node, "property")},
                         {"Reference": "REF**", "Value": "part"})
        self.assertNotIn("lcsc_pn", text)
        self.assertNotIn("uuid", text)
        self.assertNotIn("(net", text)
        self.assertEqual(find(find(node, "pad"), "at")[1:], [-0.5, 0])   # the footprint's 90 degrees taken out

    def test_reference_file_records_its_source(self):
        data = json.loads(CORE.read_text(encoding="utf-8"))
        self.assertEqual(set(data["footprints"]), set(extract.PARTS.values()))
        self.assertRegex(data["source_sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("MIT", data["source"])

    @unittest.skipUnless(os.environ.get("RPI_MINIMAL_PCB"),
                         "set RPI_MINIMAL_PCB to Raspberry Pi's RPI-RP2350A-MINIMAL_R4-S1.kicad_pcb to re-extract")
    def test_reference_file_is_what_raspberry_pis_design_gives(self):
        # Re-extract from Raspberry Pi's own file and compare with the committed reference, so the
        # nanometre checks below rest on Raspberry Pi's design, not only on our copy of it.
        source = Path(os.environ["RPI_MINIMAL_PCB"])
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable, "-I", str(REPO_ROOT / "tools/eos_boards/reference/extract_rpi_minimal.py"),
                            str(source), "--footprints", str(Path(tmp) / "fp.pretty"), "--out", str(Path(tmp) / "core.json")],
                           check=True, capture_output=True)
            self.assertEqual(json.loads(Path(tmp, "core.json").read_text(encoding="utf-8")), json.loads(CORE.read_text(encoding="utf-8")))


class ReferenceExactnessTest(unittest.TestCase):
    """Raspberry Pi's copper on the built board, nanometre for nanometre. The board is committed,
    so a missing file is a failure, not a skip."""

    @classmethod
    def setUpClass(cls):
        assert PCB.is_file(), f"built board missing: {PCB}"
        cls.pcb = loads(PCB.read_text(encoding="utf-8"))
        cls.ref = json.loads(CORE.read_text(encoding="utf-8"))
        cls.ox, cls.oy = MCU

    def _at(self, x, y):
        return nm(self.ox + x), nm(self.oy + y)

    def test_footprints_where_the_reference_puts_them(self):
        placed = {}
        for fp in find_all(self.pcb, "footprint"):
            ref = next(str(p[2]) for p in find_all(fp, "property") if str(p[1]) == "Reference")
            placed[ref] = fp
        for name, f in self.ref["footprints"].items():
            fp = placed[name]
            at = find(fp, "at")
            self.assertEqual(str(fp[1]), f["footprint"], name)
            self.assertEqual((nm(at[1]), nm(at[2])), self._at(f["x"], f["y"]), name)
            self.assertEqual(round(float(at[3]) if len(at) > 3 else 0.0) % 360, round(f["rot"]) % 360, name)
            nets = {str(p[1]): str(find(p, "net")[-1]) for p in find_all(fp, "pad") if find(p, "net")}
            for pad, net in f["pads"].items():
                self.assertEqual(nets[pad], net, f"{name} pad {pad}")

    def test_every_track_exact_and_locked(self):
        segs = set()
        for s in find_all(self.pcb, "segment"):
            a = (nm(find(s, "start")[1]), nm(find(s, "start")[2]))
            b = (nm(find(s, "end")[1]), nm(find(s, "end")[2]))
            locked = find(s, "locked") is not None and str(find(s, "locked")[1]) == "yes"
            segs.add((str(find(s, "net")[-1]), str(find(s, "layer")[1]), nm(find(s, "width")[1]),
                      frozenset((a, b)), locked))
        for t in self.ref["tracks"]:
            key = (t["net"], t["layer"], nm(t["w"]), frozenset((self._at(*t["a"]), self._at(*t["b"]))), True)
            self.assertIn(key, segs, t)

    def test_every_via_exact(self):
        vias = {(str(find(v, "net")[-1]), nm(find(v, "at")[1]), nm(find(v, "at")[2]), nm(find(v, "size")[1]),
                 nm(find(v, "drill")[1])) for v in find_all(self.pcb, "via")}
        for d in self.ref["vias"]:
            self.assertIn((d["net"], *self._at(d["x"], d["y"]), nm(d["d"]), nm(d["drill"])), vias, d)

    def test_every_zone_outline_exact(self):
        zones = []
        for z in find_all(self.pcb, "zone"):
            if find(z, "name") is None or find(z, "name")[1] != "eos-reference":
                continue
            pts = tuple((nm(p[1]), nm(p[2])) for p in find_all(find(find(z, "polygon"), "pts"), "xy"))
            zones.append((str(find(z, "net_name")[1]) if find(z, "net_name") else str(find(z, "net")[-1]),
                          str(find(z, "layer")[1]), int(find(z, "priority")[1]), pts))
        self.assertEqual(len(zones), len(self.ref["zones"]))
        for zd in self.ref["zones"]:
            key = (zd["net"], zd["layer"], zd["priority"] + 10, tuple(self._at(x, y) for x, y in zd["outline"]))
            self.assertIn(key, zones, zd["net"])



CAPE_PCB = REPO_ROOT / "boards" / "eos" / "eos-sense-cape" / "hardware" / "eos-sense-cape.kicad_pcb"
PB_HEADERS = REPO_ROOT / "tools" / "eos_boards" / "reference" / "pocketbeagle_headers.json"


def _pad_positions(pcb, refs):
    """{(ref, pad number): (x, y) in nm} for the given footprints, rotation applied as KiCad does."""
    import math
    out = {}
    for fp in find_all(pcb, "footprint"):
        ref = next(str(p[2]) for p in find_all(fp, "property") if str(p[1]) == "Reference")
        if ref not in refs:
            continue
        at = find(fp, "at")
        x0, y0, rot = float(at[1]), float(at[2]), math.radians(float(at[3]) if len(at) > 3 else 0.0)
        for pad in find_all(fp, "pad"):
            px, py = float(find(pad, "at")[1]), float(find(pad, "at")[2])
            out[(ref, str(pad[1]))] = (nm(x0 + px * math.cos(rot) + py * math.sin(rot)),
                                       nm(y0 - px * math.sin(rot) + py * math.cos(rot)))
    return out


class CapeFitTest(unittest.TestCase):
    """The cape's sockets meet PocketBeagle's header pins, pin for pin, to the nanometre."""

    def test_every_socket_pad_on_its_pocketbeagle_pin(self):
        self.assertTrue(CAPE_PCB.is_file(), f"built board missing: {CAPE_PCB}")
        pins = json.loads(PB_HEADERS.read_text(encoding="utf-8"))["pins"]
        pads = _pad_positions(loads(CAPE_PCB.read_text(encoding="utf-8")), {"J1", "J2"})
        self.assertEqual(len(pins), 72)
        for name, (x, y) in pins.items():
            header, number = name.split(".")
            ref = {"P1": "J1", "P2": "J2"}[header]
            self.assertEqual(pads[(ref, number)], (x, y), name)



CM5_PCB = REPO_ROOT / "boards" / "eos" / "eos-cm5-base" / "hardware" / "eos-cm5-base.kicad_pcb"
CM5_REF = REPO_ROOT / "tools" / "eos_boards" / "reference" / "cm5_carrier.json"


class CM5FitTest(unittest.TestCase):
    """The carrier's two connectors and four mounting holes sit where the CM5's own are, to the nanometre."""

    @classmethod
    def setUpClass(cls):
        assert CM5_PCB.is_file(), f"built board missing: {CM5_PCB}"
        from eos_boards.boards import eos_cm5_base as board
        cls.board = board
        cls.ref = json.loads(CM5_REF.read_text(encoding="utf-8"))
        cls.pcb = loads(CM5_PCB.read_text(encoding="utf-8"))

    def _on_board(self, fx_nm, fy_nm):
        x, y = self.board.from_cm5(fx_nm / 1e6, fy_nm / 1e6)
        return nm(x), nm(y)

    def test_every_connector_pad_on_its_cm5_pin(self):
        pads = _pad_positions(self.pcb, {"J1", "J2"})
        self.assertEqual(len(self.ref["pads"]), 200)
        for pin, (fx, fy) in self.ref["pads"].items():
            ref, number = ("J1", pin) if int(pin) <= 100 else ("J2", str(int(pin) - 100))
            self.assertEqual(pads[(ref, number)], self._on_board(fx, fy), f"CM5 pin {pin}")

    def test_mounting_holes(self):
        holes = set()
        for fp in find_all(self.pcb, "footprint"):
            ref = next(str(p[2]) for p in find_all(fp, "property") if str(p[1]) == "Reference")
            if ref.startswith("H"):
                at = find(fp, "at")
                holes.add((nm(at[1]), nm(at[2])))
        self.assertEqual(holes, {self._on_board(h[0], h[1]) for h in self.ref["holes"]})

    def test_connector_nets_follow_the_datasheet(self):
        nets = {}
        for fp in find_all(self.pcb, "footprint"):
            ref = next(str(p[2]) for p in find_all(fp, "property") if str(p[1]) == "Reference")
            if ref in ("J1", "J2"):
                for pad in find_all(fp, "pad"):
                    n = find(pad, "net")
                    nets[int(str(pad[1])) + (100 if ref == "J2" else 0)] = str(n[-1]) if n else None
        names = self.ref["pins"]
        for pin, name in names.items():
            got = nets[int(pin)]
            if name == "GND":
                self.assertEqual(got, "GND", f"pin {pin}")
            elif name == "5V":
                self.assertEqual(got, "+5V", f"pin {pin}")
            elif name in ("CM5_3.3V", "GPIO_VREF"):
                self.assertEqual(got, "+3V3", f"pin {pin}")
            elif name.startswith("GPIO") and name[4:].isdigit():
                self.assertEqual(got, f"/{name}", f"pin {pin}")
        self.assertEqual(nets[94], "/CC1")
        self.assertEqual(nets[96], "/CC2")


CM4_PCB = REPO_ROOT / "boards" / "eos" / "eos-cm4-base" / "hardware" / "eos-cm4-base.kicad_pcb"
CM4_PINS = REPO_ROOT / "tools" / "eos_boards" / "reference" / "cm4_pins.json"


class FigureFourTest(unittest.TestCase):
    """The carriers' holes and connectors, placed from nothing but the dimensions in Figure 4 of the
    CM4 and CM5 datasheets (55 x 40 mm module, holes 3.5 mm in, connector centres 3 mm from the long
    edges and 3.5 + 21.5 mm from the pin-99 edge), land where the footprint facts put them."""

    def test_holes_and_connector_centres_match_the_datasheet_drawing(self):
        for name in ("eos-cm5-base", "eos-cm4-base"):
            with self.subTest(board=name):
                board = importlib.import_module(f"eos_boards.boards.{name.replace('-', '_')}")
                pcb = loads((REPO_ROOT / "boards" / "eos" / name / "hardware" / f"{name}.kicad_pcb").read_text(encoding="utf-8"))
                at = {}
                for fp in find_all(pcb, "footprint"):
                    ref = next(str(p[2]) for p in find_all(fp, "property") if str(p[1]) == "Reference")
                    a = find(fp, "at")
                    at[ref] = (round(float(a[1]), 4), round(float(a[2]), 4))
                holes = {at[r] for r in at if r.startswith("H")}
                drawing = {tuple(round(c, 4) for c in board.from_module(x, y)) for x in (3.5, 51.5) for y in (3.5, 36.5)}
                self.assertEqual(holes, drawing)
                self.assertEqual(at["J1"], tuple(round(c, 4) for c in board.from_module(25.0, 3.0)))    # pins 1-100
                self.assertEqual(at["J2"], tuple(round(c, 4) for c in board.from_module(25.0, 37.0)))   # pins 101-200


class CM4FitTest(CM5FitTest):
    """The CM4 carrier: the same connector pads and holes as the CM5's (Figure 4 of both datasheets),
    every pin's net from the CM4 datasheet's own pinout."""

    @classmethod
    def setUpClass(cls):
        assert CM4_PCB.is_file(), f"built board missing: {CM4_PCB}"
        from eos_boards.boards import eos_cm4_base as board
        cls.board = board
        cls.ref = json.loads(CM5_REF.read_text(encoding="utf-8"))
        cls.pins = json.loads(CM4_PINS.read_text(encoding="utf-8"))["pins"]
        cls.pcb = loads(CM4_PCB.read_text(encoding="utf-8"))

    def test_connector_nets_follow_the_datasheet(self):
        nets = {}
        for fp in find_all(self.pcb, "footprint"):
            ref = next(str(p[2]) for p in find_all(fp, "property") if str(p[1]) == "Reference")
            if ref in ("J1", "J2"):
                for pad in find_all(fp, "pad"):
                    n = find(pad, "net")
                    nets[int(str(pad[1])) + (100 if ref == "J2" else 0)] = str(n[-1]) if n else None
        self.assertEqual(len(self.pins), 200)
        for pin, name in self.pins.items():
            got = nets[int(pin)]
            if name == "GND":
                self.assertEqual(got, "GND", f"pin {pin}")
            elif name == "+5V":
                self.assertEqual(got, "+5V", f"pin {pin}")
            elif name in ("CM4_3.3V", "GPIO_VREF"):
                self.assertEqual(got, "+3V3", f"pin {pin}")
            elif name.startswith("GPIO") and name[4:].isdigit():
                self.assertEqual(got, f"/{name}", f"pin {pin}")
            elif name in ("CM4_1.8V", "Reserved") or name.startswith(("HDMI", "CAM", "DSI", "PCIe")):
                self.assertTrue(got is None or got.startswith("unconnected-"), f"pin {pin} ({name}) carries {got}")
        self.assertEqual((nets[94], nets[96]), ("/CC1", "/CC2"))          # AnalogIP1/0: the USB-C CC lines
        self.assertEqual((nets[101], nets[103], nets[105]), ("/OTG_ID", "/USB_N", "/USB_P"))
        self.assertEqual(nets[92], "/RUN_PG")


def _parts(pcb):
    """{reference: (value, {pad number: net})} from a built board."""
    out = {}
    for fp in find_all(pcb, "footprint"):
        props = {str(p[1]): str(p[2]) for p in find_all(fp, "property")}
        pads = {}
        for pad in find_all(fp, "pad"):
            n = find(pad, "net")
            pads.setdefault(str(pad[1]), str(n[-1]) if n else None)
        out[props["Reference"]] = (props.get("Value"), pads)
    return out


class BoardIntentTest(unittest.TestCase):
    """What each board's documentation promises, read back from the built boards' own pads."""

    @classmethod
    def setUpClass(cls):
        cls.boards = {}
        for name in ("eos-learn-rp2350", "eos-sense-cape", "eos-probe-s3", "eos-cm5-base", "eos-cm4-base", "eos-motion-wing",
                     "eos-esp32-devkit"):
            path = REPO_ROOT / "boards" / "eos" / name / "hardware" / f"{name}.kicad_pcb"
            assert path.is_file(), f"built board missing: {path}"
            cls.boards[name] = _parts(loads(path.read_text(encoding="utf-8")))

    def test_rp2350_power_path_and_usb(self):
        b = self.boards["eos-learn-rp2350"]
        self.assertEqual(b["U3"][0], "AP7361C-33")                       # stable with ceramic capacitors
        self.assertEqual(b["U3"][1], {"1": "+5V", "2": "GND", "3": "+3V3"})
        self.assertEqual(b["D1"][1], {"1": "+5V", "2": "/VBUS_F"})       # cathode +5V: header 5 V cannot reach VBUS
        self.assertEqual(b["F1"][1], {"1": "VBUS", "2": "/VBUS_F"})                 # VBUS is a power net: no "/"
        self.assertEqual((b["R3"][0], b["R4"][0]), ("27", "27"))          # USB series resistors
        self.assertEqual(set(b["R3"][1].values()), {"/USB_D+", "/RP_USB_DP"})
        self.assertEqual(b["R8"][0], "1k")                                 # BOOTSEL resistor on QSPI_SS
        self.assertEqual(set(b["R8"][1].values()), {"/QSPI_SS", "/BOOTSEL"})

    def test_cape_straps_pullups_and_analog(self):
        b = self.boards["eos-sense-cape"]
        self.assertEqual(b["U1"][1]["2"], "+3V3")                          # BME280 CSB to VDDIO: I2C
        self.assertEqual(b["U1"][1]["5"], "/BME_SDO")
        self.assertEqual(b["JP2"][1], {"1": "GND", "2": "/BME_SDO", "3": "+3V3"})   # bridged 1-2: 0x76
        self.assertEqual(b["U2"][1]["8"], "+3V3")                          # LIS3DH CS high: I2C
        self.assertEqual(b["U2"][1]["10"], "GND")                          # RES to GND
        self.assertEqual(b["JP3"][1], {"1": "GND", "2": "/ACC_SA0", "3": "+3V3"})
        self.assertEqual([b["U4"][1][p] for p in "123"], ["+3V3"] * 3)     # 24LC256 at 0x57
        self.assertEqual(b["JP1"][1], {"1": "GND", "2": "/EE_WP", "3": "+3V3"})
        for ref, net in (("R1", "/I2C1_SDA"), ("R2", "/I2C1_SCL"), ("R4", "/I2C2_SDA"), ("R5", "/I2C2_SCL")):
            self.assertEqual((b[ref][0], set(b[ref][1].values())), ("4.7k", {net, "+3V3"}), ref)
        self.assertEqual(b["J1"][1]["2"], "/AIN6")                         # 3.3 V-tolerant inputs only
        self.assertEqual(b["J2"][1]["35"], "/AIN5")
        for pin in ("19", "21", "23", "25", "27"):                          # AIN0-4: 1.8 V only, untouched
            self.assertTrue(b["J1"][1][pin].startswith("unconnected-"), pin)
        self.assertTrue(b["J2"][1]["36"].startswith("unconnected-"))       # AIN7

    def test_probe_translators(self):
        b = self.boards["eos-probe-s3"]
        direction = {"U4": "+3V3", "U5": "/SWDIO_DIR", "U6": "GND", "U7": "+3V3", "U8": "+3V3", "U9": "GND"}
        for ref, d in direction.items():
            pads = b[ref][1]
            self.assertEqual((pads["1"], pads["6"], pads["5"]), ("+3V3", "/VTREF", d), ref)   # VCCA, VCCB, DIR
        self.assertEqual(set(b["R10"][1].values()), {"/SWDIO_DIR", "GND"})                  # reads at power-up
        self.assertEqual(set(b["R17"][1].values()), {"/NRESET_G", "GND"})                   # nRESET switch off
        for pin in ("15", "16", "26"):                                                       # IO3, IO46, IO45 untouched
            self.assertTrue(b["U3"][1][pin].startswith("unconnected-"), pin)

    def test_cm5_usb_c_and_host_port(self):
        b = self.boards["eos-cm5-base"]
        cc = {b["J3"][1][p] for p in ("A5", "B5")}
        self.assertEqual(cc, {"/CC1", "/CC2"})
        self.assertFalse(any(set(pads.values()) & {"/CC1", "/CC2"} for ref, (_, pads) in b.items()
                             if ref not in ("J1", "J3")), "the CM5 negotiates USB-C power itself: no CC resistors")
        self.assertEqual(b["U2"][1], {"1": "/USBH_VBUS", "2": "GND", "3": b["U2"][1]["3"], "4": "/VBUS_EN", "5": "+5V"})

    def test_esp32_auto_program_strapping_and_usb(self):
        b = self.boards["eos-esp32-devkit"]
        u1 = b["U1"][1]                                                    # ESP32-WROOM-32E
        self.assertEqual({u1[p] for p in ("1", "15", "38", "39")}, {"GND"})                 # stacked GND pin
        self.assertEqual((u1["3"], u1["25"], u1["35"], u1["34"]), ("/EN", "/IO0", "/U0TXD", "/U0RXD"))
        u4 = b["U4"][1]                                                    # CP2102N QFN-24: 20 RXD, 21 TXD, 19 RTS, 23 DTR
        self.assertEqual((u4["20"], u4["21"]), ("/U0TXD", "/U0RXD"))     # UART crossed over
        self.assertEqual((u4["19"], u4["23"]), ("/RTS", "/DTR"))
        # esptool's auto-program pair: Q1 pulls EN low, Q2 pulls IO0 low, never both at once
        self.assertEqual(b["Q1"][1], {"1": "/QB1", "2": "/RTS", "3": "/EN"})          # B, E, C
        self.assertEqual(b["Q2"][1], {"1": "/QB2", "2": "/DTR", "3": "/IO0"})
        self.assertEqual(set(b["R10"][1].values()), {"/DTR", "/QB1"})
        self.assertEqual(set(b["R11"][1].values()), {"/RTS", "/QB2"})
        self.assertEqual((b["R4"][0], set(b["R4"][1].values())), ("10k", {"/EN", "+3V3"}))   # EN RC delay
        self.assertEqual((b["C5"][0], set(b["C5"][1].values())), ("1u", {"/EN", "GND"}))
        self.assertEqual((b["R5"][0], set(b["R5"][1].values())), ("10k", {"/IO0", "+3V3"}))  # boots from flash
        straps = {"/IO2", "/IO12", "/IO15", "/IO5"}                        # strapping pins left to their defaults
        pulled = [r for r, (_, pads) in b.items() if r.startswith("R") and set(pads.values()) & straps]
        self.assertEqual([r for r in pulled if not set(b[r][1].values()) & {"/LED_USR_A"}], [])
        self.assertEqual(b["D1"][1], {"1": "+5V", "2": "/VBUS_F"})        # 5V pin cannot back-feed USB
        self.assertEqual((b["R12"][0], set(b["R12"][1].values())), ("5.1k", {"VBUS", "GND"}))   # VBUS bleed

    def test_motion_wing_straps_addresses_and_pullups(self):
        b = self.boards["eos-motion-wing"]
        u1 = b["U1"][1]                                                    # ADXL343 (LGA-14)
        self.assertEqual((u1["1"], u1["6"], u1["7"]), ("+3V3", "+3V3", "+3V3"))       # VDD I/O, VS, CS high: I2C
        self.assertEqual((u1["12"], u1["13"], u1["14"]), ("/ACC_SDO", "/I2C_SDA", "/I2C_SCL"))
        self.assertEqual(b["JP3"][1], {"1": "GND", "2": "/ACC_SDO", "3": "+3V3"})       # ALT ADDRESS: 0x53 as delivered
        u2 = b["U2"][1]                                                    # ADT7410 (SOIC-8)
        self.assertEqual((u2["1"], u2["2"], u2["7"], u2["8"]), ("/I2C_SCL", "/I2C_SDA", "GND", "+3V3"))
        for jp, net in (("JP2", "/TMP_A0"), ("JP4", "/TMP_A1")):          # 0x48 as delivered
            self.assertEqual(b[jp][1], {"1": "GND", "2": net, "3": "+3V3"}, jp)
        for r in ("R1", "R2"):                                             # removable I2C pull-ups
            self.assertEqual(b[r][0], "10k")
            self.assertIn("/I2C_PU", b[r][1].values())
        self.assertEqual(set(b["JP1"][1].values()), {"+3V3", "/I2C_PU"})

    def test_cm4_usb_switch_power_and_controls(self):
        b = self.boards["eos-cm4-base"]
        u7 = b["U7"][1]                                                    # TS3USB30E (VSSOP pins)
        self.assertEqual((u7["1"], u7["9"], u7["10"], u7["5"]), ("/OTG_ID", "GND", "+3V3", "GND"))   # S, ~OE, VCC, GND
        self.assertEqual((u7["4"], u7["6"]), ("/USB_P", "/USB_N"))                                   # common side: the CM4
        self.assertEqual((u7["2"], u7["8"]), ("/USBH_DP", "/USBH_DM"))   # D1: S low (host jumper fitted) -> USB-A
        self.assertEqual((u7["3"], u7["7"]), ("/USBC_DP", "/USBC_DM"))   # D2: S high (default device) -> USB-C
        self.assertEqual(b["U2"][0], "TPS2051C")                            # enable active high
        self.assertEqual(b["U2"][1]["4"], "/USBH_EN")
        self.assertEqual(b["Q2"][1], {"1": "/OTG_ID", "2": "GND", "3": "/USBH_EN"})   # inverter: OTG_ID high holds it off
        self.assertEqual((b["R11"][0], set(b["R11"][1].values())), ("10k", {"/USBH_EN", "+3V3"}))   # off when 3.3 V is down
        self.assertEqual(set(b["C10"][1].values()), {"/USBH_VBUS", "GND"})  # TI's output ceramic
        self.assertEqual(b["J9"][1], {"1": "/NRPIBOOT", "2": "GND", "3": "/EEPROM_NWP", "4": "GND", "5": "/OTG_ID", "6": "GND"})
        for ref, cc in (("R6", "/CC1"), ("R7", "/CC2")):                   # USB-C sink: Rd on each CC
            self.assertEqual((b[ref][0], set(b[ref][1].values())), ("5.1k", {cc, "GND"}), ref)
        self.assertEqual((b["R8"][0], set(b["R8"][1].values())), ("220", {"/RUN_PG", "/RUN_RST"}))
        self.assertEqual(b["Q1"][1]["1"], "/PI_LED_NPWR")                  # BSS84 gate: the buffered power LED
        self.assertNotIn("BT1", b)                                          # the CM4 has no RTC battery input



def _segment_meets_box(a, b, box):
    """True when segment a-b touches the axis-aligned box (x0, y0, x1, y1): Liang-Barsky clipping."""
    (x0, y0, x1, y1), (ax, ay), (bx, by) = box, a, b
    t0, t1, dx, dy = 0.0, 1.0, bx - ax, by - ay
    for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


def _point_in_polygon(x, y, pts):
    inside = False
    for (xa, ya), (xb, yb) in zip(pts, pts[1:] + pts[:1]):
        if (ya > y) != (yb > y) and x < xa + (y - ya) * (xb - xa) / (yb - ya):
            inside = not inside
    return inside


class AntennaKeepoutTest(unittest.TestCase):
    """The CM5 datasheet (section 4.1.2) forbids metal, ground planes included, under the module's
    PCB antenna. The carrier keeps a rule area there on every copper layer, and nothing is in it."""

    def test_no_copper_under_the_module_antenna(self):
        for name in ("eos-cm5-base", "eos-cm4-base"):
            with self.subTest(board=name):
                self._check(name)

    def _check(self, name):
        module = importlib.import_module(f"eos_boards.boards.{name.replace('-', '_')}")
        pcb = loads((REPO_ROOT / "boards" / "eos" / name / "hardware" / f"{name}.kicad_pcb").read_text(encoding="utf-8"))
        x0, y0, x1, y1 = module.ANTENNA_KEEPOUT
        corners = [module.from_module(x, y) for x, y in ((0.0, 10.5), (6.5, 21.5))]      # Figure 4's cut-out
        self.assertTrue(all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in corners), (module.ANTENNA_KEEPOUT, corners))
        self.assertGreaterEqual((x1 - x0, y1 - y0), (8.0, 15.0))                          # the datasheet's ideal size
        areas = [z for z in find_all(pcb, "zone") if find(z, "name") and str(find(z, "name")[1]) == "eos-copper-keepout"]
        self.assertEqual(len(areas), 1)
        rules = {str(item[0]): str(item[1]) for item in find(areas[0], "keepout")[1:]}
        self.assertEqual(rules, {"tracks": "not_allowed", "vias": "not_allowed", "pads": "not_allowed",
                                 "copperpour": "not_allowed", "footprints": "allowed"})
        layers = [str(x) for x in find(areas[0], "layers")[1:]]
        self.assertTrue(layers == ["*.Cu"] or set(layers) == {"F.Cu", "In1.Cu", "In2.Cu", "B.Cu"}, layers)
        outline = [(float(p[1]), float(p[2])) for p in find_all(find(find(areas[0], "polygon"), "pts"), "xy")]
        self.assertEqual((min(x for x, _ in outline), min(y for _, y in outline), max(x for x, _ in outline),
                          max(y for _, y in outline)), (x0, y0, x1, y1))
        for seg in find_all(pcb, "segment"):
            a, b = find(seg, "start"), find(seg, "end")
            self.assertFalse(_segment_meets_box((float(a[1]), float(a[2])), (float(b[1]), float(b[2])), (x0, y0, x1, y1)),
                             f"track in the antenna keep-out: {a} {b}")
        for via in find_all(pcb, "via"):
            at, r = find(via, "at"), float(find(via, "size")[1]) / 2
            self.assertFalse(x0 - r < float(at[1]) < x1 + r and y0 - r < float(at[2]) < y1 + r, f"via in the keep-out: {at}")
        probes = [(x0 + (x1 - x0) * i / 8, y0 + (y1 - y0) * j / 8) for i in range(1, 8) for j in range(1, 8)]
        for z in find_all(pcb, "zone"):
            for fill in find_all(z, "filled_polygon"):
                pts = [(float(p[1]), float(p[2])) for p in find_all(find(fill, "pts"), "xy")]
                hits = [q for q in probes if _point_in_polygon(*q, pts)]
                self.assertFalse(hits, f"{str(find(fill, 'layer')[1])} pour under the antenna at {hits[:3]}")


EOS_DIR = REPO_ROOT / "boards" / "eos"
EOS_BOARDS = {d.name: d.name.replace("-", "_") for d in sorted(EOS_DIR.iterdir()) if (d / "README.md").is_file()}


class UsbCEdgeTest(unittest.TestCase):
    """Every HRO TYPE-C-31-M-12 faces a board edge at the distance HRO's recommended layout gives
    (design.USB_C_EDGE), so the shell stands proud of the edge and a plug seats fully."""

    def test_each_usb_c_receptacle_sits_at_hros_edge_distance(self):
        seen = 0
        for path in sorted((REPO_ROOT / "tools" / "eos_boards" / "boards").glob("eos_*.py")):
            board = importlib.import_module(f"eos_boards.boards.{path.stem}").BOARD
            for part in board.parts:
                if not part.footprint.endswith(":USB_C_Receptacle_HRO_TYPE-C-31-M-12"):
                    continue
                x, y, rot = part.pcb
                # the mating face is the footprint's +y side; rotated, it faces one board edge
                to_edge = {0: board.height - y, 90: board.width - x, 180: y, 270: x}[round(rot) % 360]
                with self.subTest(board=path.stem, part=part.ref):
                    self.assertAlmostEqual(to_edge, design.USB_C_EDGE, delta=0.05)   # HRO's layout tolerance
                seen += 1
        self.assertGreater(seen, 0)


class ExposedPadTest(unittest.TestCase):
    """A chip's exposed ground pad is joined to ground through the board, not by a lone track:
    the generator puts vias in it (or its footprint brings through-hole thermal vias)."""

    def test_every_exposed_ground_pad_has_a_via_in_it(self):
        for folder in sorted((REPO_ROOT / "boards" / "eos").iterdir()):
            pcb_path = folder / "hardware" / f"{folder.name}.kicad_pcb"
            if not pcb_path.is_file():
                continue
            pcb = loads(pcb_path.read_text(encoding="utf-8"))
            vias = [(float(find(v, "at")[1]), float(find(v, "at")[2])) for v in find_all(pcb, "via")
                    if str(find(v, "net")[-1]) == "GND"]
            for fp in find_all(pcb, "footprint"):
                ref = next(str(p[2]) for p in find_all(fp, "property") if str(p[1]) == "Reference")
                at = find(fp, "at")
                fx, fy, rot = float(at[1]), float(at[2]), math.radians(float(at[3]) if len(at) > 3 else 0)
                pads = find_all(fp, "pad")
                if len({str(q[1]) for q in pads}) < 4:
                    continue                             # a chip has four pads or more; a test pad has one
                biggest = max(float(find(q, "size")[1]) * float(find(q, "size")[2]) for q in pads)
                for pad in pads:
                    net = find(pad, "net")
                    w, h = (float(v) for v in find(pad, "size")[1:3])
                    if str(pad[2]) != "smd" or net is None or str(net[-1]) != "GND" or min(w, h) <= 1.5 \
                            or w * h < biggest:
                        continue
                    with self.subTest(board=folder.name, pad=f"{ref}.{pad[1]}"):
                        if any(str(q[1]) == str(pad[1]) and str(q[2]) == "thru_hole" for q in pads):
                            continue                     # the footprint's own thermal vias
                        px, py = (float(v) for v in find(pad, "at")[1:3])
                        cx = fx + px * math.cos(rot) + py * math.sin(rot)
                        cy = fy - px * math.sin(rot) + py * math.cos(rot)
                        inside = [v for v in vias if abs(v[0] - cx) < w / 2 and abs(v[1] - cy) < h / 2]
                        self.assertTrue(inside, "no via in the exposed pad")


VIA_PAD_GAP = 0.1   # mm of solder mask between a via and a surface pad (pcb_build.VIA_PAD_GAP)


def _vias_in_pads(pcb, skip=()):
    """The surface pads, other than a chip's exposed pad, that some via's copper overlaps or comes
    within VIA_PAD_GAP of. Vias centred at a position in ``skip`` (mm, to 0.001) are left out."""
    vias = [(float(find(v, "at")[1]), float(find(v, "at")[2]), float(find(v, "size")[1]) / 2)
            for v in find_all(pcb, "via")
            if (round(float(find(v, "at")[1]), 3), round(float(find(v, "at")[2]), 3)) not in skip]
    hits = set()
    for fp in find_all(pcb, "footprint"):
        ref = next(str(p[2]) for p in find_all(fp, "property") if str(p[1]) == "Reference")
        at = find(fp, "at")
        fx, fy, rot = float(at[1]), float(at[2]), math.radians(float(at[3]) if len(at) > 3 else 0)
        pads = find_all(fp, "pad")
        numbers = {str(q[1]) for q in pads}
        biggest = max(float(find(q, "size")[1]) * float(find(q, "size")[2]) for q in pads) if pads else 0
        for pad in pads:
            if str(pad[2]) != "smd" or str(pad[1]) == "":
                continue                                 # a through-hole pad, or a paste-only opening
            # a custom pad (a solder jumper's) is checked as its anchor rectangle only
            w, h = (float(v) for v in find(pad, "size")[1:3])
            if len(numbers) >= 4 and min(w, h) > 1.5 and w * h >= biggest:
                continue                                 # the exposed pad, which takes vias on purpose
            pa = find(pad, "at")
            px, py = float(pa[1]), float(pa[2])
            cx = fx + px * math.cos(rot) + py * math.sin(rot)
            cy = fy - px * math.sin(rot) + py * math.cos(rot)
            a = math.radians(float(pa[3]) if len(pa) > 3 else 0)   # a pad's angle is written in board space
            # corner radius: a rounded rectangle's ratio of its short side; a circle or oval is all corner
            shape = str(pad[3])
            rratio = find(pad, "roundrect_rratio")
            corner = {"circle": min(w, h) / 2, "oval": min(w, h) / 2,
                      "roundrect": float(rratio[1]) * min(w, h) if rratio else 0.0}.get(shape, 0.0)
            for vx, vy, vr in vias:
                # the via's disk against the pad's outline, in the pad's own axes
                # (the inverse of KiCad's rotation: a positive angle turns counter-clockwise on screen)
                u = abs((vx - cx) * math.cos(a) - (vy - cy) * math.sin(a)) - (w / 2 - corner)
                s = abs((vx - cx) * math.sin(a) + (vy - cy) * math.cos(a)) - (h / 2 - corner)
                if math.hypot(max(u, 0), max(s, 0)) - corner < vr + VIA_PAD_GAP - 0.005:
                    hits.add(f"{ref}.{pad[1]}")
    return hits


class ViaInPadTest(unittest.TestCase):
    """No via sits in a surface pad, or within VIA_PAD_GAP of one, except the vias a chip's exposed
    pad takes on purpose: solder wicks down an open barrel and starves the joint. Every board is
    built under the rule, the ten built before it included."""

    # Raspberry Pi's RP2350A reference copper, kept exactly as drawn (the board README's "The core
    # layout is Raspberry Pi's, exactly"): two of its locked ground vias sit 0.05 mm from the
    # regulator capacitors' ground pads (C6.2, C7.2). Only these two vias, by position, are left
    # out; any other via in or beside any pad, those two pads included, still fails.
    REFERENCE_COPPER = {"eos-learn-rp2350": {(29.4, 24.8), (29.4, 25.4)}}

    def test_the_gap_matches_the_generators(self):
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        self.assertIn(f"VIA_PAD_GAP = {VIA_PAD_GAP}\n", source)

    def test_no_via_sits_in_a_surface_pad(self):
        for folder in sorted((REPO_ROOT / "boards" / "eos").iterdir()):
            pcb_path = folder / "hardware" / f"{folder.name}.kicad_pcb"
            if not pcb_path.is_file():
                continue
            hits = _vias_in_pads(loads(pcb_path.read_text(encoding="utf-8")),
                                 skip=self.REFERENCE_COPPER.get(folder.name, set()))
            with self.subTest(board=folder.name):
                self.assertFalse(hits, f"vias in {', '.join(sorted(hits))}")



class PourKeepoutTest(unittest.TestCase):
    """A board's pour keep-outs hold no pour on their layer: the fill polygons have no corner
    inside one and do not cover its middle (KiCad saves fills fractured, without holes)."""

    def test_no_pour_fills_a_pour_keepout(self):
        for path in sorted((REPO_ROOT / "tools" / "eos_boards" / "boards").glob("eos_*.py")):
            board = importlib.import_module(f"eos_boards.boards.{path.stem}").BOARD
            name = path.stem.replace("_", "-")
            pcb_path = REPO_ROOT / "boards" / "eos" / name / "hardware" / f"{name}.kicad_pcb"
            if not board.pour_keepouts or not pcb_path.is_file():
                continue
            pcb = loads(pcb_path.read_text(encoding="utf-8"))
            areas = [z for z in find_all(pcb, "zone") if find(z, "name") is not None
                     and str(find(z, "name")[1]) == "eos-pour-keepout"]
            for x0, y0, x1, y1, layer in board.pour_keepouts:
                with self.subTest(board=name, rule_area=(x0, y0, x1, y1, layer)):   # kept on the saved board
                    self.assertTrue(any(str(find(z, "layer")[1]) == layer for z in areas if find(z, "layer") is not None))
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                for zone in find_all(pcb, "zone"):
                    for poly in find_all(zone, "filled_polygon"):
                        if str(find(poly, "layer")[1]) != layer:
                            continue
                        pts = [(float(q[1]), float(q[2])) for q in find_all(find(poly, "pts"), "xy")]
                        with self.subTest(board=name, keepout=(x0, y0, x1, y1, layer)):
                            self.assertFalse(any(x0 + 0.01 < x < x1 - 0.01 and y0 + 0.01 < y < y1 - 0.01 for x, y in pts))
                            self.assertFalse(_point_in_polygon(cx, cy, pts))


class OwnershipTest(unittest.TestCase):
    """The boards are Kartikeydheer Srivastava's, all rights reserved. Everywhere a reader or a
    fab sees the licence says so, and nothing still gives the boards themselves the MIT licence."""

    def test_each_board_carries_the_all_rights_reserved_licence(self):
        for name, module in EOS_BOARDS.items():
            with self.subTest(board=name):
                board = importlib.import_module(f"eos_boards.boards.{module}").BOARD
                self.assertEqual((board.company, board.licence, board.contact),
                                 ("Kartikeydheer Srivastava", design.ALL_RIGHTS_RESERVED, "kartikeydheer@gmail.com"))
                folder = REPO_ROOT / "boards" / "eos" / name
                licence = (folder / "LICENSE.txt").read_text(encoding="utf-8")
                self.assertEqual(licence, build.licence_text(board, module))     # what the build writes
                self.assertEqual("tools/eos_boards/footprints/EoS_Connectors.pretty" in licence,
                                 "EoS_Connectors" in board.local_footprints)        # the owner's own library, where used
                self.assertIn("To ask,\n   write to kartikeydheer@gmail.com.", licence)
                self.assertIn(f"tools/eos_boards/boards/{module}.py", licence)
                sch = (folder / "hardware" / f"{name}.kicad_sch").read_text(encoding="utf-8")
                self.assertIn('(comment 1 "Copyright (c) 2026 Kartikeydheer Srivastava. Licence: All rights reserved")', sch)
                pcb = loads((folder / "hardware" / f"{name}.kicad_pcb").read_text(encoding="utf-8"))
                silk = [str(t[1]) for t in find_all(pcb, "gr_text") if str(find(t, "layer")[1]) == "B.SilkS"]
                self.assertIn("(c) 2026 Kartikeydheer Srivastava", silk)
                self.assertIn("All rights reserved", silk)
                self.assertFalse([s for s in silk if "Srivastava" in s and "MIT" in s], silk)
                readme = (folder / "README.md").read_text(encoding="utf-8")
                self.assertIn("All rights reserved: not open source", readme)
                self.assertNotIn("MIT licence (see", readme)

    def test_every_design_file_has_a_built_board_and_the_other_way_round(self):
        designs = {p.stem for p in (REPO_ROOT / "tools" / "eos_boards" / "boards").glob("eos_*.py")}
        self.assertEqual(designs, set(EOS_BOARDS.values()))

    def test_index_lists_every_board_with_its_recorded_checks(self):
        rows = {}
        for line in (EOS_DIR / "README.md").read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            link = re.match(r"\[[^\]]+\]\(([^)/]+)\)$", cells[0]) if len(cells) == 7 else None
            if link:
                rows[link.group(1)] = tuple(int(c) for c in cells[3:7])
        self.assertEqual(set(rows), set(EOS_BOARDS))
        for name, (erc, drc, unconnected, parity) in rows.items():
            report = json.loads((EOS_DIR / name / "build-report.json").read_text(encoding="utf-8"))
            drc_json = json.loads((EOS_DIR / name / "drc.json").read_text(encoding="utf-8"))
            self.assertEqual((erc, drc, unconnected, parity),
                             (report["erc_violations"], report["drc_errors"], len(drc_json["unconnected_items"]),
                              len(drc_json["schematic_parity"])), name)

    def test_each_readme_states_the_checks_its_build_recorded(self):
        for name in EOS_BOARDS:
            with self.subTest(board=name):
                readme = (EOS_DIR / name / "README.md").read_text(encoding="utf-8")
                report = json.loads((EOS_DIR / name / "build-report.json").read_text(encoding="utf-8"))
                drc_json = json.loads((EOS_DIR / name / "drc.json").read_text(encoding="utf-8"))
                row = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\| ([^|]+?) \| (\d+)\b", readme, re.M)}
                self.assertEqual((row["Schematic ERC"], row["DRC errors"], row["Unconnected items"],
                                  row["Schematic ↔ board parity"], row["DRC warnings"]),
                                 (report["erc_violations"], report["drc_errors"], len(drc_json["unconnected_items"]),
                                  len(drc_json["schematic_parity"]), report["drc_warnings"]))

    def test_generic_symbols_copied_into_a_board_stay_mit(self):
        licence = (REPO_ROOT / "boards" / "eos" / "eos-cm5-base" / "LICENSE.txt").read_text(encoding="utf-8")
        self.assertIn("Schematic symbols in hardware/symbols (EoS_Connectors.kicad_sym, EoS_Parts.kicad_sym): "
                      "written by this repository's generator, tools/eos_boards/symbols, MIT licence", licence)

    def test_each_footprint_library_is_the_owners_third_party_or_generic(self):
        folder = REPO_ROOT / "tools" / "eos_boards" / "footprints"
        for lib in sorted(folder.glob("*.pretty")):
            with self.subTest(library=lib.stem):
                kinds = [(folder / f"{lib.stem}.NOTICE.txt").exists(), (folder / f"{lib.stem}.LICENSE.txt").exists(),
                         lib.stem in build.GENERIC_FOOTPRINTS]
                self.assertEqual(sum(kinds), 1, kinds)        # all rights reserved, its own licence, or MIT

    def test_generic_footprints_are_what_the_generator_writes_and_stay_mit(self):
        fp = importlib.import_module("eos_boards.footprints.generate")
        committed = REPO_ROOT / "tools" / "eos_boards" / "footprints" / "EoS_Packages.pretty" / f"{fp.NAME}.kicad_mod"
        self.assertEqual(dumps(fp.footprint()) + "\n", committed.read_text(encoding="utf-8"))
        board = importlib.import_module("eos_boards.boards.eos_lpc55s69_board").BOARD
        licence = build.licence_text(board, "eos_lpc55s69_board")
        self.assertIn("Footprint libraries in hardware/footprints (EoS_Packages.pretty): written by this "
                      "repository's generator, tools/eos_boards/footprints, MIT licence", licence)
        self.assertNotIn("tools/eos_boards/footprints/EoS_Packages.pretty, a footprint library drawn", licence)

    def test_repository_docs_state_the_exception(self):
        contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("### Exception: the EmbeddedOS original boards", contributing)
        self.assertIn("may use and relicense the change on any terms", contributing)
        self.assertIn("all rights reserved, and are not under the MIT licence", (REPO_ROOT / "README.md").read_text(encoding="utf-8"))
        notice = REPO_ROOT / "tools" / "eos_boards" / "footprints" / "EoS_Connectors.NOTICE.txt"
        self.assertIn("All rights reserved", notice.read_text(encoding="utf-8"))
        self.assertFalse((notice.parent / "EoS_Connectors.LICENSE.txt").exists())   # would be listed as third-party

if __name__ == "__main__":
    unittest.main()
