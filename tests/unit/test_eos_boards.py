"""tools/eos_boards: the board generator's pure-Python parts, and the exactness of the copper
reused from Raspberry Pi's RP2350A minimal design on the built EoS Learn RP2350.

None of this needs KiCad: symbols come from a small library written here, and the built board
is read as text. The exactness check compares in integer nanometres (KiCad's own unit), so a
1 nm move of any reused footprint, track end, via or zone corner fails it.
"""

from __future__ import annotations

import contextlib
import dataclasses
import importlib
import io
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

from eos_boards import build, design, fabrication, metrics, schematic  # noqa: E402
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
        args = dict(name="t", title="T", date="2026-10-11", company="Kartikeydheer Srivastava", licence="MIT",
                    width=10, height=10, parts=parts, power_nets={}, flagged_nets=[])     # revision: the default, "A"
        args.update(kw)
        return Board(**args)


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
        # TI SPRS945H Table 5-1, 100 PZ column; TI SPMS433B Table 26-3 (128-pin TQFP).
        # A shifted supply pin can damage hardware.
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
            "TM4C1294NCPDT": (128, {
                "7": ("VDD", "power_in"), "8": ("VDDA", "power_in"), "9": ("VREFA+", "power_in"),
                "10": ("GNDA", "power_in"), "17": ("GND", "power_in"), "65": ("~{HIB}", "output"),
                "68": ("VBAT", "power_in"), "70": ("~{RST}", "input"), "87": ("VDDC", "power_in"),
                "97": ("PC3/TDO/SWO", "bidirectional"), "99": ("PC1/TMS/SWDIO", "bidirectional"),
                "100": ("PC0/TCK/SWCLK", "bidirectional"), "115": ("VDDC", "power_in"),
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

    def test_the_spec_carries_the_stackup_and_refuses_a_board_without_one(self):
        parts = [Part("U1", "T:M", "M", "fp", (5, 5), {"GND": "GND", "A/B": NC})]
        spec = build.spec_for(self.board(parts), self.lib, Path(self.tmp.name), [])
        self.assertEqual([r["name"] for r in spec["stackup"]["layers"] if r["type"] == "copper"], ["F.Cu", "B.Cu"])
        with self.assertRaisesRegex(SystemExit, "t: stack-up: no published standard stack-up for 2 layers at 0.8 mm"):
            build.spec_for(self.board(parts, thickness=0.8), self.lib, Path(self.tmp.name), [])

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
        self.assertEqual(build.clearance_clashes(drc), [
            {"net": "/PH0", "pos": [30.09, 1.0], "via": True, "length": 0.0,
             "other": {"net": "/PA1", "pos": [30.08, 1.0], "via": False, "length": 5.2445}},
            {"net": "/B", "pos": [2.0, 1.0], "via": False, "length": 0.4,
             "other": {"net": "/A", "pos": [1.0, 1.0], "via": False, "length": 9.0}}])

    def test_locked_fanout_copper_can_be_lifted_round_and_pruned(self):
        # review m10/D5: a clash naming a locked fan-out via lifts the other item; a dangling fan-out via
        # or stub is pruned; a via_dangling warning fails the build
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        ripup = source[source.index("def ripup("):source.index("def repair(")]
        self.assertIn("fabrication.lift_with_fallback(c, lift, fixed)", ripup)
        self.assertIn('t.IsLocked() and t.GetNetname() == item["net"] and via == item.get("via", False)', ripup)
        # the behaviour (review n3, N14): the named item first, the other only when the first lifts nothing
        calls = []

        def lift(net, pos, fixed=("GND",)):
            calls.append(net)
            return 0 if net in fixed else 3
        clash = {"net": "GND", "pos": [1.0, 2.0], "other": {"net": "/A", "pos": [1.0, 2.2]}}
        self.assertEqual((fabrication.lift_with_fallback(clash, lift), calls), (3, ["GND", "/A"]))
        calls.clear()
        self.assertEqual((fabrication.lift_with_fallback(dict(clash, net="/B"), lift), calls), (3, ["/B"]))
        calls.clear()
        self.assertEqual((fabrication.lift_with_fallback({"net": "GND", "pos": [0, 0]}, lift), calls), (0, ["GND"]))
        # PR #74 review (coderabbit): a locked named item is never lifted round, even when its net has
        # loose copper nearby that lift() would take; the item it clashes with goes instead
        calls.clear()
        locked = dict(clash, net="/B", via=True)
        self.assertEqual((fabrication.lift_with_fallback(locked, lift, lambda item: item.get("via")), calls), (3, ["/A"]))
        calls.clear()
        self.assertEqual((fabrication.lift_with_fallback(dict(locked, via=False), lift, lambda item: item.get("via")), calls),
                         (3, ["/B"]))
        fanout = source[source.index("def fanout("):source.index("REFERENCE_ZONE = ")]
        self.assertEqual(fanout.count('spec.setdefault("fanout_copper", []).append('), 2)      # its vias and stubs
        prune = source[source.index("def prune_dangling("):source.index("def finish(")]
        self.assertIn("(not t.IsLocked() or _fanout_item(t, fanout))", prune)
        self.assertEqual(source.count("prune_dangling(board, spec)"), 2)                        # finish and repair
        drc = {"violations": [{"type": "via_dangling", "severity": "warning", "items": [{"description": "Via [GND] on F.Cu - B.Cu"}]},
                              {"type": "track_dangling", "severity": "warning", "items": [{"description": "Track [+3V3] on F.Cu"}]}]}
        self.assertEqual(build.dangling_via_problems(drc), ["via_dangling: Via [GND] on F.Cu - B.Cu"])
        self.assertIn("+ dangling_via_problems(drc)", (REPO_ROOT / "tools" / "eos_boards" / "build.py").read_text(encoding="utf-8"))


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

def pcb_stackup(pcb):
    """(copper layer names of the board's layer table, its stack-up's rows as (name, type, thickness),
    copper finish) read from a parsed .kicad_pcb; the rows are [] when it has no stack-up."""
    table = [str(item[1]) for item in find(pcb, "layers")[1:] if isinstance(item, list) and str(item[1]).endswith(".Cu")]
    stack = find(find(pcb, "setup"), "stackup")
    if stack is None:
        return table, [], None
    rows = [(str(r[1]), str(find(r, "type")[1]), float(find(r, "thickness")[1]) if find(r, "thickness") else None)
            for r in find_all(stack, "layer")]
    return table, rows, str(find(stack, "copper_finish")[1])


# Boards built before the P3 stage 1 generator (stack-up, fiducials, identity line, PCB title block);
# P4 rebuilds every board and takes it out of this set. The tests check the set too: a listed board
# that already has a stack-up fails them, so the set cannot go stale.
BUILT_BEFORE_P3 = {
    "eos-atmega328p-board", "eos-cm4-base", "eos-cm5-base", "eos-esp32-devkit", "eos-f280049c-board",
    "eos-feather-rp2040", "eos-ke16z-board", "eos-kl25-board", "eos-learn-rp2350", "eos-lpc55s69-board",
    "eos-motion-wing", "eos-msp430g2-board", "eos-probe-s3", "eos-ra2e1-board", "eos-ra4m2-board",
    "eos-rl78g13-board", "eos-sense-cape", "eos-stm32-64", "eos-tm4c123-board", "eos-tm4c1294-board"}


# Designs whose README tabulates a stack-up other than the one the generator writes (TM4C1294 asks for a
# ~0.10 mm top prepreg and 1 oz inner copper; the generator now writes JLC06161H-2116B, 0.5 oz inner).
# P4 sets the design's stackup option (impedance_controlled), settles the inner copper (widen the inner
# 5 V tracks for 0.5 oz, or order 1 oz) and rewrites the README's table; then this set empties.
STACKUP_TO_DECLARE = {"eos-tm4c1294-board"}


class StackupTest(unittest.TestCase):
    """A1: the board file carries the fab's stack-up (JLCPCB's published 1.6 mm stack-ups)."""

    def test_jlcpcb_numbers_as_published(self):
        rows = {n: [(r["type"], r["thickness"], r.get("epsilon_r")) for r in fabrication.STACKUPS[n]["layers"]] for n in (2, 4, 6)}
        cu, inner, p7628, core = ("copper", 0.035, None), ("copper", 0.0152, None), ("prepreg", 0.2104, 4.4), ("core", 1.065, 4.6)
        self.assertEqual(rows[4], [cu, p7628, inner, core, inner, p7628, cu])                  # JLC04161H-7628
        p2116 = ("prepreg", 0.1164, 4.16)
        self.assertEqual(rows[6], [cu, p2116, inner, ("core", 0.5, 4.6), inner, ("prepreg", 0.1528, 3.91), inner,
                                   ("core", 0.5, 4.6), inner, p2116, cu])                       # JLC06161H-2116B (1080 x 2 in the middle)
        self.assertEqual(rows[2], [cu, ("core", 1.51, 4.5), cu])
        for n in (2, 4, 6):
            with self.subTest(layers=n):
                st = fabrication.stackup_for(n, 1.6)
                self.assertEqual([r["name"] for r in st["layers"] if r["type"] == "copper"], fabrication.copper_names(n))
                self.assertAlmostEqual(fabrication.stackup_thickness(st), 1.6, delta=0.16)     # JLCPCB: +-10 %
                self.assertEqual((st["finish"], st["mask_color"], st["silk_color"]), ("ENIG", "Green", "White"))
                self.assertIn("jlcpcb.com", st["source"])

    def test_overrides_and_refusals(self):
        self.assertEqual(fabrication.stackup_for(2, 1.6, {"finish": "HAL lead-free"})["finish"], "HAL lead-free")
        own = {"source": "Fab X standard 4-layer, read 2026-10-24", "layers": [
            {"type": "copper", "name": n, "thickness": 0.035} if i % 2 == 0 else
            {"type": "core", "thickness": 0.5, "material": "FR4", "epsilon_r": 4.3}
            for i, n in enumerate(["F.Cu", None, "In1.Cu", None, "In2.Cu", None, "B.Cu"])]}
        self.assertEqual(fabrication.stackup_for(4, 1.6, own)["source"], own["source"])
        bad = [((2, 1.0, None), "no published standard"), ((4, 1.6, {"layers": own["layers"]}), "needs a source"),
               ((2, 1.6, own), "copper layers"), ((2, 1.6, {"finish": "Gold"}), "finish"),
               ((2, 1.6, {"colour": "Red"}), "unknown option"),
               ((4, 1.6, dict(own, layers=own["layers"][:1] + [own["layers"][1]] * 2 + own["layers"][2:])), "copper layers|alternate"),
               # JLCPCB holds 1.6 mm boards to +-10 %: a 1.0 mm core makes 1.09 mm, a 2.0 mm one 2.09 mm
               ((2, 1.6, {"source": "x", "layers": [own["layers"][0], dict(own["layers"][1], thickness=1.0), dict(own["layers"][0], name="B.Cu")]}),
                "adds up to 1.0900 mm, outside 1.6 mm"),
               ((2, 1.6, {"source": "x", "layers": [own["layers"][0], dict(own["layers"][1], thickness=2.0), dict(own["layers"][0], name="B.Cu")]}),
                "adds up to 2.0900 mm"),
               ((2, 1.6, {"impedance_controlled": "yes"}), "impedance_controlled")]
        ok = {"source": "x", "layers": [own["layers"][0], dict(own["layers"][1], thickness=1.45), dict(own["layers"][0], name="B.Cu")]}
        self.assertAlmostEqual(fabrication.stackup_thickness(fabrication.stackup_for(2, 1.6, ok)), 1.54)   # inside +-10 %
        for args, message in bad:
            with self.subTest(args=str(args)[:60]), self.assertRaisesRegex(ValueError, message):
                fabrication.stackup_for(*args)

    def test_an_impedance_controlled_board_puts_er_in_the_job_file(self):
        # KiCad copies er, loss tangent and "ImpedanceControlled" into the job file only with this flag (review m2)
        self.assertIn("(dielectric_constraints no)", fabrication.stackup_text(fabrication.stackup_for(6, 1.6)))
        self.assertIn("(dielectric_constraints yes)",
                      fabrication.stackup_text(fabrication.stackup_for(6, 1.6, {"impedance_controlled": True})))

    def test_a_readme_stack_up_table_names_the_stackup_the_board_carries(self):
        # A README that tabulates its stack-up must name the JLCPCB stack-up the generator writes, so the
        # README and the board file cannot ask the fab for two different boards (review MAJOR-1).
        found = set()
        for name, module in EOS_BOARDS.items():
            text = (EOS_DIR / name / "README.md").read_text(encoding="utf-8")
            if not re.search(r"^\| (F|In\d|B)\.Cu \|", text, re.M):
                continue
            board = importlib.import_module(f"eos_boards.boards.{module}").BOARD
            source = fabrication.stackup_for(board.layers, board.thickness, board.stackup)["source"]
            named = re.findall(r"JLC0\d{4}H-[0-9A-Z]+", text)
            if not named or any(n not in source for n in named):
                found.add(name)
        self.assertEqual(found, STACKUP_TO_DECLARE)

    def test_inserted_stackup_reads_back_as_kicad_writes_it(self):
        board = '(kicad_pcb\n\t(version 20260206)\n\t(layers\n\t\t(0 "F.Cu" signal)\n\t\t(4 "In1.Cu" signal)\n' \
                '\t\t(6 "In2.Cu" signal)\n\t\t(2 "B.Cu" signal)\n\t)\n\t(setup\n\t\t(pad_to_mask_clearance 0)\n\t)\n)\n'
        text = fabrication.insert_stackup(board, fabrication.stackup_for(4, 1.6))
        table, rows, finish = pcb_stackup(loads(text))
        self.assertEqual([n for n, kind, _ in rows if kind == "copper"], table)
        self.assertEqual(finish, "ENIG")
        self.assertEqual([t for _, kind, t in rows if kind in ("prepreg", "core")], [0.2104, 1.065, 0.2104])
        with self.assertRaises(ValueError):                     # never two stack-ups
            fabrication.insert_stackup(text, fabrication.stackup_for(4, 1.6))

    def test_every_design_gets_a_stackup_for_its_layers(self):
        for path in sorted((REPO_ROOT / "tools" / "eos_boards" / "boards").glob("eos_*.py")):
            board = importlib.import_module(f"eos_boards.boards.{path.stem}").BOARD
            with self.subTest(board=path.stem):
                st = fabrication.stackup_for(board.layers, board.thickness, board.stackup)
                self.assertEqual(len([r for r in st["layers"] if r["type"] == "copper"]), board.layers)

    def test_every_built_board_carries_a_stackup_matching_its_layers(self):
        for name in EOS_BOARDS:
            pcb = loads((EOS_DIR / name / "hardware" / f"{name}.kicad_pcb").read_text(encoding="utf-8"))
            table, rows, _ = pcb_stackup(pcb)
            with self.subTest(board=name):
                if name in BUILT_BEFORE_P3:
                    self.assertEqual(rows, [], "has a stack-up now: take it out of BUILT_BEFORE_P3")
                else:
                    self.assertEqual([n for n, kind, _ in rows if kind == "copper"], table)


class IdentityTest(_Lib):
    """A3: the board's name, revision and year on the silkscreen beside its ownership line, and the
    board file's title block with the owner and the all-rights-reserved notice."""

    OWN = [{"text": "(c) 2026 Kartikeydheer Srivastava", "x": 10.0, "y": 8.0, "size": 0.8, "layer": "B_SilkS", "mirror": True},
           {"text": "All rights reserved", "x": 10.0, "y": 9.4, "size": 0.8, "layer": "B_SilkS", "mirror": True}]

    def test_every_design_gets_one_identity_line_beside_its_ownership_line(self):
        for path in sorted((REPO_ROOT / "tools" / "eos_boards" / "boards").glob("eos_*.py")):
            module = importlib.import_module(f"eos_boards.boards.{path.stem}")
            board, texts = module.BOARD, module.TEXTS
            out = build.identity_texts(board, texts)
            own = next(t for t in out if t["text"] == "(c) 2026 Kartikeydheer Srivastava")
            mine = [t for t in out if t["text"] == f"{board.title}  rev {board.revision}  2026"]
            with self.subTest(board=path.stem):
                self.assertEqual(len(mine), 1)
                self.assertEqual((mine[0]["layer"], mine[0].get("mirror")), (own["layer"], own.get("mirror")))
                self.assertLess(abs(mine[0]["y"] - own["y"]), 2.6)               # beside it: the line above
                self.assertFalse([t for t in out if t.get("layer") == own["layer"] and t["text"].endswith("rev A")])
                self.assertEqual(len(out), len(texts))                           # the hand-drawn name line replaced

    def test_identity_line_without_a_name_line_and_refusals(self):
        board = self.board([], revision="B", date="2027-01-05")
        board.title = "EoS Test"
        own = [dict(t, text=t["text"].replace("2026", "2027")) for t in self.OWN]
        out = build.identity_texts(board, own)
        self.assertEqual(out[-1], {"text": "EoS Test  rev B  2027", "x": 10.0, "y": 6.0, "size": 1.0, "bold": True,
                                   "layer": "B_SilkS", "mirror": True, "identity": True, "fit": True,
                                   "variants": ["EoS Test  rev B  2027", "EoS Test  rev B", "EoS Test rev B"],
                                   "design_text": "", "design_size": 1.0})
        # review m6: a later revision replaces the old hand-drawn "rev A" line, it does not sit beside it
        out = build.identity_texts(board, own + [dict(own[0], text="EoS Test  rev A", y=5.0)])
        self.assertEqual([t["text"] for t in out if "rev" in t["text"]], ["EoS Test  rev B  2027"])
        self.assertEqual(out[-1]["y"], 5.0)
        self.assertEqual(self.board([]).revision, "A")                            # the default revision
        with self.assertRaisesRegex(SystemExit, "needs one ownership line"):
            build.identity_texts(self.board([]), [])
        with self.assertRaisesRegex(SystemExit, "2 name lines"):
            build.identity_texts(self.board([]), self.OWN + [dict(self.OWN[0], text="T  rev A"), dict(self.OWN[0], text="X  rev A")])

    def test_generator_silk_is_legible(self):
        # stage 2 item 6: every line the generator sizes is at least 1.0 mm high with a 0.15 mm stroke
        # (JLCPCB's stated minimum), the ownership lines go up from 0.8 mm, and a line that does not fit
        # is shortened, never shrunk
        self.assertEqual((fabrication.SILK_MIN_TEXT, fabrication.SILK_MIN_STROKE), (1.0, 0.15))
        for size in (1.0, 1.2, 2.0):
            for bold in (False, True):
                self.assertGreaterEqual(fabrication.silk_stroke(size, bold), 0.15)
        for path in sorted((REPO_ROOT / "tools" / "eos_boards" / "boards").glob("eos_*.py")):
            module = importlib.import_module(f"eos_boards.boards.{path.stem}")
            out = build.identity_texts(module.BOARD, module.TEXTS)
            fitted = [t for t in out if t.get("fit")]
            with self.subTest(board=path.stem):
                self.assertEqual(sorted(t["text"].split("  ")[0] for t in fitted),
                                 sorted([module.BOARD.title, "(c) 2026 Kartikeydheer Srivastava", "All rights reserved"]))
                self.assertTrue(all(t["size"] >= 1.0 for t in fitted))
                identity = next(t for t in fitted if t.get("identity"))
                self.assertEqual(identity["variants"][-1], f"{module.BOARD.title} rev {module.BOARD.revision}")
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        fit = source[source.index("def fit_text("):source.index("def place_fiducials(")]
        # one height, never lowered; only the character width may narrow, last (SILK_WIDTHS)
        self.assertEqual(fit.count("item.SetTextSize("), 2)                     # the design line's check, and the fit
        self.assertEqual(fit.count('item.SetTextSize(v(t["size"] * width, t["size"]))'), 1)
        self.assertNotIn("0.8", fit)
        self.assertIn("allowed", fit)                        # other silkscreen checked (review n4)

    def test_a_small_design_name_line_is_raised_to_1_mm(self):
        # stage-2 review n1 (mutation S8 survived): every design draws its name line at 1.0 mm already, so a
        # fixture with a 0.8 mm one is what exercises the identity line's raise
        board = self.board([])
        board.title = "EoS Test"
        name = dict(self.OWN[0], text="EoS Test  rev A", y=6.6, size=0.8, bold=False)
        out = build.identity_texts(board, self.OWN + [name])
        identity = next(t for t in out if t.get("identity"))
        self.assertEqual((identity["size"], identity["design_size"], identity["design_text"]), (1.0, 0.8, "EoS Test  rev A"))
        self.assertEqual((identity["x"], identity["y"]), (10.0, 6.6))                      # where the design drew it
        self.assertTrue(all(t["size"] >= 1.0 for t in out if t.get("fit")))
        big = build.identity_texts(board, self.OWN + [dict(name, size=1.2)])               # never lowered
        self.assertEqual(next(t for t in big if t.get("identity"))["size"], 1.2)

    def test_the_stroke_is_a_sixth_of_the_height(self):
        # stage-2 review n7: JLCPCB "The preferred ratio of width to height is 1:6"; 0.15 mm stays the floor
        for size in (1.0, 1.2, 1.5, 2.0):
            self.assertGreaterEqual(fabrication.silk_stroke(size), round(size / 6, 4))
            self.assertGreaterEqual(fabrication.silk_stroke(size, bold=True), round(size * 0.2, 4))
        self.assertEqual(fabrication.silk_stroke(1.0), 0.1667)
        self.assertEqual(fabrication.silk_stroke(0.8), fabrication.SILK_MIN_STROKE)
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        fit = source[source.index("def fit_text("):source.index("def place_labels(")]
        # the preferred stroke first; the 0.15 mm minimum only for a line that fits nowhere with it, reported
        self.assertIn("for stroke in [preferred] + ([fabrication.SILK_MIN_STROKE] if preferred > fabrication.SILK_MIN_STROKE else []):", fit)
        self.assertLess(fit.index("for stroke in"), fit.index("for width in fabrication.SILK_WIDTHS:"))
        self.assertIn('stroke: none fits at', fit)

    def test_a_line_moves_then_shortens_then_narrows(self):
        # stage 2 sweep (30 Oct): at 1.0 mm the 26.4 mm ownership line fits nowhere on four boards, so a
        # line may also move sideways and, last, take narrower characters; its height never changes
        widths = fabrication.SILK_WIDTHS
        self.assertEqual(widths[0], 1.0)
        self.assertEqual(list(widths), sorted(widths, reverse=True))
        self.assertGreaterEqual(min(widths), 0.8)
        moves = fabrication.silk_moves()
        self.assertEqual(moves[0], (0.0, 0.0))
        vertical = [m for m in moves if m[0] == 0.0]
        self.assertEqual(moves[:len(vertical)], vertical)                       # up and down before sideways
        self.assertEqual(max(abs(dy) for _, dy in moves), 2.0)
        self.assertEqual(max(abs(dx) for dx, _ in moves), max(fabrication.SILK_SIDEWAYS))
        self.assertEqual(len(set(moves)), len(moves))
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        fit = source[source.index("def fit_text("):source.index("def place_labels(")]
        # widths outermost, then the identity line's variants, then the moves: shortening before narrowing
        self.assertLess(fit.index("for width in fabrication.SILK_WIDTHS:"), fit.index('for words in t.get("variants"'))
        self.assertLess(fit.index('for words in t.get("variants"'), fit.index("for dx, dy in fabrication.silk_moves():"))
        self.assertIn("allowed = touched | set(pending)", fit)
        place = source[source.index("def place(spec"):]
        self.assertIn("fit_text(board, spec, item, t, {later.m_Uuid.AsString() for _, later in fits[i + 1:]})", place)

    def test_generated_silk_over_copper_or_the_edge_fails_the_build(self):
        texts = [{"text": "EoS Test  rev A  2026", "identity": True}, {"text": "J1"}]
        drc = {"violations": [
            {"type": "silk_over_copper", "severity": "warning",
             "items": [{"description": "PCB text 'EoS Test  rev A  2026' on B.Silkscreen"}, {"description": "PTH pad 8 [GND] of J1"}]},
            {"type": "silk_over_copper", "severity": "warning", "items": [{"description": "PCB text 'J1' on F.Silkscreen"}]},
            {"type": "silk_edge_clearance", "severity": "warning",
             "items": [{"description": "Segment on Edge.Cuts"}, {"description": "PCB text 'EoS Test  rev A  2026' on B.Silkscreen"}]},
            {"type": "silk_overlap", "severity": "warning", "items": [{"description": "PCB text 'EoS Test  rev A  2026' on B.Silkscreen"}]}]}
        self.assertEqual(build.generated_silk_problems(drc, texts),
                         ["silk_over_copper: PCB text 'EoS Test  rev A  2026' on B.Silkscreen",
                          "silk_edge_clearance: PCB text 'EoS Test  rev A  2026' on B.Silkscreen",
                          "silk_overlap: PCB text 'EoS Test  rev A  2026' on B.Silkscreen"])     # PR #74 review
        source = (REPO_ROOT / "tools" / "eos_boards" / "build.py").read_text(encoding="utf-8")
        self.assertIn("+ generated_silk_problems(drc, texts)", source)
        pcb = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        self.assertIn('if t.get("identity"):', pcb)            # the placement step fits the line or stops

    def test_title_block_carries_owner_and_rights(self):
        board = self.board([], contact="kartikeydheer@gmail.com", licence_terms="boards/licence_terms.txt")
        board.licence = design.ALL_RIGHTS_RESERVED
        self.assertEqual(build.title_block(board), {
            "title": "T", "date": "2026-10-11", "rev": "A", "company": "Kartikeydheer Srivastava",
            "comments": ["Copyright (c) 2026 Kartikeydheer Srivastava. Licence: All rights reserved",
                         "Generated by tools/eos_boards from the board's design file",
                         "All rights reserved: see LICENSE.txt; permission from kartikeydheer@gmail.com"]})
        self.assertEqual(len(build.title_block(self.board([]))["comments"]), 2)       # an MIT board: no permission line
        spec = build.spec_for(board, self.lib, Path(self.tmp.name), [])
        self.assertEqual(spec["title_block"], build.title_block(board))

    def test_every_built_board_carries_its_identity_and_title_block(self):
        for name, module in EOS_BOARDS.items():
            if name in BUILT_BEFORE_P3:
                continue
            board = importlib.import_module(f"eos_boards.boards.{module}").BOARD
            pcb = loads((EOS_DIR / name / "hardware" / f"{name}.kicad_pcb").read_text(encoding="utf-8"))
            with self.subTest(board=name):
                silk = [str(t[1]) for t in find_all(pcb, "gr_text") if str(find(t, "layer")[1]) == "B.SilkS"]
                self.assertTrue(set(fabrication.identity_variants(board.title, board.revision, board.date[:4])) & set(silk))
                tb = find(pcb, "title_block")
                self.assertEqual(str(find(tb, "company")[1]), board.company)
                self.assertEqual([str(c[2]) for c in find_all(tb, "comment")], build.title_block(board)["comments"])


class FiducialTest(_Lib):
    """A2: three fiducials per side the assembler populates, near three corners and spread, not in a line,
    their mask openings 3 mm or more from the edge, their copper-free squares clear of everything; two
    diagonally opposite where three do not fit."""

    def test_free_board_gets_three_corners(self):
        points, note = fabrication.choose_fiducials(30.0, 20.0, 1.0, [])
        self.assertEqual((points, note), ([(4.0, 4.0), (26.0, 4.0), (4.0, 16.0)], ""))
        self.assertEqual(fabrication.fiducial_problems(points, 30.0, 20.0, 1.0, []), [])

    def test_blocked_corners_are_avoided(self):
        # a FeatherWing: headers along both long edges, holes in the corners (motion wing's courtyards)
        obstacles = [(0, -0.5, 50.8, 3.04), (0, 19.82, 50.8, 23.4), (0, 0, 5.3, 5.3), (45.5, 0, 50.8, 5.3),
                     (0, 17.5, 5.3, 22.9), (45.5, 17.5, 50.8, 22.9), (3.0, 3.0, 9.0, 9.0)]
        points, note = fabrication.choose_fiducials(50.8, 22.86, 2.54, obstacles)
        self.assertEqual((note, fabrication.fiducial_problems(points, 50.8, 22.86, 2.54, obstacles)), ("", []))
        self.assertEqual(len({(x < 25.4, y < 11.43) for x, y in points}), 3)          # three different corners

    def test_crowded_corners_still_spread_the_three(self):
        # review m5: the free spot nearest each corner can sit near the middle (Feather RP2040's three were
        # within 17 x 15 mm); the trio is chosen among each corner's 25 nearest free spots for its spread
        obstacles = [(0, 0, 15, 9), (36, 0, 50.8, 3), (0, 14, 25, 22.86), (30, 15, 50.8, 22.86)]
        points, note = fabrication.choose_fiducials(50.8, 22.86, 2.54, obstacles)
        self.assertEqual(note, "")
        self.assertEqual(fabrication.fiducial_problems(points, 50.8, 22.86, 2.54, obstacles), [])
        self.assertGreaterEqual(fabrication._min_distance(points), 9.0)
        self.assertGreaterEqual(max(x for x, _ in points) - min(x for x, _ in points), 40.0)   # across the board

    def test_the_widest_trio_wins_over_the_first(self):
        # review n3 (N12): with the top-left corner blocked, the nearest trio (top-left, top-right,
        # bottom-left) has its closest pair 22.5 mm apart; leaving out bottom-left for bottom-right
        # spreads it to 32 mm, and the chooser must prefer that (by more than its 0.5 mm hysteresis)
        points, note = fabrication.choose_fiducials(60.0, 40.0, 1.0, [(0, 0, 20, 12)])
        self.assertEqual((points, note), ([(4.0, 13.5), (56.0, 4.0), (56.0, 36.0)], ""))
        self.assertEqual(fabrication._min_distance(points), 32.0)
        nearest = [(4.0, 13.5), (56.0, 4.0), (4.0, 36.0)]
        self.assertEqual(fabrication._min_distance(nearest), 22.5)

    def test_two_diagonally_opposite_where_three_do_not_fit(self):
        # ESP32 DevKit's case (review m4): the module and its antenna keep-out fill the top half
        obstacles = [(0, 0, 27.94, 24.0), (0, 0, 2.5, 48.76), (25.4, 0, 27.94, 48.76)]
        points, note = fabrication.choose_fiducials(27.94, 48.76, 1.0, obstacles)
        self.assertEqual(len(points), 2)
        # stage-2 review n8: what the dots are, their spacing, and the panel rails
        (ax, ay), (bx, by) = points
        self.assertIn("two fiducials, the free spots nearest the top-left and bottom-right corners", note)
        self.assertIn(f"{((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5:.1f} mm apart ({abs(ax - bx):g} mm in x, "
                      f"{abs(ay - by):g} mm in y)", note)
        self.assertIn("only 2 corner quarter(s) have room", note)
        self.assertIn("use the panel-rail fiducials as well", note)
        self.assertGreaterEqual(fabrication._diagonal(points), fabrication.FIDUCIAL_SPREAD)
        self.assertEqual(fabrication.fiducial_problems(points, 27.94, 48.76, 1.0, obstacles), [])

    def test_no_room_is_refused_with_the_way_out(self):
        with self.assertRaisesRegex(ValueError, "near only 0 corner.*fiducials option"):
            fabrication.choose_fiducials(30.0, 20.0, 1.0, [(0, 0, 30, 20)])
        with self.assertRaisesRegex(ValueError, "no two diagonally opposite"):     # a strip too thin to go diagonal
            fabrication.choose_fiducials(40.0, 9.0, 1.0, [(0, 0, 40, 3.5)])

    def test_problems_are_named(self):
        args = (30.0, 20.0, 1.0)
        self.assertIn("three are needed", fabrication.fiducial_problems([(5, 5)], *args, [])[0])
        self.assertIn("not diagonally apart", fabrication.fiducial_problems([(5, 5), (25, 7)], *args, [])[0])
        self.assertEqual(fabrication.fiducial_problems([(5, 5), (25, 15)], *args, []), [])
        self.assertIn("under 3.0 mm from the board edge", fabrication.fiducial_problems([(3.5, 5), (25, 5), (5, 15)], *args, [])[0])
        self.assertIn("meets 1 item", fabrication.fiducial_problems([(5, 5), (25, 5), (5, 15)], *args, [(5.5, 5.5, 7, 7)])[0])
        self.assertIn("of a line", fabrication.fiducial_problems([(5, 5), (15, 7), (25, 9)], *args, [])[0])

    def test_one_definition_of_an_assembled_side(self):
        # review m3/D1: fitted, in the position file, and a pad that gets paste
        self.assertTrue(fabrication.carries_smd_parts(False, False, [(True, True), (True, True)]))
        for dnp, excluded, pads in ((True, False, [(True, True)]), (False, True, [(True, True)]),
                                    (False, False, [(True, False)]), (False, False, [(False, False)])):
            with self.subTest(dnp=dnp, excluded=excluded, pads=pads):
                self.assertFalse(fabrication.carries_smd_parts(dnp, excluded, pads))
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        place = source[source.index("def place_fiducials("):source.index("def place(")]
        self.assertIn("fabrication.carries_smd_parts(", place)
        self.assertIn("fp.SetBoardOnly(True)", place)
        self.assertIn("fp.SetExcludedFromBOM(True)", place)
        self.assertIn("fabrication.carries_smd_parts(", (REPO_ROOT / "tools" / "eos_boards" / "metrics.py").read_text(encoding="utf-8"))
        # STM32 64's bottom: two fitted-nothing test pads (dnp, exclude_from_pos_files, no paste)
        self.assertEqual(metrics.board_metrics(EOS_DIR / "eos-stm32-64")["smd_sides"], ["top"])
        self.assertEqual(metrics.board_metrics(EOS_DIR / "eos-cm5-base")["smd_sides"], ["bottom", "top"])   # BT1 on the bottom

    def test_design_positions_reach_the_spec_and_bad_ones_are_refused(self):
        parts = [Part("U1", "T:M", "M", "fp", (5, 5), {"GND": "GND", "A/B": NC})]
        spec = build.spec_for(self.board(parts, fiducials={"B": [(4, 4), (6, 4), (4, 6)]}), self.lib, Path(self.tmp.name), [])
        self.assertEqual(spec["fiducials"], {"B": [[4, 4], [6, 4], [4, 6]]})
        spec = build.spec_for(self.board(parts, fiducials={"F": [(4, 4), (6, 6)]}), self.lib, Path(self.tmp.name), [])
        self.assertEqual(spec["fiducials"], {"F": [[4, 4], [6, 6]]})                 # two: checked for diagonal in place
        for bad in ({"T": [(1, 1)] * 3}, {"F": [(1, 1)]}, {"F": [(1, 1, 0)] * 3}, {"F": [(1, 1)] * 4}):
            with self.subTest(bad=bad), self.assertRaisesRegex(SystemExit, "three"):
                build.spec_for(self.board(parts, fiducials=bad), self.lib, Path(self.tmp.name), [])

    def test_the_placement_step_keeps_generator_copper_out_of_the_squares(self):
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        inside = source[source.index("def _inside("):source.index("def _in_fiducial_keepout(")]
        self.assertIn('spec.get("fiducial_keepouts", [])', inside)          # fan-out, stitching, maze, repair vias
        self.assertEqual(source.count("_in_fiducial_keepout(spec, "), 5)    # its definition; fan-out stub, pre-route, repair track, fragment via
        maze = source[source.index("def maze("):source.index("def _track(")]
        self.assertIn('li = 0 if k[4] == "F" else 1', maze)                 # tracks: the fiducial's own layer only
        self.assertIn("_inside(no_fiducials, pt, t_edge)", maze)
        place = source[source.index("def place("):source.index("def stitch(")]
        self.assertLess(place.index("for route in spec.get(\"priority_routes\""), place.index("place_fiducials(board, spec)"))
        self.assertLess(place.index("place_fiducials(board, spec)"), place.index("fanout(board, spec, exclude=early | first)"))

    def test_every_built_board_has_fiducials_on_each_assembled_side(self):
        for name in EOS_BOARDS:
            if name in BUILT_BEFORE_P3:
                continue
            folder = EOS_DIR / name
            pcb = loads((folder / "hardware" / f"{name}.kicad_pcb").read_text(encoding="utf-8"))
            board = importlib.import_module(f"eos_boards.boards.{EOS_BOARDS[name]}").BOARD
            m = metrics.board_metrics(folder)
            areas = [z for z in find_all(pcb, "zone") if find(z, "name") and str(find(z, "name")[1]) == "eos-fiducial-keepout"]
            with self.subTest(board=name):
                self.assertEqual(sorted(m["fiducials"]), m["smd_sides"])           # fiducials on, and only on, assembled sides
                self.assertEqual(m["fiducial_flags"], [])                           # board-only, out of the BOM
                for side, points in m["fiducials"].items():
                    self.assertEqual(fabrication.fiducial_problems([tuple(q) for q in points], board.width, board.height,
                                                                   board.corner_radius, []), [])
                    if len(points) == 2:                                            # A2: the README says why
                        self.assertIn("two fiducials", (folder / "README.md").read_text(encoding="utf-8").lower())
                self.assertEqual(len(areas), sum(len(p) for p in m["fiducials"].values()))
                placement = (folder / "fab" / f"{name}-placement.csv").read_text(encoding="utf-8")
                bom = (folder / "fab" / f"{name}-bom.csv").read_text(encoding="utf-8")
                self.assertIn('"FID1"', placement)
                self.assertNotIn("FID1", bom)


# Designs whose SWD header is a Samtec FTSH-105 (by MPN) but still on KiCad's generic 1.27 mm SMD
# header footprint; each switches to EoS_Packages:Samtec_FTSH-105-... (and lists EoS_Packages in its
# local_footprints) when P4 rebuilds it, and leaves this set.
FTSH_TO_SWITCH = {("eos_ke16z_board", "J2"), ("eos_kl25_board", "J7"), ("eos_lpc55s69_board", "J3"),
                  ("eos_probe_s3", "J2"), ("eos_ra2e1_board", "J2"), ("eos_ra4m2_board", "J9"),
                  ("eos_stm32_64", "J3"), ("eos_tm4c123_board", "J7"), ("eos_tm4c1294_board", "J9")}


class OneRevisionTest(_Lib):
    """PR #74 review (qodo): a hand-drawn name line on the other side kept its own revision, so a board
    raised to rev B would show rev B on one side and rev A on the other."""

    def test_every_name_line_carries_the_board_revision(self):
        board = self.board([], revision="B")
        board.title = "EoS Sense Cape for PocketBeagle"
        texts = [{"text": "EoS Sense Cape  rev A", "x": 27.5, "y": 37.2, "size": 1.0, "bold": True},
                 {"text": "EoS Sense Cape for PocketBeagle  rev A", "x": 27.5, "y": 44.0, "size": 1.0,
                  "layer": "B_SilkS", "bold": True, "mirror": True},
                 {"text": "(c) 2026 Kartikeydheer Srivastava", "x": 27.5, "y": 46.0, "size": 0.8, "layer": "B_SilkS", "mirror": True},
                 {"text": "PWR", "x": 3.0, "y": 3.0, "size": 0.8}]
        out = build.one_revision(board, build.identity_texts(board, texts))
        self.assertEqual(out[0], dict(texts[0], text="EoS Sense Cape  rev B"))     # moved nowhere, resized never
        self.assertFalse([t["text"] for t in out if "rev A" in t["text"]])
        self.assertEqual(out[3], texts[3])
        source = (REPO_ROOT / "tools" / "eos_boards" / "build.py").read_text(encoding="utf-8")
        self.assertIn('texts = one_revision(board, identity_texts(board, getattr(module, "TEXTS", [])))', source)

    def test_designs_show_one_revision(self):
        for path in sorted((REPO_ROOT / "tools" / "eos_boards" / "boards").glob("eos_*.py")):
            module = importlib.import_module(f"eos_boards.boards.{path.stem}")
            out = build.one_revision(module.BOARD, build.identity_texts(module.BOARD, module.TEXTS))
            revs = {m.group(1) for t in out for m in [re.search(r"\brev ([A-Z0-9]+)\b", t["text"])] if m}
            with self.subTest(board=path.stem):
                self.assertEqual(revs, {module.BOARD.revision})


class GeneratedSilkGateTest(unittest.TestCase):
    """PR #74 review (greptile, qodo): the name line over other silkscreen fails the build, as it does
    over copper or at the edge; findings on the design's own texts stay warnings."""

    def test_the_name_line_over_other_silk_fails_the_build(self):
        texts = [{"text": "EoS T  rev A  2026", "identity": True}, {"text": "(c) 2026 Kartikeydheer Srivastava"}]
        def drc(kind, first):
            return {"violations": [{"type": kind, "severity": "warning", "items": [
                {"description": f"PCB text '{first}' on B.Silkscreen"},
                {"description": "PCB text '(c) 2026 Kartikeydheer Srivastava' on B.Silkscreen"}]}]}
        self.assertEqual(build.generated_silk_problems(drc("silk_overlap", "EoS T  rev A  2026"), texts),
                         ["silk_overlap: PCB text 'EoS T  rev A  2026' on B.Silkscreen"])
        self.assertEqual(build.generated_silk_problems(drc("silk_overlap", "PWR"), texts), [])
        for kind in ("silk_over_copper", "silk_edge_clearance"):
            self.assertEqual(len(build.generated_silk_problems(drc(kind, "EoS T  rev A  2026"), texts)), 1)

    def test_an_ownership_line_over_other_silk_fails_the_build_too(self):
        # stage 2 sweep (30 Oct): EoS ESP32 DevKit's ownership line, raised to 1.0 mm, met the pin label "16"
        # stroke to stroke; the generator sizes and fits the ownership lines, so the gate covers them
        texts = [{"text": "(c) 2026 Kartikeydheer Srivastava", "fit": True}, {"text": "All rights reserved", "fit": True},
                 {"text": "16"}]
        drc = {"violations": [{"type": "silk_overlap", "severity": "warning", "items": [
            {"description": "PCB text '16' on B.Silkscreen"},
            {"description": "PCB text '(c) 2026 Kartikeydheer Srivastava' on B.Silkscreen"}]}]}
        self.assertEqual(build.generated_silk_problems(drc, texts),
                         ["silk_overlap: PCB text '(c) 2026 Kartikeydheer Srivastava' on B.Silkscreen"])
        self.assertEqual(build.generated_silk_problems(drc, texts[2:]), [])          # a design text alone: a warning
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        fit = source[source.index("def fit_text("):source.index("def place_labels(")]
        self.assertIn("_silk_clear(spec, item, pads, silk, allowed) and not _strokes_touch(item, near)", fit)
        self.assertIn("near = [items[uid] for uid in touched - set(pending)]", fit)


FIT_SCRIPT = """
import json, sys
sys.path.insert(0, sys.argv[1])
import pcbnew as P
import fabrication, pcb_build
v = pcb_build.v
board = P.BOARD()
spec = {"width": 40.0, "height": 20.0, "corner_radius": 0.0}
for x in (12.0, 16.0, 20.0, 24.0, 28.0):         # 4 mm pads under the name line and every spot above it
    fp = P.FootprintLoad(sys.argv[2] + "/TestPoint.pretty", "TestPoint_Pad_4.0x4.0mm")
    board.Add(fp)
    fp.SetPosition(v(x, 6.3))
own = pcb_build.text(board, "(c) 2026 Kartikeydheer Srivastava", 20.0, float(sys.argv[3]), 0.8, P.F_SilkS)
t = {"text": "EoS T  rev A  2026", "x": 20.0, "y": 8.0, "size": 1.0, "bold": True, "identity": True, "fit": True,
     "variants": fabrication.identity_variants("EoS T", "A", "2026"), "design_text": "", "design_size": 1.0}
item = pcb_build.text(board, t["text"], t["x"], t["y"], t["size"], P.F_SilkS, 0.0, True)
try:
    where = pcb_build.fit_text(board, spec, item, t)[1]       # the one fitter (stage 2 replaced fit_identity)
except SystemExit as e:
    where = "stopped: " + str(e)
print(json.dumps({"where": where, "on_ownership": item.GetBoundingBox().Intersects(own.GetBoundingBox())}))
"""


class IdentityFitTest(unittest.TestCase):
    """PR #74 review (greptile, qodo): the name line, moved off pads, must not land on the ownership
    line (or other silkscreen), and every design text is down before it is fitted."""

    def test_the_fitter_checks_other_silk_after_every_text_is_down(self):
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        clear = source[source.index("def _silk_clear("):source.index("def fit_text(")]
        self.assertIn("and not any(box.Intersects(b) for uid, box in silk.items() if uid not in allowed)", clear)
        fit = source[source.index("def fit_text("):source.index("def place_fiducials(")]
        self.assertIn("_silk_clear(spec, item, pads, silk, allowed)", fit)
        place = source[source.index("def place(spec"):]
        self.assertLess(place.index("placed_texts = [(t, text(board"), place.index("fit_text(board, spec, item, t,"))
        self.assertIn('design_text=old[0]["text"] if old else ""',
                      (REPO_ROOT / "tools" / "eos_boards" / "build.py").read_text(encoding="utf-8"))

    @unittest.skipUnless(os.environ.get("EOS_KICAD_TESTS"), "set EOS_KICAD_TESTS=1 to run the KiCad-backed fit "
                         "(one small KiCad job: run it through the campaign's locked.sh)")
    def test_a_blocked_name_line_never_lands_on_the_ownership_line(self):
        from eos_boards import kicad_env
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp, "fit.py")
            script.write_text(FIT_SCRIPT, encoding="utf-8")
            results = {}
            for own_y in (10.0, 13.0):           # the ownership line just below, or out of the way
                run = subprocess.run([kicad_env.python(), str(script), str(REPO_ROOT / "tools" / "eos_boards"),
                                      str(kicad_env.footprints()), str(own_y)], capture_output=True, text=True, timeout=300)
                self.assertEqual(run.returncode, 0, run.stderr[-2000:])
                results[own_y] = json.loads(run.stdout.strip().splitlines()[-1])
        # just below: no spot within 2 mm clears both, so the build stops (before the fix: 1.0 mm on top of it)
        self.assertTrue(results[10.0]["where"].startswith("stopped: silkscreen line 'EoS T  rev A  2026' at 1.0 mm "
                                                          "clears no pad, edge or other silkscreen"), results[10.0])
        self.assertFalse(results[13.0]["where"].startswith("stopped"), results[13.0])   # room below the pads: it goes there
        self.assertFalse(results[13.0]["on_ownership"])


FIT_TEXT_SCRIPT = """
import json, sys
sys.path.insert(0, sys.argv[1])
import pcbnew as P
import fabrication, pcb_build
v = pcb_build.v
board = P.BOARD()
spec = {"width": 40.0, "height": 20.0, "corner_radius": 0.0}
for x in (12.0, 16.0, 20.0, 24.0, 28.0):         # 4 mm pads under the name line and every spot above it
    fp = P.FootprintLoad(sys.argv[2] + "/TestPoint.pretty", "TestPoint_Pad_4.0x4.0mm")
    board.Add(fp)
    fp.SetPosition(v(x, 6.3))
own = pcb_build.text(board, "(c) 2026 Kartikeydheer Srivastava", 20.0, float(sys.argv[3]), 1.0, P.F_SilkS)
t = {"text": "EoS T  rev A  2026", "x": 20.0, "y": 8.0, "size": 1.0, "bold": True, "identity": True, "fit": True,
     "variants": fabrication.identity_variants("EoS T", "A", "2026"), "design_text": "", "design_size": 1.0}
item = pcb_build.text(board, t["text"], t["x"], t["y"], t["size"], P.F_SilkS, 0.0, True)
try:
    where = pcb_build.fit_text(board, spec, item, t)[1]
except SystemExit as e:
    where = "stopped: " + str(e)
print(json.dumps({"where": where, "on_ownership": item.GetBoundingBox().Intersects(own.GetBoundingBox())}))
"""


class FitTextTest(unittest.TestCase):
    """PR #74 review (greptile, qodo), as it applies to the stage-2 fitter: a name line moved off pads
    never lands on the ownership line (or other silkscreen)."""

    @unittest.skipUnless(os.environ.get("EOS_KICAD_TESTS"), "set EOS_KICAD_TESTS=1 to run the KiCad-backed fit "
                         "(one small KiCad job: run it through the campaign's locked.sh)")
    def test_a_blocked_name_line_never_lands_on_the_ownership_line(self):
        from eos_boards import kicad_env
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp, "fit.py")
            script.write_text(FIT_TEXT_SCRIPT, encoding="utf-8")
            results = {}
            for own_y in (10.0, 13.0):           # the ownership line just below, or out of the way
                run = subprocess.run([kicad_env.python(), str(script), str(REPO_ROOT / "tools" / "eos_boards"),
                                      str(kicad_env.footprints()), str(own_y)], capture_output=True, text=True, timeout=300)
                self.assertEqual(run.returncode, 0, run.stderr[-2000:])
                results[own_y] = json.loads(run.stdout.strip().splitlines()[-1])
        # just below: no spot within 2 mm clears both, so the build stops; out of the way: it moves below the pads
        self.assertTrue(results[10.0]["where"].startswith("stopped: silkscreen line 'EoS T  rev A  2026' at 1.0 mm "
                                                          "clears no pad, edge or other silkscreen"), results[10.0])
        self.assertFalse(results[13.0]["where"].startswith("stopped"), results[13.0])
        self.assertFalse(results[13.0]["on_ownership"])


