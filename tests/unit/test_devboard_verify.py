"""Issue #28: the verifier decides availability from content, and never from a status code.

Every test here is offline. Payloads are synthesised in memory, so the suite is
deterministic and CI never depends on a vendor's CDN being up or willing to serve a bot.
The behaviours pinned below are the ones that were observed to matter against real vendor
infrastructure:

* ``datasheets.raspberrypi.com`` answers HEAD for a real 266 kB ZIP with
  ``content-type: text/html`` and ``content-length: 0``, so headers cannot be trusted and
  only a GET of the body settles anything.
* ``raspberrypi.com`` answers an automated client with a Cloudflare interstitial at
  status 200, so a 200 whose body is HTML must never satisfy a CAD claim.
* A guessed URL that 404s says the guess was wrong, not that the vendor publishes nothing.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from devboard_cad import discover_github as discover  # noqa: E402
from devboard_cad import harvest_github as harvest  # noqa: E402
from devboard_cad import read_licenses as licences  # noqa: E402
from devboard_cad.verify import (  # noqa: E402
    FetchResult,
    Fetcher,
    classify,
    derive_status,
    detect_format,
    is_binary_stl,
    parse_step_header,
    revision_corroborated,
)
from jsonschema import Draft7Validator  # noqa: E402

STEP_BODY = (
    b"ISO-10303-21;\n"
    b"HEADER;\n"
    b"FILE_DESCRIPTION (( 'STEP AP203' ),\n    '1' );\n"
    b"FILE_NAME ('PICO.STEP',\n    '2021-01-22T14:05:44',\n    ( '' ),\n    ( '' ),\n"
    b"    'SwSTEP 2.0',\n    'SolidWorks 2021',\n    '' );\n"
    b"FILE_SCHEMA (( 'CONFIG_CONTROL_DESIGN' ));\n"
    b"ENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"
)
CLOUDFLARE = (
    b"<!DOCTYPE html><html lang=\"en-US\"><head><title>Just a moment...</title>"
    b"<meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\">"
)


def _zip(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _result(payload: bytes | None, status: int | None = 200,
            media_type: str | None = None, error: str | None = None) -> FetchResult:
    return FetchResult("https://vendor.invalid/file", status, payload, media_type,
                       "https://vendor.invalid/file", error)


class TestContentSniffing(unittest.TestCase):
    def test_recognises_the_formats_vendors_actually_ship(self) -> None:
        cases = {
            b"%PDF-1.4\n1 0 obj": "pdf",
            b"PK\x03\x04\x14\x00": "zip",
            STEP_BODY: "step",
            CLOUDFLARE: "html",
            b"EESchema Schematic File Version 4": "kicad",
            b"(kicad_pcb (version 20221018)": "kicad",
            b"<?xml version=\"1.0\"?>\n<eagle version=\"9.6\">": "eagle",
            b"solid boardOutline\n facet normal": "stl",
            b"  0\r\nSECTION\r\n  2\r\nHEADER": "dxf",
            b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": "ole",
        }
        for payload, expected in cases.items():
            self.assertEqual(detect_format(payload), expected, payload[:24])

    def test_a_zip_is_recognised_despite_a_lying_content_type(self) -> None:
        """The Pico case: HEAD said text/html and length 0 for a genuine ZIP."""
        result = _result(_zip({"Pico-R3.step": STEP_BODY}), media_type="text/html")
        self.assertEqual(classify("step", result).available, True)

    def test_a_dxf_comment_line_does_not_hide_the_dxf(self) -> None:
        """Group code 999 is a legal comment; Raspberry Pi's mechanical DXFs open with one,
        so anchoring the SECTION pattern at byte 0 silently rejected real files."""
        self.assertEqual(detect_format(b"999\ndxfrw 0.6.3\n  0\nSECTION\n  2\nHEADER\n"),
                         "dxf")
        self.assertEqual(detect_format(b"  0\r\nSECTION\r\n  2\r\nHEADER\r\n"), "dxf")
        # Still specific: prose that happens to contain the words is not a drawing.
        self.assertIsNone(
            detect_format(b"Some prose mentioning SECTION and HEADER in a sentence.\n"))

    def test_recognises_pcb_fabrication_output(self) -> None:
        """Gerber and Excellon are what 'gerbers' and 'nc_drill' actually resolve to."""
        cases = {
            b"G04 EAGLE Gerber RS-274X export*\nG75*\n%MOMM*%\n": "gerber",
            b"G04 #@! TF.GenerationSoftware,KiCad,Pcbnew*\n": "gerber",
            b"%FSLAX34Y34*%\n%MOMM*%\n": "gerber",
            b"M48\nINCH\nT01C.006\n": "excellon",
        }
        for payload, expected in cases.items():
            self.assertEqual(detect_format(payload), expected, payload[:24])
        self.assertIs(classify("gerbers", _result(b"G04 EAGLE Gerber*\n")).available, True)
        self.assertIs(classify("nc_drill", _result(b"M48\nINCH\n")).available, True)

    def test_delimited_text_is_a_last_resort_and_stays_conservative(self) -> None:
        table = b"Designator,Manufacturer/MPN,Qty,Description\r\n,\"PLACON\",1,\"x\"\r\n"
        self.assertEqual(detect_format(table), "csv")
        self.assertIs(classify("bom", _result(table)).available, True)
        # Prose and binary must not be promoted into a satisfied claim.
        self.assertIsNone(detect_format(b"Just a sentence with no delimiters.\nAnother.\n"))
        self.assertIsNone(detect_format(b"\x00\x01\x02binary,garbage,here\n"))
        self.assertIsNone(classify("bom", _result(b"Just prose.\nMore prose.\n")).available)

    def test_binary_stl_is_detected_by_its_triangle_count(self) -> None:
        payload = b"\x00" * 80 + (2).to_bytes(4, "little") + b"\x00" * 100
        self.assertTrue(is_binary_stl(payload))
        self.assertFalse(is_binary_stl(payload + b"\x00"))


class TestStepHeader(unittest.TestCase):
    def test_reads_schema_tool_and_internal_name(self) -> None:
        header = parse_step_header(STEP_BODY)
        self.assertEqual(header["step_schema"], "CONFIG_CONTROL_DESIGN")
        self.assertEqual(header["internal_name"], "PICO.STEP")
        self.assertEqual(header["timestamp"], "2021-01-22T14:05:44")
        self.assertIn("SolidWorks 2021", header["authoring_tool"] or "")

    def test_a_file_that_names_the_revision_corroborates_it(self) -> None:
        self.assertTrue(revision_corroborated(STEP_BODY, "Pico-R3.step", "Pico-R3"))
        self.assertFalse(revision_corroborated(STEP_BODY, "Pico-R3.step", "Pico-R4"))
        self.assertFalse(revision_corroborated(STEP_BODY, None, "unverified"))


class TestClassification(unittest.TestCase):
    def test_a_guessed_url_that_404s_is_unknown_not_absent(self) -> None:
        verdict = classify("step", _result(None, status=404, error="HTTP 404"))
        self.assertIsNone(verdict.available)
        self.assertIsNone(verdict.evidence)

    def test_an_indexed_url_that_404s_may_be_recorded_absent(self) -> None:
        verdict = classify("step", _result(None, status=404, error="HTTP 404"),
                           absent_on_404=True)
        self.assertIs(verdict.available, False)
        self.assertEqual(verdict.evidence["verification_method"], "http_get_absent")
        self.assertEqual(verdict.evidence["http_status"], 404)

    def test_a_200_serving_html_never_satisfies_a_cad_claim(self) -> None:
        verdict = classify("step", _result(CLOUDFLARE, media_type="text/html"))
        self.assertIsNone(verdict.available)
        self.assertIn("HTML", verdict.reason)

    def test_a_timeout_is_unknown(self) -> None:
        verdict = classify("step", _result(None, status=None, error="timeout"))
        self.assertIsNone(verdict.available)
        self.assertEqual(verdict.reason, "timeout")

    def test_an_archive_must_contain_a_member_that_satisfies_the_claim(self) -> None:
        good = classify("step", _result(_zip({"Pico-R3.step": STEP_BODY})))
        self.assertIs(good.available, True)
        self.assertEqual(good.evidence["contained_member"], "Pico-R3.step")
        self.assertEqual(good.evidence["verification_method"], "http_get_step_header")
        self.assertEqual(good.evidence["detected_format"], "step:CONFIG_CONTROL_DESIGN")

        bad = classify("step", _result(_zip({"readme.txt": b"nothing here"})))
        self.assertIsNone(bad.available)

    def test_macos_resource_forks_do_not_satisfy_a_claim(self) -> None:
        payload = _zip({"__MACOSX/._Pico-R3.step": b"junk", "readme.txt": b"x"})
        self.assertIsNone(classify("step", payload and _result(payload)).available)

    def test_content_must_match_the_declared_format(self) -> None:
        self.assertIsNone(classify("step", _result(b"%PDF-1.4 not a model")).available)
        self.assertIs(classify("schematic", _result(b"%PDF-1.4\n1 0 obj")).available, True)

    def test_a_native_eagle_schematic_satisfies_a_schematic_claim(self) -> None:
        """Issue #28 section 8 counts native schematics, not only schematic PDFs."""
        payload = b"<?xml version=\"1.0\"?>\n<eagle version=\"9.6\"><drawing/></eagle>"
        self.assertIs(classify("schematic", _result(payload)).available, True)

    def test_evidence_produced_by_the_tool_satisfies_the_schema(self) -> None:
        schema = json.loads(
            (REPO_ROOT / "schemas" / "devboard-cad" / "v1" /
             "board-record.schema.json").read_text(encoding="utf-8")
        )
        record = json.loads(
            (REPO_ROOT / "tools" / "devboard_cad" / "records" /
             "raspberry-pi__pico.json").read_text(encoding="utf-8")
        )
        verdict = classify("step", _result(_zip({"Pico-R3.step": STEP_BODY})))
        record["files"]["step"] = {
            "available": verdict.available,
            "url": "https://vendor.invalid/file",
            "verified_revision": None,
            "evidence": verdict.evidence,
        }
        record["record_status"] = derive_status(record)
        errors = list(Draft7Validator(schema).iter_errors(record))
        self.assertEqual(errors, [], errors[:1])


class TestFetchCache(unittest.TestCase):
    """A cached failure is not a result; replaying one would freeze a record at unknown."""

    UNREACHABLE = "http://127.0.0.1:1/never-served"

    def _fetcher(self, directory: str, **kwargs) -> Fetcher:
        return Fetcher(cache_dir=Path(directory), min_interval=0.0, timeout=1.0, **kwargs)

    def test_a_cached_transport_error_is_retried_rather_than_replayed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fetcher = self._fetcher(directory)
            first = fetcher.get(self.UNREACHABLE)
            self.assertIsNone(first.payload)
            self.assertFalse(first.from_cache)
            second = fetcher.get(self.UNREACHABLE)
            self.assertFalse(
                second.from_cache,
                "a transient failure was replayed from cache instead of retried",
            )

    def test_offline_mode_does_replay_what_was_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self._fetcher(directory).get(self.UNREACHABLE)
            offline = self._fetcher(directory, offline=True).get(self.UNREACHABLE)
            self.assertTrue(offline.from_cache)

    def test_a_404_is_definitive_and_may_be_replayed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fetcher = self._fetcher(directory)
            blob, meta = fetcher._paths("https://vendor.invalid/gone")
            Path(directory).mkdir(parents=True, exist_ok=True)
            meta.write_text(json.dumps({"url": "https://vendor.invalid/gone", "status": 404,
                                        "media_type": None, "final_url": None,
                                        "error": "HTTP 404"}), encoding="utf-8")
            replayed = fetcher.get("https://vendor.invalid/gone")
            self.assertTrue(replayed.from_cache)
            self.assertEqual(replayed.status, 404)