class FtshFootprintTest(unittest.TestCase):
    """Samtec FTSH-105 on Samtec's recommended land pattern (Rev H, Fig 1): pads 0.74 x 2.79 mm,
    1.27 mm pitch, 6.86 mm across both rows; pad order as KiCad's generic 1.27 mm SMD header."""

    def test_committed_footprints_are_what_the_generator_writes(self):
        fp = importlib.import_module("eos_boards.footprints.generate")
        folder = REPO_ROOT / "tools" / "eos_boards" / "footprints" / "EoS_Packages.pretty"
        for name, node in ((fp.NAME, fp.footprint()), (fp.HEADER_NAME, fp.header_2x49()), (fp.FTSH_NAME, fp.ftsh_105())):
            with self.subTest(footprint=name):
                self.assertEqual(dumps(node) + "\n", (folder / f"{name}.kicad_mod").read_text(encoding="utf-8"))

    def test_pads_follow_samtecs_land_pattern(self):
        fp = importlib.import_module("eos_boards.footprints.generate")
        node = loads((REPO_ROOT / "tools" / "eos_boards" / "footprints" / "EoS_Packages.pretty"
                      / f"{fp.FTSH_NAME}.kicad_mod").read_text(encoding="utf-8"))
        pads = {str(q[1]): (float(find(q, "at")[1]), float(find(q, "at")[2]), float(find(q, "size")[1]), float(find(q, "size")[2]),
                            [str(x) for x in find(q, "layers")[1:]]) for q in find_all(node, "pad")}
        self.assertEqual(sorted(pads, key=int), [str(n) for n in range(1, 11)])
        for n, (x, y, w, h, layers) in pads.items():
            with self.subTest(pad=n):
                self.assertEqual((w, h), (2.79, 0.74))                                    # .110 x .029 in
                self.assertEqual(x, -2.035 if int(n) % 2 else 2.035)                       # odd pads left, as KiCad's header
                self.assertEqual(y, round(-2.54 + 1.27 * ((int(n) - 1) // 2), 3))           # pad 1 at the top
                self.assertEqual(layers, ["F.Cu", "F.Mask", "F.Paste"])                    # Fig 2: paste = pad
        self.assertEqual(round(max(x + w / 2 for x, _, w, _, _ in pads.values()) * 2, 3), 6.86)   # .270 in across
        self.assertIn("suddendocs.samtec.com", (REPO_ROOT / "tools" / "eos_boards" / "footprints" / "generate.py").read_text(encoding="utf-8"))

    def test_designs_still_to_switch_to_it(self):
        found = set()
        for path in sorted((REPO_ROOT / "tools" / "eos_boards" / "boards").glob("eos_*.py")):
            board = importlib.import_module(f"eos_boards.boards.{path.stem}").BOARD
            for part in board.parts:
                if part.fields.get("MPN", "").startswith("FTSH-105") and not part.footprint.startswith("EoS_Packages:Samtec_FTSH"):
                    found.add((path.stem, part.ref))
        self.assertEqual(found, FTSH_TO_SWITCH)


# 2.54 mm jumper headers (a JP reference, or a BOOT header) drawn with a connector symbol, whose design
# does not yet say how many shunts come with them (Board.shunts); P4 declares each and empties this set.
SHUNTS_TO_DECLARE = {("eos_cm4_base", "J9"), ("eos_cm5_base", "J9"), ("eos_f280049c_board", "JP1"),
                     ("eos_msp430g2_board", "JP1"), ("eos_msp430g2_board", "JP2"), ("eos_msp430g2_board", "JP3"),
                     ("eos_msp430g2_board", "JP4"), ("eos_rl78g13_board", "JP1"), ("eos_tm4c123_board", "JP1"),
                     ("eos_tm4c1294_board", "JP1"), ("eos_tm4c1294_board", "JP2")}


class ShuntTest(_Lib):
    """B3: the shunts a 2.54 mm jumper header needs are BOM lines (BOM-only symbols, no footprint)."""

    HOUSING = """(kicad_symbol_lib (version 20231120) (generator "test")
  (symbol "Housing" (in_bom yes) (on_board yes)
    (property "Reference" "N" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "Housing" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (symbol "Housing_0_1" (rectangle (start -1 -1) (end 1 1) (stroke (width 0) (type default)) (fill (type none))))))
"""

    def setUp(self):
        super().setUp()
        Path(self.tmp.name, "Mechanical.kicad_sym").write_text(self.HOUSING)
        self.lib = Library(Path(self.tmp.name))
        self.jp = Part("JP1", "T:R", "MD", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", (50, 50), {"1": "A", "2": "B"})
        self.jp.lib_id = "Jumper:Jumper_2_Open"          # as the RA2E1 draws its boot jumper
        self.boot = Part("J9", "T:U", "BOOT", "Connector_PinHeader_2.54mm:PinHeader_2x02_P2.54mm_Vertical", (80, 50),
                         {"VDD": "A", "3": "B"})

    def test_jumper_symbols_get_one_and_declared_headers_their_count(self):
        shunts = build.shunt_parts(self.board([self.jp, self.boot], shunts={"J9": 2}))
        self.assertEqual([(p.ref, p.lib_id, p.value, p.on_board) for p in shunts],
                         [("JS1", "Mechanical:Housing", "Shunt 2.54 mm", False), ("JS2", "Mechanical:Housing", "Shunt 2.54 mm", False),
                          ("JS3", "Mechanical:Housing", "Shunt 2.54 mm", False)])
        self.assertEqual({p.fields["MPN"] for p in shunts}, {"SNT-100-BK-G"})
        self.assertIn("supplied for J9 (2), JP1 (1)", shunts[0].fields["Description"])
        self.assertEqual(build.shunt_parts(self.board([self.jp], shunts={"JP1": 0})), [])     # a design can say none

    def test_refusals(self):
        smd = Part("J4", "T:R", "X", "Connector_PinHeader_1.27mm:PinHeader_1x02_P1.27mm_Vertical", (50, 50), {"1": "A", "2": "B"})
        for parts, shunts, message in (([self.jp], {"J5": 1}, "does not have"), ([smd], {"J4": 1}, "2.54 mm pin header"),
                                       ([self.boot], {"J9": -1}, "count"),
                                       ([self.jp, Part("JS1", "T:R", "x", "fp", (9, 9), {"1": "A", "2": "B"})], {}, "JS references")):
            with self.subTest(message=message), self.assertRaisesRegex(SystemExit, message):
                build.shunt_parts(self.board(parts, shunts=shunts))

    def test_a_jumper_on_a_finer_header_gets_no_2_54_mm_shunt(self):
        # PR #74 review (greptile): the automatic count took any PinHeader, 1.27 mm too, past the pitch check
        fine = Part("JP2", "T:R", "MD", "Connector_PinHeader_1.27mm:PinHeader_1x02_P1.27mm_Vertical", (50, 50),
                    {"1": "A", "2": "B"})
        fine.lib_id = "Jumper:Jumper_2_Open"
        with self.assertRaisesRegex(SystemExit, r"JP2 is a jumper on .*P1\.27mm.*no 2\.54 mm shunt fits; give shunts=\{'JP2': 0\}"):
            build.shunt_parts(self.board([fine]))
        self.assertEqual(build.shunt_parts(self.board([fine], shunts={"JP2": 0})), [])    # the design says none
        with self.assertRaisesRegex(SystemExit, "2.54 mm pin header"):
            build.shunt_parts(self.board([fine], shunts={"JP2": 1}))
        self.assertEqual([p.ref for p in build.shunt_parts(self.board([fine, self.jp], shunts={"JP2": 0}))], ["JS1"])

    def test_the_spec_validates_shunts_and_bom_only_parts(self):
        # review m8: spec_for itself refuses a bad shunts entry and a part with pins left off the board
        for kw, message in (({"shunts": {"U1": 5}}, "U1 has pins|does not have|2.54 mm pin header"),
                            ({"shunts": {"NOPE": 1}}, "does not have"), ({"shunts": {"J9": True}}, "count")):
            with self.subTest(**{k: str(v) for k, v in kw.items()}), self.assertRaisesRegex(SystemExit, message):
                build.spec_for(self.board([self.boot], **kw), self.lib, Path(self.tmp.name), [])
        off = Part("R5", "T:R", "1k", "fp", (9, 9), {"1": "A", "2": "B"}, on_board=False)
        with self.assertRaisesRegex(SystemExit, "R5 has pins"):
            build.spec_for(self.board([self.boot, off]), self.lib, Path(self.tmp.name), [])
        board = self.board([self.boot], shunts={"J9": 1})
        board.parts = board.parts + build.shunt_parts(board)            # pinless and off the board: fine
        self.assertEqual([p["ref"] for p in build.spec_for(board, self.lib, Path(self.tmp.name), [])["parts"]], ["J9"])

    def test_a_shunt_line_says_it_is_loose_and_names_a_second_source(self):
        # review m9: an assembler matching BOM lines to placement rows must not look for it; B1 fallback
        shunt = build.shunt_parts(self.board([self.boot], shunts={"J9": 1}))[0]
        self.assertEqual(shunt.fields["Assembly"], "Loose: supplied with the board, not placed")
        self.assertIn("Second source: Sullins QPC02SXGN-RC", shunt.fields["Description"])
        self.assertIn("Assembly", build.BOM_FIELDS[0].split(","))
        self.assertEqual(len(build.BOM_FIELDS[0].split(",")), len(build.BOM_FIELDS[1].split(",")))
        self.assertIn("BOM_FIELDS[0]", (REPO_ROOT / "tools" / "eos_boards" / "build.py").read_text(encoding="utf-8"))

    def test_a_shunt_is_a_bom_line_in_the_schematic_and_off_the_board(self):
        board = self.board([self.boot], shunts={"J9": 1})
        board.parts = board.parts + build.shunt_parts(board)
        sch = loads(schematic.write(board, self.lib))
        js = next(n for n in find_all(sch, "symbol") if find(n, "lib_id") and any(
            str(q[1]) == "Reference" and str(q[2]) == "JS1" for q in find_all(n, "property")))
        self.assertEqual((str(find(js, "in_bom")[1]), str(find(js, "on_board")[1])), ("yes", "no"))
        self.assertIn("SNT-100-BK-G", [str(q[2]) for q in find_all(js, "property")])
        self.assertEqual([p["ref"] for p in build.spec_for(board, self.lib, Path(self.tmp.name), [])["parts"]], ["J9"])

    def test_designs_with_shunts_and_those_still_to_declare(self):
        auto, undeclared = {}, set()
        for path in sorted((REPO_ROOT / "tools" / "eos_boards" / "boards").glob("eos_*.py")):
            board = importlib.import_module(f"eos_boards.boards.{path.stem}").BOARD
            shunts = build.shunt_parts(board)
            if shunts:
                auto[path.stem] = len(shunts)
            counted = set(board.shunts) | {p.ref for p in board.parts if p.lib_id.startswith("Jumper:Jumper_")}
            for p in board.parts:
                if "PinHeader" in p.footprint and "P2.54mm" in p.footprint and (p.ref.startswith("JP") or p.value == "BOOT") \
                        and p.ref not in counted:
                    undeclared.add((path.stem, p.ref))
        self.assertEqual(auto, {"eos_ra2e1_board": 1, "eos_ra4m2_board": 1})         # their boot-mode jumper (Jumper_2_Open)
        self.assertEqual(undeclared, SHUNTS_TO_DECLARE)


class RobustRoutingTest(_Lib):
    """Deferred routing items: a new Freerouting run when repairs leave opens, a width per priority
    route, fan-out vias fixed for the router, and pour fragments joined again after each repair."""

    OPEN = {"items": [{"description": "Pad 1 [/A] of R1 on F.Cu", "pos": {"x": 1.0, "y": 1.0}},
                      {"description": "Pad 2 [/A] of R2 on F.Cu", "pos": {"x": 2.0, "y": 1.0}}]}
    ISLAND = {"items": [{"description": "Zone [GND] on B.Cu", "pos": {"x": 3.0, "y": 3.0}},
                        {"description": "Zone [GND] on B.Cu", "pos": {"x": 4.0, "y": 3.0}}]}

    def _route(self, opens, attempts=3):
        """Run build.route with Freerouting, the pcb_build steps and DRC replaced: ``opens`` is, per
        run, the unconnected items its last DRC reports (after a keep-the-best restore, the DRC is run
        once more). Returns (result, the board text each finish step started from, the Freerouting
        options of each run, the board file at the end)."""
        from unittest import mock
        out = Path(tempfile.mkdtemp(dir=self.tmp.name))
        work = out / ".build"
        work.mkdir()
        pcb, ses = out / "b.kicad_pcb", work / "b.ses"
        pcb.write_text("placed\n")
        seen, runs, reports = [], [], iter(list(opens) + [opens[0]])

        def step(mode, spec, board, other, tail=2000):
            seen.append(Path(board).read_text())
            Path(board).write_text(Path(board).read_text() + f"routed by run {len(runs)}\n")

        def freeroute(dsn, ses_, passes, attempt, work_):
            runs.append(build.freerouting_args(attempt))
            ses_.write_text(f"session of run {len(runs)}")

        def drc_round(cli, pcb_, out_):
            return {"violations": [], "schematic_parity": [], "unconnected_items": next(reports)}

        with mock.patch.object(build, "pcb_step", side_effect=step), mock.patch.object(build, "freeroute", side_effect=freeroute), \
                mock.patch.object(build, "check_and_repair", side_effect=lambda *a: (drc_round(*a[:1], None, None), 0)), \
                mock.patch.object(build, "run_drc", side_effect=drc_round), contextlib.redirect_stdout(io.StringIO()):
            result = build.route("kicad-cli", "spec.json", pcb, "b.dsn", ses, work, out, 60, attempts)
        self.session = ses.read_text()
        return result, seen, runs, pcb.read_text()

    def test_a_run_that_leaves_opens_is_routed_again_with_other_costs(self):
        (drc, rounds, made, kept), seen, runs, board = self._route([[self.OPEN] * 2, []])
        self.assertEqual((len(drc["unconnected_items"]), made, kept), (0, 2, 2))
        self.assertEqual(seen, ["placed\n", "placed\n"])                 # the second run starts from the placement
        self.assertEqual(runs, [[], ["--router.scoring.via_costs=100"]])   # with Freerouting's via cost changed

    def test_the_best_run_is_kept_and_zone_islands_are_retried(self):
        (drc, _, made, kept), _, runs, board = self._route([[self.OPEN], [self.OPEN] * 3, [self.OPEN] * 2])
        self.assertEqual((made, kept, len(drc["unconnected_items"])), (3, 1, 1))
        self.assertEqual(board, "placed\nrouted by run 1\n")                  # run 1's board, restored
        self.assertEqual(self.session, "session of run 1")                    # and its session (review n2)
        self.assertEqual(runs[2], ["--router.scoring.start_ripup_costs=300"])
        # stage 2 (EoS Feather RP2040): a route can cut a pad's patch of pour off, and another may not
        (drc, _, made, kept), _, _, _ = self._route([[self.ISLAND], []])
        self.assertEqual((made, kept, len(drc["unconnected_items"])), (2, 2, 0))
        (drc, _, made, kept), _, _, _ = self._route([[self.ISLAND]] * 3)       # an island every run: the first kept
        self.assertEqual((made, kept), (3, 1))
        self.assertEqual(self._route([[]])[0][2], 1)                           # a clean first run is not repeated

    def test_retry_settings_change_the_auto_router(self):
        # review MAJOR-2: "-is random" only reordered the optimizer; each retry now changes a router cost
        self.assertEqual([build.freerouting_args(i) for i in range(build.ROUTE_ATTEMPTS)],
                         [[], ["--router.scoring.via_costs=100"], ["--router.scoring.start_ripup_costs=300"]])
        self.assertEqual(len({tuple(a) for a in build.RETRY_SETTINGS}), build.ROUTE_ATTEMPTS)
        self.assertEqual(build.repairable_opens({"unconnected_items": [self.OPEN, self.ISLAND]}),
                         [{"net": "/A", "a": [1.0, 1.0], "b": [2.0, 1.0]}])

    def test_priority_route_options(self):
        self.assertEqual(fabrication.route_options((("U1", "1"), ("C1", "2"))), (False, None))
        self.assertEqual(fabrication.route_options((("U1", "1"), ("C1", "2"), "join")), (True, None))
        self.assertEqual(fabrication.route_options((("U1", "1"), ("C1", "2"), 0.4, "join")), (True, 0.4))
        for bad in ("joins", 0, -0.2, True, ("join", "join"), (0.3, 0.4)):
            extra = bad if isinstance(bad, tuple) else (bad,)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                fabrication.route_options((("U1", "1"), ("C1", "2"), *extra))
        parts = [Part("U1", "T:U", "U", "fp", (5, 5), {"VDD": "A", "3": NC})]
        spec = build.spec_for(self.board(parts, priority_routes=[(("U1", "1"), ("U1", "2"), 0.3)]), self.lib, Path(self.tmp.name), [])
        self.assertEqual(spec["priority_routes"], [[["U1", "1"], ["U1", "2"], 0.3]])
        for routes, message in (([(("U1", "1"), ("U1", "2"), 0.05)], "minimum track"), ([(("U1", "1"), ("U1", "2"), "jion")], "join")):
            with self.subTest(message=message), self.assertRaisesRegex(SystemExit, message):
                build.spec_for(self.board(parts, priority_routes=routes), self.lib, Path(self.tmp.name), [])

    def test_the_router_cannot_take_the_fanout_and_repairs_rejoin_pour_fragments(self):
        # pcbnew code, read as source: these steps cannot run without KiCad
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        fanout = source[source.index("def fanout("):source.index("REFERENCE_ZONE = ")]
        self.assertEqual(fanout.count(".SetLocked(True)"), 2)                         # the via and its stub
        repair = source[source.index("def repair("):source.index("def ease_vias(")]
        finish = source[source.index("def finish("):source.index('if __name__ == "__main__":')]
        for body in (repair, finish):
            self.assertIn("join_all_fragments(board, spec, filler)", body)
        place = source[source.index("def place("):source.index("def stitch(")]
        self.assertIn("fabrication.route_options(route)", place)
        self.assertIn("MM(width) if width else track_width(spec, net)", place)


# What each board README's Fabrication section says now about its narrowest track, smallest drill and
# vias: (the README's own words, the number in them), None where it states no number. Read by hand on
# 24 Oct 2026 (P3 stage 1); the test checks each phrase is still in the README.
README_FAB = {
    "eos-atmega328p-board": {"narrowest": ("widens it to 0.127 mm, the design's minimum", "0.127"),
                             "drill": ("**Smallest drill:** 0.3 mm (vias)", "0.3"), "vias": ("**Vias:** 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-cm4-base": {"narrowest": ("narrowing to the 0.09 mm four-layer minimum", "0.09"), "drill": None,
                     "vias": ("**Vias:** 0.45 mm with a 0.2 mm drill", ["0.45/0.2"])},
    "eos-cm5-base": {"narrowest": None, "drill": None, "vias": ("**Vias:** 0.45 mm with a 0.2 mm drill", ["0.45/0.2"])},
    "eos-esp32-devkit": {"narrowest": ("**Tracks:** 0.15 mm (the rules allow 0.1 mm at fine-pitch pads; this build narrows none)", "0.15"),
                         "drill": ("**Smallest drill:** 0.2 mm", "0.2"), "vias": ("**Vias:** 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-f280049c-board": {"narrowest": ("0.15 mm tracks, 0.4 mm on VBUS and 5 V", "0.15"),
                           "drill": ("vias 0.6 mm with a 0.3 mm drill, which is the smallest drill", "0.3"),
                           "vias": ("vias 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-feather-rp2040": {"narrowest": ("0.095 mm on the USB-C receptacle's CC contacts", "0.095"),
                           "drill": ("**Smallest drill:** 0.2 mm, in the vias", "0.2"),
                           "vias": ("**Vias:** 0.45 mm with a 0.2 mm drill", ["0.45/0.2"])},
    "eos-ke16z-board": {"narrowest": ("minimum track is set to 0.127 mm (5 mil, `rules`), so the build widens such necks to it", "0.127"),
                        "drill": ("**Smallest drill:** 0.3 mm (vias)", "0.3"), "vias": ("**Vias:** 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-kl25-board": {"narrowest": ("minimum track is set to 0.127 mm (5 mil, `rules`), so the build widens such necks to it", "0.127"),
                       "drill": ("**Smallest drill:** 0.3 mm (vias)", "0.3"), "vias": ("**Vias:** 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-learn-rp2350": {"narrowest": ("narrowing to 0.112 mm where the router necks down", "0.112"), "drill": None,
                         "vias": ("**Vias:** 0.6 mm with a 0.3 mm drill; Raspberry Pi's own copper uses a 0.25 mm drill",
                                  ["0.6/0.3", "0.6/0.25"])},
    "eos-lpc55s69-board": {"narrowest": ("(0.09 mm minimum at fine-pitch pins)", "0.09"), "drill": ("smallest drill 0.3 mm", "0.3"),
                           "vias": ("Vias 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-motion-wing": {"narrowest": ("**Tracks:** 0.15 mm, 0.25 mm on the 3.3 V net", "0.15"),
                        "drill": ("**Smallest drill:** 0.3 mm (vias)", "0.3"), "vias": ("**Vias:** 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-msp430g2-board": {"narrowest": ("narrowing to 0.112 mm where the router necks into the CP2102N's fine-pitch pads", "0.112"),
                           "drill": ("**Smallest drill:** 0.3 mm, in the vias", "0.3"), "vias": ("**Vias:** 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-probe-s3": {"narrowest": ("narrowing to 0.112 mm at fine-pitch pins", "0.112"), "drill": ("**Smallest drill:** 0.2 mm", "0.2"),
                     "vias": ("**Vias:** 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-ra2e1-board": {"narrowest": ("The smallest track is 0.10 mm", "0.10"), "drill": ("**Smallest drill:** 0.3 mm (vias)", "0.3"),
                        "vias": ("**Vias:** 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-ra4m2-board": {"narrowest": ("Choose a fab process that allows 0.11 mm tracks", "0.11"),
                        "drill": ("the smallest drill is 0.3 mm", "0.3"), "vias": ("Vias are 0.6 mm with 0.3 mm drills", ["0.6/0.3"])},
    "eos-rl78g13-board": {"narrowest": None, "drill": None, "vias": ("Standard vias are 0.60 mm with 0.30 mm drill", ["0.6/0.3"])},
    "eos-sense-cape": {"narrowest": ("Measured from the board file: 0.15 mm signal tracks", "0.15"), "drill": None,
                       "vias": ("0.6 mm vias with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-stm32-64": {"narrowest": ("**Tracks:** 0.15 mm signals", "0.15"), "drill": ("**Smallest drill:** 0.3 mm (vias)", "0.3"),
                     "vias": ("**Vias:** 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-tm4c123-board": {"narrowest": ("So the smallest track is 0.10 mm", "0.10"),
                          "drill": ("the smallest drill is 0.3 mm, in the vias", "0.3"), "vias": ("Vias 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
    "eos-tm4c1294-board": {"narrowest": ("0.15 mm tracks (every net that enters the TQFP-128), 0.13 mm on the device USB pair", "0.13"),
                           "drill": ("vias 0.6 mm with a 0.3 mm drill, which is the smallest drill", "0.3"),
                           "vias": ("vias 0.6 mm with a 0.3 mm drill", ["0.6/0.3"])},
}
# Where a README's numbers and the built board disagree today (README first, then the board), from
# test_readme_fabrication_numbers_agree_with_metrics. P4 fixes each README and removes its entries;
# this stage does not edit board READMEs.
README_FAB_MISMATCHES = {
    ("eos-cm4-base", "narrowest", "0.09", 0.1124), ("eos-cm4-base", "drill", None, 0.2),
    ("eos-cm5-base", "narrowest", None, 0.1124), ("eos-cm5-base", "drill", None, 0.2),
    ("eos-f280049c-board", "narrowest", "0.15", 0.1124), ("eos-learn-rp2350", "drill", None, 0.25),
    ("eos-lpc55s69-board", "narrowest", "0.09", 0.1124), ("eos-probe-s3", "narrowest", "0.112", 0.15),
    ("eos-ra2e1-board", "narrowest", "0.10", 0.1124), ("eos-rl78g13-board", "narrowest", None, 0.1124),
    ("eos-rl78g13-board", "drill", None, 0.3), ("eos-sense-cape", "drill", None, 0.3),
    ("eos-stm32-64", "narrowest", "0.15", 0.1124), ("eos-tm4c1294-board", "narrowest", "0.13", 0.09),
}


def _fab_section(name):
    text = (EOS_DIR / name / "README.md").read_text(encoding="utf-8")
    section = text.split("\n## Fabrication", 1)[1].split("\n## ", 1)[0]
    return " ".join(section.split())


FIXED_LINES = {"narrowest": "Narrowest track", "drill": "Smallest drill"}


def _fixed_line(section, item):
    """The number on a README's fixed line, "**Narrowest track:** 0.1124 mm" or "**Smallest drill:** 0.3
    mm", or None. P4 writes these lines from metrics.json; once a README has one, it is what is checked."""
    m = re.search(r"\*\*" + FIXED_LINES[item] + r":\*\* ([0-9.]+) mm", section)
    return m.group(1) if m else None


def _agrees(stated, value):
    """A README's minimum agrees with the board's when it is not above it (a fab process chosen for the
    README's number must make the board) and the board's number, rounded as the README writes it (at
    least two decimals), is the same number (review m7: rounding alone let 0.15 pass for 0.146)."""
    if stated is None or value is None:
        return stated is None and value is None
    decimals = max(2, len(stated.split(".", 1)[1]) if "." in stated else 0)
    return float(stated) <= value + 1e-9 and round(value, decimals) == float(stated)


class MetricsTest(unittest.TestCase):
    """Item 4: the generator's metrics.py reads a built board's fabrication numbers, and each board
    README's Fabrication numbers agree with them (or are listed as known mismatches for P4)."""

    # A small built board, written here so the numbers below stay fixed when P4 rebuilds the real ones:
    # a 30 x 20 mm two-layer board, a resistor on top, a header with a plated slot on the bottom, two
    # track widths, one via, a ground pour, a fiducial rule area, and a BOM with one line lacking an MPN.
    FIXTURE_PCB = """(kicad_pcb (version 20260206) (generator "pcbnew")
  (layers (0 "F.Cu" signal) (2 "B.Cu" signal) (25 "Edge.Cuts" user))
  (setup (pad_to_mask_clearance 0)
    STACKUP)
  (footprint "Resistor_SMD:R_0603_1608Metric" (layer "F.Cu") (at 10 10)
    (property "Reference" "R1" (at 0 0 0)) (attr smd)
    (pad "1" smd roundrect (at -0.8 0) (size 0.8 0.9) (layers "F.Cu" "F.Mask" "F.Paste") (net "/A"))
    (pad "2" smd roundrect (at 0.8 0) (size 0.8 0.9) (layers "F.Cu" "F.Mask" "F.Paste") (net "GND")))
  (footprint "Connector:Slot" (layer "B.Cu") (at 20 10)
    (property "Reference" "J1" (at 0 0 0)) (attr through_hole)
    (pad "1" thru_hole oval (at 0 0) (size 1.2 1.8) (drill oval 0.6 1.2) (layers "*.Cu" "*.Mask") (net "/A"))
    (pad "2" thru_hole circle (at 2.54 0) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask") (net "GND")))
  (footprint "TestPoint:TestPoint_Pad_D1.0mm" (layer "F.Cu") (at 5 15)
    (property "Reference" "TP1" (at 0 0 0)) (attr smd)
    (pad "1" smd circle (at 0 0) (size 1 1) (layers "F.Cu" "F.Mask") (net "GND")))
  FIDUCIALS
  (gr_line (start 0 0) (end 30 0) (layer "Edge.Cuts")) (gr_line (start 30 0) (end 30 20) (layer "Edge.Cuts"))
  (gr_line (start 30 20) (end 0 20) (layer "Edge.Cuts")) (gr_line (start 0 20) (end 0 0) (layer "Edge.Cuts"))
  (segment (start 10.8 10) (end 20 10) (width 0.2) (layer "F.Cu") (net "/A"))
  (segment (start 9.2 10) (end 9.2 13) (width 0.1) (layer "B.Cu") (net "GND"))
  (segment (start 9.2 13) (end 5 15) (width 0.2) (layer "B.Cu") (net "GND"))
  (via (at 9.2 13) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net "GND"))
  (zone (net "GND") (net_name "GND") (layers "F.Cu" "B.Cu") (name "pour"))
  (zone (layer "F.Cu") (name "eos-fiducial-keepout") (keepout (tracks not_allowed) (vias not_allowed)))
)
"""
    STACK = '(stackup (layer "F.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 1" (type "core") ' \
            '(thickness 1.51) (material "FR4") (epsilon_r 4.5)) (layer "B.Cu" (type "copper") (thickness 0.035)) ' \
            '(copper_finish "ENIG") (dielectric_constraints no))'
    FIDS = "".join(f'(footprint "Fiducial:Fiducial_1mm_Mask2mm" (layer "F.Cu") (at {x} {y}) (property "Reference" "FID{i}" ' \
                   f'(at 0 0 0)) (attr smd board_only exclude_from_bom) (pad "" smd circle (at 0 0) (size 1 1) (layers "F.Cu" "F.Mask")))'
                   for i, (x, y) in enumerate(((4, 4), (26, 4), (4, 16)), 1))

    def _fixture(self, stackup=False, fiducials=False):
        folder = Path(tempfile.mkdtemp()) / "eos-fixture"
        (folder / "hardware").mkdir(parents=True)
        (folder / "fab").mkdir()
        self.addCleanup(lambda: __import__("shutil").rmtree(folder.parent))
        text = self.FIXTURE_PCB.replace("STACKUP", self.STACK if stackup else "").replace("FIDUCIALS", self.FIDS if fiducials else "")
        (folder / "hardware" / "eos-fixture.kicad_pcb").write_text(text, encoding="utf-8")
        (folder / "fab" / "eos-fixture-bom.csv").write_text(
            '"Refs","Value","Footprint","Manufacturer","MPN","Description","Qty","DNP"\n'
            '"R1","10k","R_0603_1608Metric","Yageo","RC0603FR-0710KL","","1",""\n'
            '"J1","Header","Slot","","","","1",""\n', encoding="utf-8")
        (folder / "build-report.json").write_text(json.dumps({"erc_violations": 0, "drc_errors": 0, "drc_warnings": 2,
                                                              "drc": {"violations": 2, "unconnected_items": 0, "schematic_parity": 0}}))
        return folder

    def test_metrics_of_a_built_board(self):
        m = metrics.board_metrics(self._fixture(stackup=True, fiducials=True))
        self.assertEqual((m["board"], m["copper_layers"], m["size_mm"]), ("eos-fixture", 2, [30.0, 20.0]))
        self.assertEqual((m["stackup"]["copper"], m["stackup"]["finish"], m["stackup"]["thickness_mm"]), (["F.Cu", "B.Cu"], "ENIG", 1.58))
        self.assertEqual((m["footprints"], m["footprints_by_side"]), (6, {"bottom": 1, "top": 5}))
        self.assertEqual((m["pads"], m["nets"], m["track_segments"]), ({"smd": 6, "thru_hole": 2}, 2, 3))
        self.assertEqual(m["track_length_mm"], {"B.Cu": 7.7, "F.Cu": 9.2})            # 3.0 + 4.65 on B.Cu
        self.assertEqual((m["track_widths_mm"], m["narrowest_track_mm"], m["narrowest_track_segments"]), ({"0.1": 1, "0.2": 2}, 0.1, 1))
        self.assertEqual(m["narrowest_track_at"], [{"net": "GND", "layer": "B.Cu", "start": [9.2, 10.0], "end": [9.2, 13.0], "length_mm": 3.0}])
        self.assertEqual((m["vias"], m["vias_by_size_drill_mm"], m["smallest_drill_mm"]), (1, {"0.6/0.3": 1}, 0.3))
        self.assertEqual(m["plated_slots"], [{"ref": "J1", "pad": "1", "width_mm": 0.6, "length_mm": 1.2}])
        self.assertEqual((m["pours"], m["rule_areas"]), ([{"net": "GND", "layers": ["F.Cu", "B.Cu"]}], {"eos-fiducial-keepout": 1}))
        self.assertEqual((m["test_points"], m["fiducials"], m["smd_sides"], m["fiducial_flags"]),
                         (["TP1"], {"top": [[4.0, 4.0], [4.0, 16.0], [26.0, 4.0]]}, ["top"], []))
        self.assertEqual((m["bom_lines"], m["bom_parts"], m["bom_lines_with_mpn"], m["bom_mpn_coverage"], m["bom_lines_without_mpn"]),
                         (2, 2, 1, 0.5, ["Header (J1)"]))
        self.assertEqual(m["checks"], {"erc": 0, "drc_errors": 0, "drc_warnings": 2, "violations": 2, "unconnected_items": 0,
                                       "schematic_parity": 0})

    def test_fab_problems_name_a_missing_stackup_and_fiducials(self):
        self.assertEqual(metrics.fab_problems(metrics.board_metrics(self._fixture()), 30, 20, 1.0),
                         ["no stack-up in the board file",
                          "top: 0 fiducial(s); three are needed (two diagonally opposite where three do not fit)"])
        self.assertEqual(metrics.fab_problems(metrics.board_metrics(self._fixture(stackup=True, fiducials=True)), 30, 20, 1.0), [])
        m = metrics.board_metrics(self._fixture(stackup=True, fiducials=True))
        m["copper_layers"] = 4
        self.assertEqual(metrics.fab_problems(m, 30, 20, 1.0), ["stack-up has 2 copper layers, the board 4"])
        # review m1/M18: a fiducial left in the BOM, or in the schematic's parity, stops the build
        folder = self._fixture(stackup=True, fiducials=True)
        pcb = folder / "hardware" / "eos-fixture.kicad_pcb"
        pcb.write_text(pcb.read_text(encoding="utf-8").replace("(attr smd board_only exclude_from_bom)", "(attr smd board_only)", 1),
                       encoding="utf-8")
        self.assertEqual(metrics.fab_problems(metrics.board_metrics(folder), 30, 20, 1.0), ["fiducial FID1 not exclude_from_bom"])

    def test_metrics_write_and_read_back(self):
        folder = self._fixture(stackup=True, fiducials=True)
        written = metrics.write(folder)
        self.assertEqual(json.loads((folder / "metrics.json").read_text(encoding="utf-8")), json.loads(json.dumps(written)))

    def test_every_board_narrowest_track_and_vias_read_independently(self):
        for name in EOS_BOARDS:
            pcb = loads((EOS_DIR / name / "hardware" / f"{name}.kicad_pcb").read_text(encoding="utf-8"))
            widths = [round(float(find(s, "width")[1]), 4) for kind in ("segment", "arc") for s in find_all(pcb, kind)]
            m = metrics.board_metrics(EOS_DIR / name)
            with self.subTest(board=name):
                self.assertEqual((m["narrowest_track_mm"], m["narrowest_track_segments"]), (min(widths), widths.count(min(widths))))
                self.assertEqual(m["vias"], len(find_all(pcb, "via")))

    def test_a_build_checks_the_fab_numbers_and_writes_metrics_json(self):
        source = (REPO_ROOT / "tools" / "eos_boards" / "build.py").read_text(encoding="utf-8")
        self.assertIn("problems = metrics.fab_problems(metrics.board_metrics(out, board.name, report)", source)
        self.assertLess(source.index("metrics.write(out, board.name, report)"), source.index('report["outputs"] = sorted('))

    def test_metrics_json_is_what_the_board_files_give(self):
        for name in EOS_BOARDS:
            path = EOS_DIR / name / "metrics.json"
            if path.is_file():               # boards built since P3 stage 1 carry one
                with self.subTest(board=name):
                    self.assertEqual(json.loads(path.read_text(encoding="utf-8")),
                                     json.loads(json.dumps(metrics.board_metrics(EOS_DIR / name))))

    def test_the_readme_rule_for_minima(self):
        self.assertTrue(_agrees("0.112", 0.1124))
        self.assertTrue(_agrees("0.10", 0.1))
        self.assertFalse(_agrees("0.15", 0.146))         # rounds to it, but claims a wider track than the board's
        self.assertFalse(_agrees("0.1", 0.095))
        self.assertFalse(_agrees("0.09", 0.1124))
        self.assertEqual(_fixed_line("x **Narrowest track:** 0.1124 mm (3 segments) y", "narrowest"), "0.1124")
        self.assertEqual(_fixed_line("**Smallest drill:** 0.3 mm (vias).", "drill"), "0.3")
        self.assertIsNone(_fixed_line("narrowing to 0.112 mm", "narrowest"))

    def test_readme_phrases_are_still_there(self):
        self.assertEqual(set(README_FAB), set(EOS_BOARDS))
        for name, claims in README_FAB.items():
            section = _fab_section(name)
            for item, claim in claims.items():
                if claim is not None:
                    with self.subTest(board=name, item=item):
                        self.assertIn(claim[0], section)

    def test_readme_fabrication_numbers_agree_with_metrics(self):
        found = set()
        for name, claims in README_FAB.items():
            path = EOS_DIR / name / "metrics.json"
            m = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else metrics.board_metrics(EOS_DIR / name)
            section = _fab_section(name)
            for item, key in (("narrowest", "narrowest_track_mm"), ("drill", "smallest_drill_mm")):
                stated = _fixed_line(section, item) or (claims[item][1] if claims[item] else None)
                if not _agrees(stated, m[key]):
                    found.add((name, item, stated, m[key]))
                if name not in BUILT_BEFORE_P3:                  # a rebuilt board's README has the fixed lines
                    with self.subTest(board=name, item=item):
                        self.assertIsNotNone(_fixed_line(section, item), f"no **{FIXED_LINES[item]}:** line")
            with self.subTest(board=name, item="vias"):
                self.assertEqual(sorted(claims["vias"][1]), sorted(m["vias_by_size_drill_mm"]))
        self.assertEqual(found, README_FAB_MISMATCHES)


# Boards whose design file has no bench data yet (rails, bring-up); P4 adds theirs and empties the set.
BRINGUP_PENDING = {
    "eos-atmega328p-board", "eos-cm4-base", "eos-cm5-base", "eos-esp32-devkit", "eos-f280049c-board",
    "eos-ke16z-board", "eos-kl25-board", "eos-learn-rp2350", "eos-lpc55s69-board", "eos-msp430g2-board",
    "eos-probe-s3", "eos-ra2e1-board", "eos-ra4m2-board", "eos-rl78g13-board", "eos-sense-cape", "eos-stm32-64",
    "eos-tm4c123-board", "eos-tm4c1294-board"}
# Boards that declare bench data but whose committed README predates it: the build writes the section,
# and the next committed build (P4) brings the README in; then the board leaves this set.
BRINGUP_README_PENDING = {"eos-motion-wing", "eos-feather-rp2040"}
# Test pads older designs draw as BOM parts (Connector:TestPoint with in_bom yes); P4 makes them bench pads.
TEST_PADS_IN_BOM_PENDING = {("eos-stm32-64", "TP1"), ("eos-stm32-64", "TP2"), ("eos-stm32-64", "TP3"),
                            ("eos-stm32-64", "TP4"), ("eos-tm4c123-board", "TP1")}


class _Bench(_Lib):
    """A small design with test pads, a rail link, rails and bring-up data, on a test symbol library."""

    LIBS = {"Connector": """(kicad_symbol_lib (version 20231120) (generator "test")
  (symbol "TestPoint" (in_bom yes) (on_board yes)
    (property "Reference" "TP" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "TestPoint" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (symbol "TestPoint_1_1"
      (pin passive line (at 0 0 90) (length 1.27) (name "1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27))))))))
""", "Jumper": """(kicad_symbol_lib (version 20231120) (generator "test")
  (symbol "SolderJumper_2_Bridged" (in_bom no) (on_board yes)
    (property "Reference" "JP" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "SJ" (at 0 0 0) (effects (font (size 1.27 1.27))))
    (symbol "SolderJumper_2_Bridged_1_1"
      (pin passive line (at -3.81 0 0) (length 1.27) (name "A" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 3.81 0 180) (length 1.27) (name "B" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27))))))))
"""}

    def setUp(self):
        super().setUp()
        for name, text in self.LIBS.items():
            Path(self.tmp.name, f"{name}.kicad_sym").write_text(text)
        self.lib = Library(Path(self.tmp.name))

    def bench(self, **kw):
        parts = [Part("U1", "T:U", "U", "fp", (50, 50), {"VDD": "+3V3", "3": "SIG"}),
                 Part("R1", "T:R", "10k", "fp", (60, 50), {"1": "+3V3_REG", "2": "GND"}),
                 design.rail_link("JP1", "+3V3_REG", "+3V3", (5.0, 5.0, 0.0), (70, 50)),
                 design.bench_pad("TP1", "+3V3", "3V3", (2.0, 2.0), (80, 50)),
                 design.bench_pad("TP2", "GND", "GND", (3.0, 2.0), (90, 50)),
                 design.bench_pad("TP3", "GND", "GND", (4.0, 2.0), (100, 50)),
                 design.bench_pad("TP4", "+3V3_REG", "REG", (5.0, 2.0), (110, 50), diameter=1.5)]
        rails = [design.Rail("+3V3_REG", "the regulator", "3.3 V", "3.25-3.35 V (a data sheet)", ["TP4"], "about 10 kohm",
                             link_note="the regulator's output, before JP1"),
                 design.Rail("+3V3", "JP1 from +3V3_REG", "3.3 V", "3.25-3.35 V (a data sheet)", ["TP1"], "> 100 kohm", link="JP1"),
                 design.Rail("GND", "-", "0 V", "-", ["TP2", "TP3"], "-")]
        bring = design.BringUp(supply="3.3 V on TP1 and TP2", current_limit_ma=20, idle_current="about 0.3 mA",
                               idle_source="estimate", clock="N/A: no clock", programming="N/A: nothing to program",
                               tests=[design.BringUpTest("I2C", "Scan", "finds 0x48")],
                               before_power=["Check the cell's polarity with a meter."])
        args = dict(rails=rails, bringup=bring, temperature_range=(-40, 85, "U1", "rated -40 to +85 C (its data sheet)"),
                    power_nets={"+3V3": "power:+3V3", "GND": "power:GND"})
        args.update(kw)
        return self.board(parts, **args)


class BenchTest(_Bench):
    """Stage 2 items 1-4 and 7: test pads, rail links, the rail list and bring-up data, the README's
    bring-up section, and the honest temperature range."""

    def test_pads_and_links_reach_the_schematic_and_the_spec(self):
        board = self.bench()
        spec = build.spec_for(board, self.lib, Path(self.tmp.name), [])
        flags = {p["ref"]: (p["in_bom"], p["footprint"]) for p in spec["parts"]}
        self.assertEqual(flags["TP1"], (False, "TestPoint:TestPoint_Pad_D1.0mm"))    # copper only: not a BOM line
        self.assertEqual(flags["TP4"], (False, "TestPoint:TestPoint_Pad_D1.5mm"))
        self.assertEqual(flags["JP1"], (False, design.RAIL_LINK_FOOTPRINT))
        self.assertEqual(spec["parts"][2]["pads"], {"1": "/+3V3_REG", "2": "+3V3"})          # +3V3 is a power net
        sch = loads(schematic.write(self.bench(power_nets={}), self.lib))    # no power symbols in the test library
        tp = next(n for n in find_all(sch, "symbol") if any(str(q[1]) == "Reference" and str(q[2]) == "TP1"
                                                            for q in find_all(n, "property")))
        self.assertEqual((str(find(tp, "in_bom")[1]), str(find(tp, "on_board")[1])), ("no", "yes"))
        with self.assertRaisesRegex(ValueError, "diameter"):
            design.bench_pad("TP9", "GND", "GND", (1, 1), (1, 1), diameter=1.2)

    def test_bench_data_is_checked_against_the_design(self):
        good = self.bench()
        build.check_bench(good)
        rails = good.rails
        bad = [({"rails": [dataclasses.replace(rails[0], test_points=[])] + rails[1:]}, "no test point"),
               ({"rails": [dataclasses.replace(rails[0], test_points=["TP1"])] + rails[1:]}, "TP1 is not a test pad"),
               ({"rails": rails[:2] + [dataclasses.replace(rails[2], test_points=["TP2"])]}, "at least two test points"),
               ({"rails": rails[:2] + [dataclasses.replace(rails[2], test_points=["TP2", "U1.3"])]}, "U1.3 is not"),
               ({"rails": [dataclasses.replace(rails[0], net="+5V")] + rails[1:]}, "no part has that net"),
               ({"rails": [dataclasses.replace(rails[0], link_note="")] + rails[1:]}, "no link, and no note"),
               ({"rails": [rails[0], dataclasses.replace(rails[1], link="R1")] + rails[2:]}, "is not a rail link"),
               ({"power_nets": {"+3V3": "power:+3V3", "GND": "power:GND", "SIG": "power:x"}}, "not in the rail list"),
               ({"rails": []}, "needs the rail list"),
               ({"pin_labels": {"U1": {"9": "X"}}}, "pins \\['9'\\]"),
               ({"pin_labels": {"J5": {"1": "X"}}}, "J5, which"),
               ({"temperature_range": (85, -40, "U1", "x")}, "temperature_range"),
               ({"temperature_range": (-40, 85, "U7", "x")}, "temperature_range")]
        for kw, message in bad:
            with self.subTest(kw=str(kw)[:70]), self.assertRaisesRegex(SystemExit, message):
                build.check_bench(self.bench(**kw))
        build.check_bench(self.bench(pin_labels={"U1": {"VDD": "3V3", "3": "IO"}}))    # by pin number or name

    def test_bom_exclusion_test_point_kinds_and_pad_side_are_checked(self):
        # stage-2 review n4: three options the build took on trust
        good = self.bench()
        # 1. only a test pad or a mechanical item may stay out of the BOM
        silent = Part("R9", "T:R", "1k", "fp", (9, 9), {"1": "SIG", "2": "GND"}, in_bom=False)
        board = self.bench()
        board.parts = board.parts + [silent]
        with self.assertRaisesRegex(SystemExit, r"R9 \(T:R\) is left out of the BOM"):
            build.spec_for(board, self.lib, Path(self.tmp.name), [])
        self.assertTrue(all(p["ref"] != "R9" for p in build.spec_for(good, self.lib, Path(self.tmp.name), [])["parts"]))
        # 2. a pin is a test point only on a connector: U1's VDD is on +3V3 but is no probe point
        rails = [dataclasses.replace(good.rails[1], test_points=["TP1", "U1.VDD"])] + good.rails[:1] + good.rails[2:]
        with self.assertRaisesRegex(SystemExit, "U1.VDD is not a test pad or connector pin"):
            build.check_bench(self.bench(rails=rails))
        # 3. test pads on the top side, or a reason
        with self.assertRaisesRegex(ValueError, "needs bottom_reason"):
            design.bench_pad("TP5", "GND", "GND", (6.0, 2.0), (120, 50), side="B")
        bottom = design.bench_pad("TP5", "GND", "GND", (6.0, 2.0), (120, 50), side="B", bottom_reason="under the shield can")
        self.assertEqual(bottom.fields[design.BOTTOM_PAD_FIELD], "under the shield can")
        board = self.bench()
        board.parts = board.parts + [bottom]
        build.check_bench(board)
        board.parts = board.parts[:-1] + [dataclasses.replace(bottom, fields={"Description": "no reason"})]
        with self.assertRaisesRegex(SystemExit, "TP5 is on the bottom side with no reason"):
            build.check_bench(board)

    def test_each_rail_range_holds_its_nominal_and_the_review_figures_are_sourced(self):
        # stage-2 review n5: the Motion Wing's "3.0-3.3 V" made a correct 3.31 V reading fail; three figures had no
        # table or page, and one no source at all
        for name, module in EOS_BOARDS.items():
            board = importlib.import_module(f"eos_boards.boards.{module}").BOARD
            for rail in board.rails:
                found = re.search(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?) V", rail.tolerance)
                nominal = re.match(r"(\d+(?:\.\d+)?) V", rail.nominal)
                if found and nominal:
                    with self.subTest(board=name, rail=rail.net):
                        self.assertLess(float(found.group(1)), float(nominal.group(1)))
                        self.assertLess(float(nominal.group(1)), float(found.group(2)))
        wing = importlib.import_module("eos_boards.boards.eos_motion_wing").BOARD
        feather = importlib.import_module("eos_boards.boards.eos_feather_rp2040").BOARD
        rails = {r.net: r.tolerance for r in feather.rails}
        self.assertIn("3.25-3.35 V", wing.rails[0].tolerance)
        self.assertIn("DS39724 Rev. 2-2, AP2112-3.3 Electrical Characteristics, page 8", wing.rails[0].tolerance)
        self.assertIn("Table 1, page 3", wing.bringup.idle_source)                                   # ADT7410
        self.assertIn("section 2.10.7, Table 192", rails["+1V1"])                                  # RP2040 VREG
        self.assertIn("page 8", rails["+3V3"])
        tests = {t.peripheral: t.passes for t in feather.bringup.tests}
        self.assertIn("estimate", tests["ADC"])
        self.assertIn("192-234 mA", tests["Charger"])
        self.assertIn("page 3", tests["Charger"])

    def test_the_feather_range_names_its_minus_25_connectors(self):
        # stage-2 review n6: the parts review corrected J4 (JST PH S2B-PH-SM4-TB) to -40/+105 C; J5 and J6
        # (JST SH) stop at -25 C with the B3U-1000P buttons
        board = importlib.import_module("eos_boards.boards.eos_feather_rp2040").BOARD
        lo, hi, ref, why = board.temperature_range
        self.assertEqual((lo, hi, ref), (-25, 70, "SW1"))
        self.assertIn("J5 and J6 also stop at -25 C", why.replace("JST SH connectors ", ""))
        self.assertIn("J4 (JST PH) is rated -40 to +105 C", why)
        self.assertNotIn("J4-J6", why)

    def test_no_designs_test_pad_is_a_bom_line(self):
        # stage-2 review n2: a test pad is bare copper with no placement row, so it is no BOM line either.
        # Two older designs still draw theirs as BOM parts; P4 turns them into bench pads (ratchet)
        found = set()
        for path in sorted((REPO_ROOT / "tools" / "eos_boards" / "boards").glob("eos_*.py")):
            board = importlib.import_module(f"eos_boards.boards.{path.stem}").BOARD
            found |= {(board.name, p.ref) for p in board.parts if p.lib_id == design.TESTPOINT_SYMBOL and p.in_bom}
        self.assertEqual(found, TEST_PADS_IN_BOM_PENDING)
        self.assertFalse({name for name, _ in found} - BRINGUP_PENDING)    # a board with bench data has none

    def test_the_readme_section_is_written_from_the_data(self):
        board = self.bench()
        text = build.bringup_markdown(board)
        self.assertTrue(text.startswith(build.BRINGUP_BEGIN + "\n## Bench bring-up\n"))
        self.assertTrue(text.rstrip().endswith(build.BRINGUP_END))
        self.assertIn("Rated operating range: \u221240 to 85 \u00b0C, the narrowest of its parts: U1", text)
        self.assertIn("2. Check the cell's polarity with a meter.", text)
        pads = [p for p in board.parts if p.lib_id == design.TESTPOINT_SYMBOL]
        self.assertIn(f"Test pads (reference, rail, centre in mm from the board's top-left corner, on its top side): "
                      f"{pads[0].ref} {pads[0].value} (+3V3) at ({pads[0].pcb[0]:g}, {pads[0].pcb[1]:g})", text)
        # stage-2 review n3: each reference keyed to its rail; a pad with no label at all is named
        self.assertIn("On the silkscreen each carries its rail name, or its reference where the name has no room.", text)
        self.assertNotIn("no label", text)
        self.assertEqual(build.unlabelled_pads(board, ["TP4.1 REG", "J2.9 D24", "TP1.1 3V3"]), ["TP1", "TP4"])
        some = build.bringup_markdown(board, ["TP1", "TP4"])
        self.assertIn("On the silkscreen each of the others carries its rail name, or its reference where", some)
        self.assertIn("TP1 and TP4 have no label: on this board neither the rail name nor the reference fits beside "
                      "the pad, so this list is how to find them.", some)
        self.assertIn("TP4 has no label: on this board neither the rail name nor the reference fits beside the pad, "
                      "so this list is how to find it.", build.bringup_markdown(board, ["TP4"]))
        every = build.bringup_markdown(board, ["TP1", "TP2", "TP3", "TP4"])                  # the Feather's case
        self.assertIn("None of them is labelled on the silkscreen: on this board neither the rail name nor the "
                      "reference fits beside any of them, so this list is how to find them.", every)
        self.assertNotIn("carries its rail name", every)
        self.assertIn("| +3V3 | TP1 | > 100 kohm |", text)
        self.assertIn("GND test points: TP2, TP3.", text)
        self.assertIn("from a bench supply limited to 20 mA. Expected current: about 0.3 mA (estimate)", text)
        self.assertIn("| +3V3 | JP1 from +3V3_REG | TP1 | 3.3 V | 3.25-3.35 V (a data sheet) |", text)
        self.assertIn("cut JP1's bridge, put an ammeter across its two pads", text)
        self.assertIn("| I2C: Scan | | finds 0x48 | |", text)
        for step in ("### 1. Before power", "### 2. Resistance to GND", "### 3. First power", "### 4. Rail voltages",
                     "### 5. Rail links", "### 6. Clocks", "### 7. Programming", "### 8. Peripheral tests", "### Results"):
            self.assertIn(step, text)
        readme = "# Board\n\nText.\n\n## Rebuild\n\n    python3 build.py\n"
        once = build.update_readme(readme, text)
        self.assertEqual(once.count("## Bench bring-up"), 1)
        self.assertLess(once.index("## Bench bring-up"), once.index("## Rebuild"))
        self.assertEqual(build.update_readme(once, text), once)                       # rewriting changes nothing
        changed = build.update_readme(once, text.replace("20 mA", "50 mA"))
        self.assertEqual((changed.count("## Bench bring-up"), "50 mA" in changed, "20 mA" in changed), (1, True, False))
        self.assertIn("## Bench bring-up", build.update_readme("# Board\n", text))  # no Rebuild heading: at the end

    def test_every_design_with_bench_data_passes_its_checks_and_its_readme_has_the_section(self):
        self.assertFalse(BRINGUP_PENDING & BRINGUP_README_PENDING)
        self.assertLessEqual(BRINGUP_PENDING | BRINGUP_README_PENDING, set(EOS_BOARDS))
        for name, module in EOS_BOARDS.items():
            board = importlib.import_module(f"eos_boards.boards.{module}").BOARD
            readme = (EOS_DIR / name / "README.md").read_text(encoding="utf-8")
            with self.subTest(board=name):
                if name in BRINGUP_PENDING:
                    self.assertIsNone(board.bringup, "declares bring-up data now: take it out of BRINGUP_PENDING")
                    continue
                self.assertIsNotNone(board.bringup)
                build.check_bench(board)
                self.assertTrue(any(r.net == "GND" and len(r.test_points) >= 2 for r in board.rails))
                self.assertIsNotNone(board.temperature_range)
                if name in BRINGUP_README_PENDING:
                    self.assertNotIn(build.BRINGUP_BEGIN, readme, "README has the section: take it out of BRINGUP_README_PENDING")
                else:
                    # the section as the board's own build wrote it, with the pads it left unlabelled
                    report_path = EOS_DIR / name / "build-report.json"
                    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
                    section = build.bringup_markdown(board, build.unlabelled_pads(board, report.get("labels_skipped", [])))
                    self.assertIn(section.strip(), readme)
                    self.assertEqual(readme.count("## Bench bring-up"), 1)


class LabelTest(_Bench):
    """Stage 2 item 5 (A4): pin and test-pad labels on the silkscreen, beside the pad where they fit."""

    def test_spots_beside_a_pad(self):
        pad = (10.0, 20.0, 11.7, 21.7)                          # a 1.7 mm header pad
        vertical = fabrication.label_spots(pad, "vertical", 2.4, 1.0)
        self.assertEqual(vertical[:2], [(13.1, 20.85, 0.0), (8.6, 20.85, 0.0)])          # right, then left, 0.2 mm off
        self.assertEqual(len(vertical), 2 * len(fabrication.LABEL_GAPS))
        horizontal = fabrication.label_spots(pad, "horizontal", 2.4, 1.0)
        self.assertEqual(horizontal[:2], [(10.85, 18.6, 90.0), (10.85, 23.1, 90.0)])     # turned: up, then down
        lone = fabrication.label_spots(pad, "", 2.4, 1.0)
        self.assertEqual([a for _, _, a in lone[:4]], [0.0] * 4)
        self.assertEqual(lone[2:4], [(10.85, 19.3, 0.0), (10.85, 22.4, 0.0)])            # above, below
        gaps = [x - 11.7 - 1.2 for x, _, _ in vertical[::2]]
        self.assertEqual([round(g, 4) for g in gaps], list(fabrication.LABEL_GAPS))       # nearest first

    def test_labels_reach_the_spec_by_pad(self):
        board = self.bench(pin_labels={"U1": {"VDD": "3V3", "3": "IO"}})
        spec = build.spec_for(board, self.lib, Path(self.tmp.name), [])
        self.assertEqual(spec["pin_labels"], {"U1": {"1": "3V3", "3": "IO"}})     # a shared name: its first pad
        self.assertEqual({p["ref"] for p in spec["parts"] if p["test_pad"]}, {"TP1", "TP2", "TP3", "TP4"})
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        labels = source[source.index("def place_labels("):source.index("def place_fiducials(")]
        for needed in ("fabrication.SILK_MIN_TEXT", "fabrication.label_spots(", 'silk["crtyd/"', 'silk[f"fiducial/{i}"]',
                       "skipped.append(", "_silk_clear(spec, item, pads, silk, set())"):
            self.assertIn(needed, labels)

    def test_a_through_hole_pin_may_be_labelled_on_the_back(self):
        """A pin's pad is on both sides, so a label with no room on top goes on the bottom silkscreen,
        mirrored to read from below, and the build report lists it; a test pad (top copper only) never."""
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        labels = source[source.index("def place_labels("):source.index("def place_fiducials(")]
        self.assertIn("sides = [bottom] + ([not bottom] if pad.HasHole() else [])", labels)
        self.assertIn("text(board, label, 0, 0, fabrication.SILK_MIN_TEXT, layer, 0.0, False, bottom)", labels)
        self.assertIn("(P.B_SilkS, P.B_CrtYd) if bottom else (P.F_SilkS, P.F_CrtYd)", labels)
        self.assertIn('spec["labels_on_back"]', labels)
        report = (REPO_ROOT / "tools" / "eos_boards" / "build.py").read_text(encoding="utf-8")
        self.assertIn('report["labels_on_back"] = placed_spec.get("labels_on_back", [])', report)

    def test_a_test_pad_falls_back_to_its_reference(self):
        # stage-2 review n3: where the rail name has no room, the shorter reference ("TP5"), keyed to its rail
        # in the README; only a pad with room for neither is left bare, and the README names it
        source = (REPO_ROOT / "tools" / "eos_boards" / "pcb_build.py").read_text(encoding="utf-8")
        labels = source[source.index("def place_labels("):source.index("def _place_label(")]
        self.assertIn('jobs += [(p["ref"], "1", p["value"], p["ref"]) for p in spec["parts"] if p.get("test_pad")]', labels)
        self.assertIn("tries += [(on_bottom, fallback) for on_bottom in sides]", labels)
        self.assertLess(labels.index("tries = [(on_bottom, label) for on_bottom in sides]"),
                        labels.index("tries += [(on_bottom, fallback) for on_bottom in sides]"))   # the name first
        self.assertIn('spec["labels_as_ref"] = as_ref', labels)
        report = (REPO_ROOT / "tools" / "eos_boards" / "build.py").read_text(encoding="utf-8")
        self.assertIn('report["labels_as_ref"] = placed_spec.get("labels_as_ref", [])', report)
        self.assertIn('bringup_markdown(board, unlabelled_pads(board, report.get("labels_skipped", [])))', report)


class CrashSafetyTest(unittest.TestCase):
    """Issue #70: KiCad 10's bindings can crash a step when a removed item's proxy is freed, so every
    board.Remove() keeps its item referenced, and build.py stops when a pcb_build.py step crashes."""

    def test_every_removal_goes_through_the_retaining_helper(self):
        folder = REPO_ROOT / "tools" / "eos_boards"
        source = (folder / "pcb_build.py").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"\.Remove\(", source)), 1, "a board.Remove() outside _remove")
        helper = source[source.index("def _remove("):]
        helper = helper[:helper.index("\ndef ")]
        self.assertIn("board.Remove(item)", helper)
        self.assertIn("_REMOVED.append(item)", helper)
        for path in sorted(folder.rglob("*.py")):
            if path.name != "pcb_build.py":
                with self.subTest(file=path.name):
                    self.assertNotIn(".Remove(", path.read_text(encoding="utf-8"))

    def _step(self, returncode):
        import contextlib
        import io
        from unittest import mock
        done = subprocess.CompletedProcess(["kicad-python"], returncode, "repaired 0 of 3", "TypeError: not iterable")
        with mock.patch.object(build, "run", return_value=done), \
                mock.patch.object(build.kicad_env, "python", return_value="kicad-python"), \
                contextlib.redirect_stdout(io.StringIO()):
            return build.pcb_step("repair", "spec.json", "board.kicad_pcb", "open.json")

    def test_a_crashed_step_stops_the_build(self):
        for code in (139, -11, 1):                 # a shell's exit 139, a signal, an exception
            with self.subTest(exit=code), self.assertRaisesRegex(SystemExit, rf"pcb_build.py repair failed \(exit {code}\)"):
                self._step(code)
        self.assertEqual(self._step(0).returncode, 0)

    def _check(self, returncode, writes):
        from unittest import mock
        out = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(out))
        report = out / "drc.json"
        report.write_text('{"violations": [], "unconnected_items": [], "schematic_parity": []}')   # the last good build's

        def fake(cmd, **kw):
            self.assertEqual(cmd[-3:], ["-o", report, "board.kicad_pcb"])
            self.assertFalse(report.exists(), "the old report must be gone before kicad-cli runs")
            if writes:
                report.write_text('{"violations": [1]}')
            return subprocess.CompletedProcess(cmd, returncode, "", "")
        with mock.patch.object(build, "run", side_effect=fake), contextlib.redirect_stdout(io.StringIO()):
            return build.kicad_check(["kicad-cli", "pcb", "drc", "--format", "json", "board.kicad_pcb"], report)

    def test_a_crashed_or_silent_kicad_check_never_reads_an_old_report(self):
        self.assertEqual(self._check(0, True), {"violations": [1]})
        for code, writes, message in ((0, False, "no report written"), (134, True, r"exit 134"), (-11, False, r"exit -11")):
            with self.subTest(exit=code, writes=writes), self.assertRaisesRegex(SystemExit, message):
                self._check(code, writes)

    def test_every_pcb_build_step_in_a_build_is_checked(self):
        source = (REPO_ROOT / "tools" / "eos_boards" / "build.py").read_text(encoding="utf-8")
        self.assertEqual(source.count('HERE / "pcb_build.py"'), 1)           # only inside pcb_step
        for mode in ("place", "finish", "ripup", "repair"):
            self.assertIn(f'pcb_step("{mode}"', source)
        self.assertEqual(source.count('"erc", "--format"') + source.count('"drc", "--format"') + source.count('"drc", "--schematic-parity"'),
                         source.count("kicad_check([cli, "))          # every ERC and DRC through kicad_check


if __name__ == "__main__":
    unittest.main()