class TestDerivedStatus(unittest.TestCase):
    def _record(self, files: dict, **identity) -> dict:
        base = {"part_number": "X", "mcu_soc": "Y", "revision": "R1"}
        base.update(identity)
        base["files"] = files
        return base

    def test_all_unknown_is_incomplete(self) -> None:
        self.assertEqual(derive_status(self._record({"a": {"available": None}})), "incomplete")

    def test_some_known_is_partial(self) -> None:
        record = self._record({"a": {"available": True}, "b": {"available": None}})
        self.assertEqual(derive_status(record), "partial")

    def test_all_known_with_confirmed_identity_is_verified(self) -> None:
        record = self._record({"a": {"available": True}, "b": {"available": False}})
        self.assertEqual(derive_status(record), "verified")

    def test_unverified_identity_holds_a_record_at_partial(self) -> None:
        """Issue #28 section 9: a record must bind an exact part number, not a family."""
        record = self._record({"a": {"available": True}}, part_number="UNVERIFIED")
        self.assertEqual(derive_status(record), "partial")

    def test_a_recorded_finding_is_not_treated_as_an_unfilled_gap(self) -> None:
        """'The vendor publishes no revision' is an answer; 'unverified' is a to-do."""
        files = {"a": {"available": True}, "b": {"available": False}}
        self.assertEqual(derive_status(self._record(files, revision="not-stated")),
                         "verified")
        self.assertEqual(derive_status(self._record(files, mcu_soc="not-applicable")),
                         "verified")
        self.assertEqual(derive_status(self._record(files, revision="unverified")),
                         "partial")
        self.assertEqual(derive_status(self._record(files, mcu_soc="UNVERIFIED")),
                         "partial")


class TestRevisionInference(unittest.TestCase):
    """Vendors put the revision in the filename far more often than in prose."""

    def test_reads_the_revision_the_manufacturer_wrote(self) -> None:
        cases = [
            (["Pico-R3.step"], "R3"),
            (["ALLEGRO/BeagleBone Black_PCB_RevD_250403.brd"], "D"),
            (["thing_plus_v1.2.brd"], "1.2"),
            (["Feather RP2040.brd", "Feather RP2040 rev B.brd"], "B"),
        ]
        for paths, expected in cases:
            self.assertEqual(harvest.infer_revision(paths), expected, paths)

    def test_an_underscore_does_not_hide_a_revision(self) -> None:
        """\\b fails between 'D' and '_', which silently lost every RevX_date filename."""
        self.assertEqual(harvest.infer_revision(["Board_RevC_210222.brd"]), "C")
        self.assertEqual(harvest.infer_revision(["board_v2.1_final.brd"]), "2.1")

    def test_no_revision_in_any_filename_returns_none(self) -> None:
        self.assertIsNone(harvest.infer_revision(["board.kicad_pcb", "README.md"]))

    def test_the_latest_revision_wins(self) -> None:
        self.assertEqual(harvest.infer_revision(["x rev A.brd", "x rev C.brd",
                                                 "x rev B.brd"]), "C")


class TestGithubHarvester(unittest.TestCase):
    PATHS = [
        "Adafruit Feather RP2040.brd",
        "Adafruit Feather RP2040.sch",
        "Adafruit Feather RP2040 Original.brd",
        "Adafruit Feather RP2040 rev B.brd",
        "Adafruit Feather RP2040 pinout.pdf",
        "feather_test/feather_test.c",
        ".DS_Store",
    ]

    def test_one_file_can_answer_several_format_questions(self) -> None:
        found = harvest.classify_paths(self.PATHS)
        self.assertIn("Adafruit Feather RP2040.brd", found["pcb_source"])
        self.assertIn("Adafruit Feather RP2040.brd", found["eagle"])
        self.assertIn("Adafruit Feather RP2040.sch", found["schematic"])
        self.assertIn("Adafruit Feather RP2040 pinout.pdf", found["pinout"])
        self.assertNotIn("step", found)

    def test_dotfiles_are_not_design_files(self) -> None:
        self.assertEqual(harvest.classify_paths([".DS_Store", "__MACOSX/._a.brd"]), {})

    def test_the_current_revision_is_preferred_over_superseded_ones(self) -> None:
        chosen = harvest._pick([
            "Adafruit Feather RP2040 Original.brd",
            "Adafruit Feather RP2040 rev B.brd",
            "Adafruit Feather RP2040.brd",
        ])
        self.assertEqual(chosen, "Adafruit Feather RP2040.brd")

    def test_a_neutral_slot_prefers_the_format_most_people_can_open(self) -> None:
        """'Does this board have PCB source?' should answer with the interoperable file."""
        both = ["EAGLE/PocketBeagle.brd", "KiCAD/PocketBeagle.kicad_pcb"]
        self.assertEqual(harvest._pick(both, "pcb_source"), "KiCAD/PocketBeagle.kicad_pcb")
        # The vendor-specific slot still answers with its own format, so nothing is hidden.
        self.assertEqual(harvest._pick(["EAGLE/PocketBeagle.brd"], "eagle"),
                         "EAGLE/PocketBeagle.brd")
        # Currency still outranks format: a superseded KiCad file loses to the current one.
        self.assertEqual(
            harvest._pick(["old/Board.kicad_pcb", "Board.kicad_pcb"], "pcb_source"),
            "Board.kicad_pcb")

    def test_a_board_in_a_shared_repository_is_recorded_as_its_folder(self) -> None:
        sha = "b" * 40
        meta = {"html_url": "https://github.com/beagleboard/capes"}
        identity = {"manufacturer": "BeagleBoard.org Foundation", "family": "Capes",
                    "board": "BeagleBone Load Cape", "official_product_page": "https://www.beagleboard.org/boards"}
        found = harvest.classify_paths(["beaglebone/Load/Load_Cape.brd", "beaglebone/Load/Load_Cape.sch"])
        record = harvest.build_record("beagleboard:beaglebone-load-cape", "beagleboard/capes", sha, meta,
                                      found, identity, folder="beaglebone/Load")
        self.assertEqual(record["sources"]["official_cad_repository"],
                         f"https://github.com/beagleboard/capes/tree/{sha}/beaglebone/Load")
        self.assertIn("folder beaglebone/Load", record["notes"])
        self.assertTrue(record["files"]["eagle"]["url"].endswith("/beaglebone/Load/Load_Cape.brd"))

    def test_absence_is_claimed_only_against_a_pinned_index(self) -> None:
        files = harvest.build_files("adafruit/X", "a" * 40, harvest.classify_paths(self.PATHS))
        self.assertIs(files["step"]["available"], False)
        self.assertEqual(files["step"]["evidence"]["verification_method"],
                         "official_index_absent")
        self.assertEqual(files["step"]["evidence"]["index_ref"], "adafruit/X@" + "a" * 40)
        # A repository is not evidence about documents that live on product pages.
        self.assertNotIn("user_manual", files)

    def test_mechanical_absence_is_claimable_like_any_other_design_file(self) -> None:
        """It is the only required format that was not, which made 'verified' unreachable."""
        self.assertIn("mechanical", harvest.ABSENCE_CLAIMABLE)
        files = harvest.build_files("o/r", "c" * 40, harvest.classify_paths(self.PATHS))
        self.assertIs(files["mechanical"]["available"], False)

    def test_the_index_only_proposes_presence(self) -> None:
        """Presence is decided by verify.py from bytes, never by a filename in a tree."""
        files = harvest.build_files("adafruit/X", "b" * 40, harvest.classify_paths(self.PATHS))
        self.assertIsNone(files["pcb_source"]["available"])
        self.assertTrue(files["pcb_source"]["url"].startswith(
            "https://raw.githubusercontent.com/adafruit/X/" + "b" * 40))
        self.assertIn("%20", files["pcb_source"]["url"])


class TestDiscovery(unittest.TestCase):
    """Matching repositories to the families issue #28 section 2 names."""

    FAMILIES = ["Feather", "FeatherWing", "QT Py", "Thing Plus", "Pro Micro"]

    def test_the_longest_matching_family_wins(self) -> None:
        self.assertEqual(
            discover.match_family("Adafruit-Feather-RP2040-PCB", "", self.FAMILIES),
            "Feather")
        self.assertEqual(
            discover.match_family("Adafruit-OLED-FeatherWing-PCB", "", self.FAMILIES),
            "FeatherWing")

    def test_a_family_name_must_be_a_whole_token(self) -> None:
        self.assertIsNone(discover.match_family("Weathervane-PCB", "", self.FAMILIES))

    def test_separators_do_not_defeat_matching(self) -> None:
        self.assertEqual(
            discover.match_family("SparkFun_Thing_Plus-RP2040", "", self.FAMILIES),
            "Thing Plus")

    def test_part_numbers_are_read_in_each_vendors_own_notation(self) -> None:
        self.assertEqual(
            discover.extract_part_number("see https://www.adafruit.com/product/4884"), "4884")
        self.assertEqual(
            discover.extract_part_number("SparkFun Thing Plus (DEV-17745)"), "DEV-17745")
        self.assertIsNone(discover.extract_part_number("no product number here"))

    def test_the_longest_mcu_match_wins_so_variants_are_not_truncated(self) -> None:
        self.assertEqual(discover.extract_mcu("ESP32-S3 board"), "ESP32-S3")
        self.assertEqual(discover.extract_mcu("plain ESP32 board"), "ESP32")
        self.assertEqual(discover.extract_mcu("RP2350A"), "RP2350A")
        self.assertIsNone(discover.extract_mcu("a board with no named part"))

    def test_architecture_follows_from_the_mcu(self) -> None:
        self.assertEqual(discover.arch_for("RP2040"), "Dual Arm Cortex-M0+")
        self.assertEqual(discover.arch_for("ESP32-C6"), "RISC-V RV32IMC")
        self.assertEqual(discover.arch_for("ESP32"), "Xtensa LX6")
        self.assertIsNone(discover.arch_for(None))

    def test_add_on_boards_are_recognised(self) -> None:
        """Issue #28 section 2.20 includes FeatherWings; most carry no MCU at all."""
        for name in ("Adafruit-OLED-FeatherWing-PCB", "Motor-Shield-PCB",
                     "Adafruit_TFT_Gizmo", "Adafruit_Charger_BFF",
                     "SparkFun_MicroMod_ATP_Carrier", "beagleboard-capes",
                     "SparkFun_Lumenati_4_Pack", "Teensy_3.x_Feather_Adapter"):
            self.assertTrue(discover.is_addon(name), name)

    def test_an_underscore_does_not_hide_an_add_on(self) -> None:
        """\\bgizmo\\b does not fire between "_" and "G"; separators are normalised first."""
        self.assertTrue(discover.is_addon("Adafruit_TFT_Gizmo"))
        self.assertTrue(discover.is_addon("Adafruit-TFT-Gizmo"))

    def test_a_description_mentioning_a_part_does_not_make_a_board_passive(self) -> None:
        """This put 'not-applicable' on 22 real MCU boards.

        "an Arduino Uno compatible board with a USB-C connector" mentions a connector
        without being one, so generic words are matched against the product NAME only.
        """
        self.assertFalse(discover.is_addon(
            "SparkFun_RedBoard",
            "An Arduino Uno compatible board with a USB-C connector"))
        self.assertFalse(discover.is_addon(
            "RedBoard_Edge",
            "The RedBoard Edge is a RedBoard rebuilt around the idea that projects are "
            "eventually put into an enclosure"))
        self.assertFalse(discover.is_addon(
            "Adafruit-Feather-RP2040-PCB", "Open source PCB files for Feather RP2040"))

    def test_a_description_that_classifies_the_product_is_trusted(self) -> None:
        """"breakout board" is the vendor classifying it, not an incidental mention."""
        self.assertTrue(discover.is_addon(
            "SparkFun_Qwiic_ADXL313", "Qwiic-enabled breakout board for the ADXL313"))
        self.assertTrue(discover.is_addon(
            "SparkFun_Qwiic_GPS_RTK", "Breakout board for the u-blox ZED-F9P"))

    def test_a_wifi_module_is_not_the_boards_processor(self) -> None:
        """WINC1500 matched before SAMD21 and hid the real MCU."""
        self.assertEqual(
            discover.extract_mcu("Feather M0 WiFi with ATSAMD21 and WINC1500"), "ATSAMD21")

    def test_part_numbers_keep_their_own_spelling(self) -> None:
        self.assertEqual(discover.extract_mcu("SiFive Freedom E310"), "SiFive FE310")
        self.assertEqual(discover.extract_mcu("built on the i.MX RT1011"), "i.MX RT1011")
        self.assertEqual(discover.arch_for("ICE40"), "FPGA (no CPU core)")
        self.assertEqual(discover.arch_for("TH1520"), "RISC-V RV64GC")

    def test_a_repository_description_is_not_always_a_product_name(self) -> None:
        """"Mirror of https://openbeagle" names no product; fall back to the repo name."""
        cases = [
            ("beaglebone-ai-64", "Mirror of https://git.beagleboard.org/x",
             "BeagleBoard.org Foundation", "BeagleBoard.org BeagleBone AI 64"),
            ("OSHW-WioTerminal", "Presented by Seeed Studio, we offer our Wio Terminal",
             "Seeed Studio", "Seeed WioTerminal"),
            ("SparkFun_RedBoard_Artemis_Nano",
             "Tiny Arduino compatible carrier board for SparkFun's Artemis module",
             "SparkFun Electronics", "SparkFun RedBoard Artemis Nano"),
        ]
        for repo, desc, mfr, expected in cases:
            self.assertEqual(discover.board_name(repo, desc, mfr), expected, repo)

    def test_boilerplate_wrapping_a_product_name_is_stripped(self) -> None:
        self.assertEqual(
            discover.board_name("Adafruit-Feather-ESP32-S3-PCB",
                                "EagleCAD PCB files for the Adafruit Feather ESP32-S3",
                                "Adafruit Industries"),
            "Adafruit Feather ESP32-S3")
        self.assertEqual(
            discover.board_name("X", "Open source PCB files for Feather RP2040",
                                "Adafruit Industries"),
            "Feather RP2040")

    def test_a_description_is_cut_where_it_stops_naming(self) -> None:
        self.assertEqual(
            discover.board_name("x", "Qwiic Power Switch, which is a power switch for "
                                     "the Qwiic system", "SparkFun Electronics"),
            "Qwiic Power Switch")
        self.assertEqual(
            discover.board_name("x", "SparkFun Qwiic 6DoF BMI270 and the SparkFun Micro "
                                     "Qwiic 6DoF BMI270", "SparkFun Electronics"),
            "SparkFun Qwiic 6DoF BMI270")

    def test_the_manufacturer_is_not_prepended_twice(self) -> None:
        self.assertEqual(
            discover.board_name("x", "Adafruit Circuit Playground Bluefruit",
                                "Adafruit Industries"),
            "Adafruit Circuit Playground Bluefruit")

    def test_slug_fallback_restores_conventional_casing(self) -> None:
        """A lowercase repo slug reads as prose unless acronyms and brands are recased."""
        self.assertEqual(discover.board_name("SparkFun_IoT_RedBoard_ESP32", "",
                                             "SparkFun Electronics"),
                         "SparkFun IoT RedBoard ESP32")
        self.assertEqual(discover.board_name("SparkFun_Qwiic_HAT_for_Raspberry_Pi", "",
                                             "SparkFun Electronics"),
                         "SparkFun Qwiic HAT for Raspberry Pi")
        self.assertEqual(discover.board_name("beaglev-fire", "Mirror of https://x",
                                             "BeagleBoard.org Foundation"),
                         "BeagleBoard.org BeagleV Fire")

    def test_board_id_is_stable_and_filename_safe(self) -> None:
        """The org is already the namespace, so a repeated vendor prefix is dropped."""
        self.assertEqual(
            discover.board_id("adafruit", "Adafruit-Feather-RP2040-PCB"),
            "adafruit:feather-rp2040")
        self.assertEqual(
            discover.board_id("sparkfun", "SparkFun_Thing_Plus-RP2040_Hardware"),
            "sparkfun:thing-plus-rp2040")
        # The ':' separator maps to '__' for the filename, which the gate cross-checks.
        self.assertNotIn("/", discover.board_id("adafruit", "A/B-PCB"))


class TestLicenceReading(unittest.TestCase):
    """Licensing is read from the manufacturer's own words, never inferred from a habit."""

    def _match(self, text: str):
        import re
        return next((name for pattern, name in licences.TEXT_PATTERNS
                     if re.search(pattern, text, re.I)), None)

    def test_house_styles_differ_and_all_of_them_count(self) -> None:
        """Adafruit writes a slash, others a comma; one house style is not the standard."""
        unversioned = "CC BY-SA (version not stated by the manufacturer)"
        self.assertEqual(
            self._match("Creative Commons Attribution/Share-Alike, all text above"),
            unversioned)
        self.assertEqual(
            self._match("Creative Commons Attribution, Share-Alike license, check license.txt"),
            unversioned)
        self.assertEqual(
            self._match("SparkFun hardware is released under Creative Commons "
                        "Share-alike 4.0 International"),
            "CC BY-SA 4.0")

    def test_a_stated_version_outranks_the_unversioned_fallback(self) -> None:
        self.assertEqual(
            self._match("Creative Commons Attribution-ShareAlike 4.0 International"),
            "CC BY-SA 4.0")

    def test_unrecognised_prose_yields_nothing(self) -> None:
        """An unrecognised statement must leave the record UNVERIFIED, not guess."""
        self.assertIsNone(self._match("You may use the design materials as you choose."))
        self.assertIsNone(self._match("Adafruit invests time and resources providing "
                                      "this open source design."))

    def test_every_recognised_licence_has_settled_permissions(self) -> None:
        for name, (_url, redist, mod, comm, attrib) in licences.KNOWN.items():
            for value in (redist, mod, comm, attrib):
                self.assertIsInstance(value, bool, name)

    def test_non_commercial_variants_are_not_recorded_as_commercial(self) -> None:
        """The one way this table could do real downstream harm."""
        for name, (_u, _r, _m, commercial, _a) in licences.KNOWN.items():
            if "NC" in name:
                self.assertFalse(commercial, f"{name} recorded as commercially reusable")

    def test_every_spdx_alias_maps_into_the_permissions_table(self) -> None:
        for spdx, name in licences.SPDX_ALIASES.items():
            self.assertIn(name, licences.KNOWN, f"{spdx} maps to an unknown licence")

    def test_applying_a_licence_records_a_citation(self) -> None:
        record = {"licenses": {"hardware_license": "UNVERIFIED"}, "notes": ""}
        licences.apply_licence(record, "CC BY-SA 4.0", None,
                               "SparkFun hardware is released under CC Share-alike 4.0",
                               "sparkfun/X")
        self.assertEqual(record["licenses"]["hardware_license"], "CC BY-SA 4.0")
        self.assertTrue(record["licenses"]["commercial_use_allowed"])
        self.assertTrue(record["licenses"]["license_url"])
        self.assertIn("sparkfun/X", record["notes"])

    def test_the_unversioned_case_records_what_is_unknown(self) -> None:
        record = {"licenses": {"hardware_license": "UNVERIFIED"}, "notes": ""}
        licences.apply_licence(record, "CC BY-SA (version not stated by the manufacturer)",
                               None, None, "adafruit/X")
        self.assertIn("version is unverified", record["notes"])
        self.assertTrue(record["licenses"]["commercial_use_allowed"])



class TestLicenceFileLookup(unittest.TestCase):
    """GitHub paths are case-sensitive, so the licence file is found by listing the root."""

    @staticmethod
    def _b64(text: str) -> str:
        import base64
        return base64.b64encode(text.encode("utf-8")).decode("ascii")

    def _api(self, files: dict, listing_fails: bool = False):
        def fake(path: str):
            if path.endswith("/contents"):
                if listing_fails:
                    raise RuntimeError("rate limited")
                return [{"name": n, "type": "file"} for n in files] + [{"name": "Hardware", "type": "dir"}]
            if path.endswith("/readme"):
                name = next((n for n in files if n.lower().startswith("readme")), None)
                if name is None:
                    raise RuntimeError("404")
                return {"content": self._b64(files[name])}
            name = path.rsplit("/contents/", 1)[1]
            if name not in files:
                raise RuntimeError("404")
            return {"content": self._b64(files[name])}
        return fake

    SPARKFUN = ("SparkFun License Information\n\nHardware\n---------\n\n"
                "**SparkFun hardware is released under [Creative Commons Share-alike 4.0 International]"
                "(http://creativecommons.org/licenses/by-sa/4.0/).**\n")

    def test_lists_licence_files_in_any_case(self) -> None:
        files = {"license.md": "x", "License.md": "x", "COPYING": "x", "README.md": "x", "licenses.json": "x"}
        from unittest import mock
        with mock.patch.object(licences, "_gh_api", self._api(files)):
            found = licences.licence_files("vendor/board")
        self.assertEqual(found, ["License.md", "license.md", "COPYING"])

    def test_reads_a_lower_case_license_md(self) -> None:
        from unittest import mock
        with mock.patch.object(licences, "_gh_api", self._api({"license.md": self.SPARKFUN, "README.md": "Board"})):
            name, url, quote = licences.read_statement("sparkfun/MicroMod_Artemis_Processor")
        self.assertEqual(name, "CC BY-SA 4.0")
        self.assertEqual(url, "https://github.com/sparkfun/MicroMod_Artemis_Processor/blob/HEAD/license.md")
        self.assertIn("SparkFun hardware is released under", quote)

    def test_falls_back_to_known_spellings_when_the_listing_fails(self) -> None:
        from unittest import mock
        with mock.patch.object(licences, "_gh_api", self._api({"LICENSE.md": self.SPARKFUN}, listing_fails=True)):
            name, url, _quote = licences.read_statement("vendor/board")
        self.assertEqual(name, "CC BY-SA 4.0")
        self.assertTrue(url.endswith("/LICENSE.md"))

    def test_reads_a_readme_whatever_its_case(self) -> None:
        from unittest import mock
        readme = "This board is released under CC BY-SA 4.0."
        with mock.patch.object(licences, "_gh_api", self._api({"Readme.md": readme})):
            name, url, _quote = licences.read_statement("vendor/board")
        self.assertEqual((name, url), ("CC BY-SA 4.0", "https://github.com/vendor/board"))

    def test_a_pointer_to_a_missing_licence_file_stays_unverified(self) -> None:
        from unittest import mock
        readme = "This product is open source! Please review the LICENSE.md file for license information."
        with mock.patch.object(licences, "_gh_api", self._api({"README.md": readme})):
            self.assertEqual(licences.read_statement("vendor/board"), (None, None, None))


class TestLicenceStatements(unittest.TestCase):
    """A statement read from a package applies only to the bytes it was read from."""

    README = (b"Copyright (c) 2014 Example Ltd.\r\n\r\nRedistribution and use in source and binary forms, "
              b"with or without \r\nmodification, are permitted provided that the following conditions \r\nare met:\r\n")

    def _statement(self, package: bytes, **changes) -> dict:
        statement = {
            "board_id": "example:board", "licence": "BSD-3-Clause",
            "source": "https://example.com/package.zip", "member": "README.txt",
            "sha256": hashlib.sha256(package).hexdigest(),
            "quotes": ["Redistribution and use in source and binary forms, with or without modification, "
                       "are permitted provided that the following conditions are met:"],
        }
        statement.update(changes)
        return statement

    @staticmethod
    def _record() -> dict:
        return {"board_id": "example:board", "notes": "Harvested.", "sources": {},
                "licenses": {"hardware_license": "UNVERIFIED", "cad_license": None, "schematic_license": None,
                             "pcb_license": None, "mechanical_cad_license": None,
                             "redistribution_allowed": None, "modification_allowed": None,
                             "commercial_use_allowed": None, "attribution_required": None, "license_url": None}}

    def test_a_quote_across_wrapped_lines_is_found_in_the_package_member(self) -> None:
        package = _zip({"README.txt": self.README, "board.brd": b"<eagle/>"})
        self.assertIsNone(licences.check_statement(self._statement(package), package))

    def test_different_bytes_are_refused(self) -> None:
        package = _zip({"README.txt": self.README})
        problem = licences.check_statement(self._statement(package), package + b"\0")
        self.assertIn("sha256", problem)

    def test_a_quote_that_is_not_in_the_bytes_is_refused(self) -> None:
        package = _zip({"README.txt": self.README})
        problem = licences.check_statement(self._statement(package, quotes=["Released under CC0."]), package)
        self.assertIn("quote not found", problem)

    def test_a_licence_outside_the_settled_table_is_refused(self) -> None:
        package = _zip({"README.txt": self.README})
        problem = licences.check_statement(self._statement(package, licence="Vendor EULA"), package)
        self.assertIn("not in the table", problem)

    def test_a_scoped_statement_sets_only_the_fields_it_covers(self) -> None:
        package = _zip({"README.txt": self.README})
        statement = self._statement(package, licence="MIT", fields=["cad_license", "mechanical_cad_license"],
                                    scope="3D model only")
        record = self._record()
        self.assertTrue(licences.apply_statement(record, statement))
        licenses = record["licenses"]
        self.assertEqual(licenses["hardware_license"], "MIT (3D model only)")
        self.assertEqual((licenses["cad_license"], licenses["schematic_license"]), ("MIT", None))
        self.assertTrue(licenses["redistribution_allowed"])
        self.assertEqual(licenses["license_url"], "https://example.com/package.zip")
        self.assertFalse(licences.apply_statement(record, statement))

    @staticmethod
    def _kicad_with_embedded_frame(frame: bytes) -> bytes:
        from compression import zstd  # type: ignore[import-not-found]
        data = base64.b64encode(zstd.compress(frame)).decode("ascii")
        wrapped = "\n\t\t\t\t".join(data[i:i + 76] for i in range(0, len(data), 76))
        return ('(kicad_sch\n\t(version 20250114)\n\t(embedded_files\n\t\t(file\n'
                '\t\t\t(name "Vendor_Open_Source.kicad_wks")\n\t\t\t(type worksheet)\n'
                f'\t\t\t(data |{wrapped}|)\n\t\t)\n\t)\n)\n').encode("ascii")

    @unittest.skipUnless(sys.version_info >= (3, 14), "compression.zstd is in the standard library from 3.14")
    def test_a_quote_in_a_kicad_embedded_drawing_frame_is_found(self) -> None:
        design = self._kicad_with_embedded_frame(b'(kicad_wks\n\t(tbtext "CC BY-SA 4.0"\n\t\t(name ""))\n)\n')
        package = _zip({"board/main.kicad_sch": design})
        statement = self._statement(package, licence="CC BY-SA 4.0", member="board/main.kicad_sch",
                                    embedded="Vendor_Open_Source.kicad_wks", quotes=['(tbtext "CC BY-SA 4.0"'])
        self.assertIsNone(licences.check_statement(statement, package))
        self.assertIn("quote not found", licences.check_statement(dict(statement, quotes=["CC BY 4.0"]), package))
        self.assertIn("no embedded file", licences.check_statement(dict(statement, embedded="Other.kicad_wks"),
                                                                   package))

    def test_an_embedded_file_is_refused_where_python_has_no_zstd(self) -> None:
        from unittest import mock
        design = b'(kicad_sch\n\t(embedded_files\n\t\t(file\n\t\t\t(name "Vendor_Open_Source.kicad_wks")\n' \
                 b'\t\t\t(type worksheet)\n\t\t\t(data |KLUv/SAA|)\n\t\t)\n\t)\n)\n'
        package = _zip({"board/main.kicad_sch": design})
        statement = self._statement(package, licence="CC BY-SA 4.0", member="board/main.kicad_sch",
                                    embedded="Vendor_Open_Source.kicad_wks", quotes=["CC BY-SA 4.0"])
        with mock.patch.dict(sys.modules, {"compression": None, "compression.zstd": None}):
            problem = licences.check_statement(statement, package)
        self.assertIn("needs Python 3.14", problem)

    def test_a_notice_from_an_embedded_file_keeps_that_file_not_the_design(self) -> None:
        from unittest import mock
        frame = "(kicad_wks\n\t(tbtext \"MIT\")\n\t(tbtext \"Copyright (c) 2026 Example Ltd\")\n)\n"
        design = b"(kicad_sch (embedded_files (file (name \"Frame.kicad_wks\") (type worksheet) (data |AA|))))\n"
        package = _zip({"board/main.kicad_sch": design})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tools/devboard_cad/records").mkdir(parents=True)
            record = self._record()
            record["files"] = {}
            statement = self._statement(package, licence="MIT", member="board/main.kicad_sch",
                                        embedded="Frame.kicad_wks", notice=True,
                                        quotes=["Copyright (c) 2026 Example Ltd"])
            with mock.patch.object(licences, "kicad_embedded_file", return_value=frame):
                licences.apply_statement(record, statement)
                (root / "tools/devboard_cad/records/example__board.json").write_text(json.dumps(record), encoding="utf-8")
                (root / licences.STATEMENTS_PATH).write_text(json.dumps({"statements": [statement]}), encoding="utf-8")

                class Fetch:
                    def get(self, url):
                        return FetchResult(url, 200, package, "application/zip", url, None)
                written, missing = licences.write_notices(root, Fetch())
            notices = json.loads((root / licences.NOTICES_PATH).read_text(encoding="utf-8"))["notices"]
        self.assertEqual((written, missing), (1, []))
        self.assertEqual(notices["example:board"]["text"], frame)

    def test_the_licence_file_is_read_at_the_pinned_commit(self) -> None:
        from unittest import mock
        commit = "a" * 40
        record = {"files": {"pcb_source": {"available": True,
                                           "url": f"https://raw.githubusercontent.com/v/r/{commit}/hw/a.kicad_pcb"}}}
        calls = []

        def fake(path: str):
            calls.append(path)
            return [{"name": "README.md", "type": "file"}, {"name": "LICENSE", "type": "file"}]
        with mock.patch.object(licences, "_gh_api", fake):
            url = licences.github_licence_url(record)
        self.assertEqual(url, f"https://raw.githubusercontent.com/v/r/{commit}/LICENSE")
        self.assertEqual(calls, [f"repos/v/r/contents?ref={commit}"])

    def test_a_notice_statement_keeps_the_licence_file_whatever_the_licence(self) -> None:
        text = b"CC-BY-4.0\n\nCopyright (c) 2017 Aron Phillips, GHI Electronics\n\nAttribution 4.0 International\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tools/devboard_cad/records").mkdir(parents=True)
            record = self._record()
            record["board_id"] = "beagleboard:beaglebone-load-cape"
            record["files"] = {}
            statement = self._statement(text, member=None, licence="CC BY 4.0", notice=True,
                                        board_id=record["board_id"], source="https://example.com/LICENSE",
                                        quotes=["Copyright (c) 2017 Aron Phillips, GHI Electronics"])
            licences.apply_statement(record, statement)
            (root / "tools/devboard_cad/records/beagleboard__beaglebone-load-cape.json").write_text(
                json.dumps(record), encoding="utf-8")
            (root / licences.STATEMENTS_PATH).write_text(json.dumps({"statements": [statement]}), encoding="utf-8")

            class Fetch:
                def get(self, url):
                    return FetchResult(url, 200, text, "text/plain", url, None)
            written, missing = licences.write_notices(root, Fetch())
            notices = json.loads((root / licences.NOTICES_PATH).read_text(encoding="utf-8"))["notices"]
        self.assertEqual((written, missing), (1, []))
        notice = notices["beagleboard:beaglebone-load-cape"]
        self.assertEqual(notice["licence"], "CC BY 4.0")
        self.assertIn("Aron Phillips, GHI Electronics", notice["text"])

    def test_committed_statements_name_settled_licences_and_existing_records(self) -> None:
        body = json.loads((REPO_ROOT / licences.STATEMENTS_PATH).read_text(encoding="utf-8"))
        for statement in body["statements"]:
            with self.subTest(board=statement["board_id"]):
                self.assertIn(statement["licence"], licences.KNOWN)
                self.assertRegex(statement["sha256"], r"^[0-9a-f]{64}$")
                self.assertTrue(statement["quotes"])
                path = REPO_ROOT / "tools/devboard_cad/records" / (statement["board_id"].replace(":", "__") + ".json")
                record = json.loads(path.read_text(encoding="utf-8"))
                expected = statement["licence"] if not statement.get("scope") \
                    else f"{statement['licence']} ({statement['scope']})"
                self.assertEqual(record["licenses"]["hardware_license"], expected)


if __name__ == "__main__":
    unittest.main()
