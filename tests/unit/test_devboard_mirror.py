"""Issue #48: the mirror holds exactly the verified, openly licensed design files.

Every test is offline. Payloads are synthesised in memory and served by a fake fetcher,
except the last class, which checks the committed mirror against the committed records.
The check also accepts Git LFS pointer files, so it keeps working if the mirror moves
to LFS.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from devboard_cad import mirror  # noqa: E402
from devboard_cad.verify import FetchResult  # noqa: E402

EAGLE_BRD = b'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE eagle SYSTEM "eagle.dtd">\n<eagle version="9.6.2"><drawing/></eagle>\n'
KICAD_PCB = b'(kicad_pcb (version 20240108) (generator "pcbnew"))\n'
GERBER = b"G04 Layer: BottomLayer*\n%FSLAX24Y24*%\n%MOIN*%\nM02*\n"
PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
HTML = b"<!doctype html><html><head><title>Sign in</title></head><body></body></html>"
JSON = b'{"error": "not found"}'


def _zip(members: Dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _entry(url: str, payload: bytes, available: Optional[bool] = True,
           detected: Optional[str] = None) -> dict:
    return {
        "available": available,
        "url": url if available else None,
        "evidence": {"sha256": _sha(payload) if available else None, "size_bytes": len(payload),
                     "captured_at": "2026-09-29T07:22:11Z",
                     "detected_format": detected or (mirror.identify(payload) if available else None)},
    }


def _record(board_id: str, files: dict, redistribution: Optional[bool] = True) -> dict:
    return {
        "board_id": board_id,
        "manufacturer": "Example Corp",
        "board": f"Example {board_id}",
        "part_number": "EX-1",
        "files": files,
        "licenses": {"cad_license": "CC BY-SA 4.0", "hardware_license": "CC BY-SA 4.0",
                     "redistribution_allowed": redistribution,
                     "license_url": "https://creativecommons.org/licenses/by-sa/4.0/"},
    }


class FakeFetcher:
    def __init__(self, payloads: Dict[str, bytes]) -> None:
        self.payloads = payloads

    def get(self, url: str) -> FetchResult:
        payload = self.payloads.get(url)
        return FetchResult(url, 200 if payload is not None else 404, payload, None, url,
                           None if payload is not None else "HTTP 404")


class SelectionTests(unittest.TestCase):
    def test_only_redistributable_boards_are_selected(self) -> None:
        records = [
            _record("open:a", {"eagle": _entry("https://x/a.brd", EAGLE_BRD)}),
            _record("closed:b", {"eagle": _entry("https://x/b.brd", EAGLE_BRD)}, redistribution=None),
            _record("denied:c", {"eagle": _entry("https://x/c.brd", EAGLE_BRD)}, redistribution=False),
        ]
        self.assertEqual([s.board_id for s in mirror.select(records)], ["open:a"])

    def test_unavailable_and_unknown_files_are_not_selected(self) -> None:
        record = _record("open:a", {
            "eagle": _entry("https://x/a.brd", EAGLE_BRD),
            "step": _entry("https://x/a.step", b"", available=None),
            "bom": _entry("https://x/a.csv", b"", available=False),
        })
        self.assertEqual([s.url for s in mirror.select([record])], ["https://x/a.brd"])

    def test_documents_are_not_selected(self) -> None:
        record = _record("open:a", {
            "eagle": _entry("https://x/a.brd", EAGLE_BRD),
            "schematic": _entry("https://x/a.pdf", PDF),
            "bom": _entry("https://x/bom.csv", b"Ref,Value,Footprint\nR1,10k,0402\n"),
        })
        self.assertEqual([s.url for s in mirror.select([record])], ["https://x/a.brd"])

    def test_step_recorded_with_its_schema_is_cad(self) -> None:
        step = b"ISO-10303-21;\nHEADER;\n"
        record = _record("open:a", {
            "step": _entry("https://x/a.stp", step, detected="step:AUTOMOTIVE_DESIGN { 1 0 10303 214 3 1 1 }"),
        })
        self.assertEqual([s.url for s in mirror.select([record])], ["https://x/a.stp"])

    def test_altium_is_cad_and_a_spreadsheet_is_not(self) -> None:
        ole = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 64
        record = _record("open:a", {
            "altium": _entry("https://x/board.PcbDoc", ole, detected="ole"),
            "bom": _entry("https://x/bom.xls", ole, detected="ole"),
        })
        self.assertEqual([s.url for s in mirror.select([record])], ["https://x/board.PcbDoc"])

    def test_one_url_serving_several_formats_is_one_file(self) -> None:
        record = _record("open:a", {
            "eagle": _entry("https://x/a.brd", EAGLE_BRD),
            "pcb_source": _entry("https://x/a.brd", EAGLE_BRD),
        })
        sources = mirror.select([record])
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].formats, ["eagle", "pcb_source"])


class ClassificationTests(unittest.TestCase):
    def test_design_sources_and_fabrication_files_are_cad(self) -> None:
        for payload, name in ((EAGLE_BRD, "a.brd"), (KICAD_PCB, "a.kicad_pcb"), (GERBER, "a.gbl"),
                              (b"ISO-10303-21;\nHEADER;\n", "a.step"), (b"M48\nINCH\nT01C0.02\n", "a.drl")):
            with self.subTest(name=name):
                self.assertEqual(mirror.category(payload, name)[0], "cad")

    def test_binary_stl_is_cad(self) -> None:
        stl = b"\0" * 80 + (1).to_bytes(4, "little") + b"\0" * 50
        self.assertEqual(mirror.category(stl, "case.stl"), ("cad", "stl"))

    def test_pdf_and_bom_are_documents(self) -> None:
        self.assertEqual(mirror.category(PDF, "schematic.pdf"), ("docs", "pdf"))
        self.assertEqual(mirror.category(b"Ref,Value,Footprint\nR1,10k,0402\n", "bom.csv"), ("docs", "csv"))

    def test_web_pages_json_and_unknown_bytes_are_refused(self) -> None:
        for payload in (HTML, JSON, b"\x00\x01\x02 not a format"):
            with self.subTest(payload=payload[:12]):
                self.assertIsNone(mirror.category(payload, "a.brd")[0])

    def test_legacy_ole_is_decided_by_extension(self) -> None:
        ole = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 64
        self.assertEqual(mirror.category(ole, "board.PcbDoc"), ("cad", "altium"))
        self.assertEqual(mirror.category(ole, "bom.xls"), ("docs", "office"))
        self.assertIsNone(mirror.category(ole, "mystery.bin")[0])

    def test_an_archive_is_cad_only_when_it_holds_design_files(self) -> None:
        self.assertEqual(mirror.category(_zip({"gerbers/top.gtl": GERBER}), "fab.zip"), ("cad", "zip"))
        self.assertEqual(mirror.category(_zip({"manual.pdf": PDF}), "docs.zip"), ("docs", "zip"))
        self.assertEqual(mirror.category(_zip({"__MACOSX/._top.gtl": b"x", "a.pdf": PDF}), "z.zip"),
                         ("docs", "zip"))


class PathTests(unittest.TestCase):
    def test_board_directory_is_vendor_then_board(self) -> None:
        self.assertEqual(mirror.board_dir("sparkfun:qwiic-pocket").as_posix(),
                         "boards/cad/sparkfun/qwiic-pocket")

    def test_names_cannot_escape_the_board_directory(self) -> None:
        name = mirror.file_name("https://x/a/..%2F..%2Fetc%2Fpasswd", None)
        self.assertNotIn("/", name)
        self.assertNotIn("..", name)
        directory = mirror.board_dir("../../evil:../x")
        self.assertTrue(directory.as_posix().startswith("boards/cad/"))
        self.assertNotIn("..", directory.parts)

    def test_extension_is_added_from_content_when_the_url_has_none(self) -> None:
        self.assertEqual(mirror.file_name("https://www.ti.com/lit/zip/SPRM860", "zip"), "SPRM860.zip")
        self.assertEqual(mirror.file_name("https://x/Board%20v2.brd", "eagle"), "Board-v2.brd")

    def test_colliding_names_get_a_digest_prefix(self) -> None:
        record = _record("open:a", {
            "eagle": _entry("https://x/rev1/board.brd", EAGLE_BRD),
            "pcb_source": _entry("https://x/rev2/board.brd", EAGLE_BRD + b"<!-- rev2 -->"),
        })
        with tempfile.TemporaryDirectory() as tmp:
            fetcher = FakeFetcher({"https://x/rev1/board.brd": EAGLE_BRD,
                                   "https://x/rev2/board.brd": EAGLE_BRD + b"<!-- rev2 -->"})
            mirror.build(Path(tmp), [record], fetcher)
            names = sorted(p.name for p in (Path(tmp) / "boards/cad/open/a/cad").iterdir())
        self.assertEqual(len(names), 2)
        self.assertIn("board.brd", names)


class BuildTests(unittest.TestCase):
    def _build(self, records, payloads, vendors=()):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        return root, mirror.build(root, records, FakeFetcher(payloads), vendors)

    def test_only_cad_files_are_written_with_attribution_and_manifest(self) -> None:
        record = _record("open:a", {"eagle": _entry("https://x/a.brd", EAGLE_BRD),
                                    "schematic": _entry("https://x/a.pdf", PDF)})
        root, report = self._build([record], {"https://x/a.brd": EAGLE_BRD, "https://x/a.pdf": PDF})
        self.assertTrue(report.ok)
        self.assertEqual((root / "boards/cad/open/a/cad/a.brd").read_bytes(), EAGLE_BRD)
        self.assertFalse((root / "boards/cad/open/a/docs").exists())
        attribution = (root / "boards/cad/open/a/ATTRIBUTION.md").read_text(encoding="utf-8")
        self.assertIn("CC BY-SA 4.0", attribution)
        self.assertIn("https://x/a.brd", attribution)
        self.assertNotIn("https://x/a.pdf", attribution)
        self.assertIn("Changes: none", attribution)
        manifest = json.loads((root / mirror.MANIFEST_PATH).read_text(encoding="utf-8"))
        self.assertEqual({e["category"] for e in manifest["entries"]}, {"cad"})
        self.assertFalse(any(p.suffix == ".json" for p in (root / "boards/cad").rglob("*")))
        self.assertEqual(mirror.check(root, [record]), [])

    def test_bytes_that_differ_from_the_record_are_refused(self) -> None:
        record = _record("open:a", {"eagle": _entry("https://x/a.brd", EAGLE_BRD)})
        root, report = self._build([record], {"https://x/a.brd": EAGLE_BRD + b"tampered"})
        self.assertFalse(report.ok)
        self.assertIn("sha256", report.refused[0])
        self.assertFalse((root / "boards/cad/open/a/cad/a.brd").exists())

    def test_a_web_page_is_refused_even_when_its_digest_matches(self) -> None:
        record = _record("open:a", {"eagle": _entry("https://x/a.brd", HTML, detected="eagle")})
        root, report = self._build([record], {"https://x/a.brd": HTML})
        self.assertFalse(report.ok)
        self.assertIn("not a CAD file", report.refused[0])

    def test_a_rebuild_removes_documents_and_boards_left_without_cad(self) -> None:
        cad_board = _record("open:a", {"eagle": _entry("https://x/a.brd", EAGLE_BRD)})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mirror.build(root, [cad_board], FakeFetcher({"https://x/a.brd": EAGLE_BRD}))
            stale_doc = root / "boards/cad/open/a/docs/a.pdf"
            stale_doc.parent.mkdir(parents=True)
            stale_doc.write_bytes(PDF)
            empty_board = root / "boards/cad/open/docs-only"
            (empty_board / "docs").mkdir(parents=True)
            (empty_board / "docs" / "manual.pdf").write_bytes(PDF)
            (empty_board / "ATTRIBUTION.md").write_text("# old\n", encoding="utf-8")
            self.assertTrue(mirror.check(root, [cad_board]))
            report = mirror.build(root, [cad_board], FakeFetcher({}))
            self.assertIn("boards/cad/open/a/docs/a.pdf", report.removed)
            self.assertFalse(stale_doc.exists())
            self.assertFalse(empty_board.exists())
            self.assertEqual(mirror.check(root, [cad_board]), [])

    def test_an_unreachable_file_is_refused_not_skipped(self) -> None:
        record = _record("open:a", {"eagle": _entry("https://x/a.brd", EAGLE_BRD)})
        root, report = self._build([record], {})
        self.assertFalse(report.ok)
        self.assertEqual(mirror.check(root, [record]), ["missing: open:a https://x/a.brd"])

    def test_vendor_batches_accumulate_in_one_manifest(self) -> None:
        records = [_record("one:a", {"eagle": _entry("https://x/a.brd", EAGLE_BRD)}),
                   _record("two:b", {"eagle": _entry("https://x/b.brd", KICAD_PCB)})]
        payloads = {"https://x/a.brd": EAGLE_BRD, "https://x/b.brd": KICAD_PCB}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mirror.build(root, records, FakeFetcher(payloads), ["one"])
            self.assertEqual(len(mirror.check(root, records)), 1)
            mirror.build(root, records, FakeFetcher(payloads), ["two"])
            self.assertEqual(mirror.check(root, records), [])


    def test_a_rebuild_reuses_mirrored_files_without_fetching(self) -> None:
        record = _record("open:a", {"eagle": _entry("https://x/a.brd", EAGLE_BRD)})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mirror.build(root, [record], FakeFetcher({"https://x/a.brd": EAGLE_BRD}))
            report = mirror.build(root, [record], FakeFetcher({}))
            self.assertTrue(report.ok)
            self.assertEqual(report.unchanged, ["boards/cad/open/a/cad/a.brd"])
            self.assertEqual(mirror.check(root, [record]), [])

    def test_a_mirrored_file_that_no_longer_matches_is_fetched_again(self) -> None:
        record = _record("open:a", {"eagle": _entry("https://x/a.brd", EAGLE_BRD)})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mirror.build(root, [record], FakeFetcher({"https://x/a.brd": EAGLE_BRD}))
            (root / "boards/cad/open/a/cad/a.brd").write_bytes(b"corrupted")
            report = mirror.build(root, [record], FakeFetcher({"https://x/a.brd": EAGLE_BRD}))
            self.assertEqual(report.written, ["boards/cad/open/a/cad/a.brd"])
            self.assertEqual((root / "boards/cad/open/a/cad/a.brd").read_bytes(), EAGLE_BRD)

class CheckTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.record = _record("open:a", {"eagle": _entry("https://x/a.brd", EAGLE_BRD)})
        mirror.build(self.root, [self.record], FakeFetcher({"https://x/a.brd": EAGLE_BRD}))
        self.file = self.root / "boards/cad/open/a/cad/a.brd"

    def _pointer(self, data: bytes) -> bytes:
        return (b"version https://git-lfs.github.com/spec/v1\noid sha256:"
                + _sha(data).encode() + b"\nsize " + str(len(data)).encode() + b"\n")

    def test_an_lfs_pointer_with_the_right_oid_passes(self) -> None:
        self.file.write_bytes(self._pointer(EAGLE_BRD))
        self.assertEqual(mirror.check(self.root, [self.record]), [])

    def test_an_lfs_pointer_with_the_wrong_oid_fails(self) -> None:
        self.file.write_bytes(self._pointer(EAGLE_BRD + b"x"))
        self.assertTrue(any("digest mismatch" in p for p in mirror.check(self.root, [self.record])))

    def test_a_deleted_file_fails(self) -> None:
        self.file.unlink()
        self.assertTrue(any("file absent" in p for p in mirror.check(self.root, [self.record])))

    def test_a_board_that_lost_its_licence_fails(self) -> None:
        withdrawn = dict(self.record, licenses=dict(self.record["licenses"], redistribution_allowed=None))
        problems = mirror.check(self.root, [withdrawn])
        self.assertTrue(any("not redistributable" in p for p in problems))

    def test_a_loose_file_in_the_mirror_root_fails(self) -> None:
        (self.root / "boards/cad/notes.json").write_text("{}", encoding="utf-8")
        self.assertTrue(any("stray file" in p for p in mirror.check(self.root, [self.record])))

    def test_a_stray_file_in_the_store_fails(self) -> None:
        (self.file.parent / "extra.brd").write_bytes(EAGLE_BRD)
        self.assertTrue(any("untracked file" in p for p in mirror.check(self.root, [self.record])))


class LicenceTextTests(unittest.TestCase):
    """MIT, BSD and Apache-2.0 require their text in every copy, so ATTRIBUTION.md carries it."""

    MIT = "MIT License\r\n\r\nCopyright (c) 2021 Example Corp\r\n\r\nPermission is hereby granted, free of charge.\r\n"

    def _mit_record(self) -> dict:
        record = _record("open:a", {"eagle": _entry("https://x/a.brd", EAGLE_BRD)})
        record["licenses"] = dict(record["licenses"], cad_license="MIT", hardware_license="MIT")
        return record

    def _write_notice(self, root: Path, text: str) -> None:
        path = root / mirror.NOTICES_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        notice = {"licence": "MIT", "source": "https://x/LICENSE", "sha256": _sha(text.encode()), "text": text}
        path.write_text(json.dumps({"notices": {"open:a": notice}}), encoding="utf-8")

    def test_the_licence_text_is_written_verbatim_into_the_attribution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_notice(root, self.MIT)
            report = mirror.build(root, [self._mit_record()], FakeFetcher({"https://x/a.brd": EAGLE_BRD}))
            self.assertTrue(report.ok)
            attribution = (root / "boards/cad/open/a/ATTRIBUTION.md").read_text(encoding="utf-8")
            self.assertIn(mirror.LICENCE_TEXT_HEADING, attribution)
            self.assertIn("Copyright (c) 2021 Example Corp", attribution)
            self.assertIn("https://x/LICENSE", attribution)
            self.assertEqual(mirror.check(root, [self._mit_record()]), [])

    def test_a_build_without_the_licence_text_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = mirror.build(Path(tmp), [self._mit_record()], FakeFetcher({"https://x/a.brd": EAGLE_BRD}))
        self.assertFalse(report.ok)
        self.assertIn("needs its licence text", report.refused[0])

    def test_check_fails_when_the_attribution_lost_the_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_notice(root, self.MIT)
            mirror.build(root, [self._mit_record()], FakeFetcher({"https://x/a.brd": EAGLE_BRD}))
            (root / "boards/cad/open/a/ATTRIBUTION.md").write_text("# Example\n", encoding="utf-8")
            problems = mirror.check(root, [self._mit_record()])
        self.assertEqual(problems, ["no MIT licence text in ATTRIBUTION.md: open:a"])

    def test_check_fails_when_the_text_does_not_match_its_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_notice(root, self.MIT)
            mirror.build(root, [self._mit_record()], FakeFetcher({"https://x/a.brd": EAGLE_BRD}))
            notices = json.loads((root / mirror.NOTICES_PATH).read_text(encoding="utf-8"))
            notices["notices"]["open:a"]["sha256"] = "0" * 64
            (root / mirror.NOTICES_PATH).write_text(json.dumps(notices), encoding="utf-8")
            problems = mirror.check(root, [self._mit_record()])
        self.assertEqual(problems, ["licence text does not match its digest: open:a"])

    def test_a_cc_board_with_a_notice_carries_its_copyright_lines(self) -> None:
        record = _record("open:a", {"eagle": _entry("https://x/a.brd", EAGLE_BRD)})
        text = "CC-BY-4.0\n\nCopyright (c) 2017 Example Author\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / mirror.NOTICES_PATH).parent.mkdir(parents=True, exist_ok=True)
            (root / mirror.NOTICES_PATH).write_text(json.dumps({"notices": {"open:a": {
                "licence": "CC BY-SA 4.0", "source": "https://x/LICENSE", "sha256": _sha(text.encode()), "text": text}}}),
                encoding="utf-8")
            report = mirror.build(root, [record], FakeFetcher({"https://x/a.brd": EAGLE_BRD}))
            attribution = (root / "boards/cad/open/a/ATTRIBUTION.md").read_text(encoding="utf-8")
            self.assertEqual(mirror.check(root, [record]), [])
        self.assertTrue(report.ok)
        self.assertIn("Copyright (c) 2017 Example Author", attribution)
        self.assertIn("as the licensor wrote them", attribution)

    def test_share_alike_boards_need_no_licence_text(self) -> None:
        record = _record("open:a", {"eagle": _entry("https://x/a.brd", EAGLE_BRD)})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = mirror.build(root, [record], FakeFetcher({"https://x/a.brd": EAGLE_BRD}))
            attribution = (root / "boards/cad/open/a/ATTRIBUTION.md").read_text(encoding="utf-8")
        self.assertTrue(report.ok)
        self.assertNotIn(mirror.LICENCE_TEXT_HEADING, attribution)


COMMIT = "c" * 40
RAW = f"https://raw.githubusercontent.com/vendor/board/{COMMIT}"
PADS_GERBER = b"*\r\n*\r\nG04 PADS Layout generated Gerber (RS-274-X) file*\r\n%FSLAX35Y35*%\r\nM02*\r\n"
PADS_DRILL = b"%\r\nT1C.00984F0S0\r\nX042087Y042874\r\nX041535Y042894\r\nM30\r\n"
KICAD_SCH = b'(kicad_sch (version 20231120) (generator "eeschema"))\n'


def _blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _repo_record(files: Dict[str, bytes]) -> dict:
    """A record naming the PCB only, pinned to COMMIT; the repository holds ``files``."""
    return _record("vendor:board", {"pcb_source": _entry(f"{RAW}/hw/board.kicad_pcb", files["hw/board.kicad_pcb"])})


def _index(files: Dict[str, bytes]) -> dict:
    return {"vendor:board": {"repository": "vendor/board", "commit": COMMIT, "indexed_at": "2026-10-09T00:00:00Z",
                             "files": [{"path": p, "blob": _blob(d), "size": len(d)} for p, d in sorted(files.items())]}}


class DetectionTests(unittest.TestCase):
    def test_gerber_and_drill_files_without_a_first_line_header_are_cad(self) -> None:
        self.assertEqual(mirror.category(PADS_GERBER, "L1-Top.pho"), ("cad", "gerber"))
        self.assertEqual(mirror.category(PADS_DRILL, "drill.drl"), ("cad", "excellon"))
        self.assertEqual(mirror.category(b"%\nM48\nINCH\nT01C0.02\n%\nX1Y1\n", "board.TXT"), ("cad", "excellon"))

    def test_project_rule_and_model_files_are_cad(self) -> None:
        self.assertEqual(mirror.category(b'{"board": {}, "meta": {"version": 1}}', "a.kicad_pro"), ("cad", "kicad"))
        self.assertEqual(mirror.category(b"(version 1)\n(rule clearance)\n", "a.kicad_dru"), ("cad", "kicad"))
        self.assertEqual(mirror.category(b"update=22/05/2020\n[pcbnew]\nversion=1\n", "a.pro"), ("cad", "kicad"))
        self.assertEqual(mirror.category(b"#VRML V2.0 utf8\nShape {}\n", "part.wrl"), ("cad", "vrml"))
        allegro = b"\x03\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00\t\x00\x00\x00" + b"\x05" * 60
        self.assertEqual(mirror.category(b"\x00\t\x14\x00" + allegro, "board.brd"), ("cad", "allegro"))
        self.assertEqual(mirror.category(b"\x02\x15\x14\x00" + allegro, "BeagleV-FIRE.brd"), ("cad", "allegro"))
        self.assertIsNone(mirror.category(b"\x02\x15\x14\x00" + b"\x05" * 76, "mystery.brd")[0])
        self.assertEqual(mirror.category(b"%TF.GenerationSoftware,KiCad,Pcbnew,8.0.6*%\n%FSLAX46Y46*%\n", "p.GBL"),
                         ("cad", "gerber"))
        self.assertEqual(mirror.category(b";LEADER: 12 \n;HEADER: \n;CODE  : ASCII \n%\nT1C0.0120\nX1200Y3400\n",
                                         "board-1-12.drl"), ("cad", "excellon"))
        self.assertEqual(mirror.category(b"# Blender\nmtllib a.mtl\nv 1.0 2.0 3.0\nv 1 2 4\nv 1 3 3\nf 1 2 3\n", "a.obj"),
                         ("cad", "obj"))
        far_faces = b"mtllib 1.mtl\n\n" + b"v  -3.590774 18.753864 11.200044\n" * 40000 + b"f 1 2 3\n"
        self.assertEqual(mirror.category(far_faces, "Dial_Subject.obj"), ("cad", "obj"))
        allegro_drill = (b";LEADER: 12 \n;HEADER: \n;CODE  : ASCII \n;   Holesize 1. = 8.000000 PLATED MILS\n"
                         b"%\nG90\nX0129522Y0132875\nX0217900Y0044200\nX0135821Y0136025\nM30\n")
        self.assertEqual(mirror.category(allegro_drill, "BeagleBone-AI-1-12.drl"), ("cad", "excellon"))
        self.assertEqual(mirror.category(b"\xef\xbb\xbf[Design]\nVersion=1.0\n", "b.PrjPcb"), ("cad", "altium"))

    def test_text_projects_and_pads_schematics_are_cad(self) -> None:
        kicad5 = b"update=Sunday, September 10, 2017 'PMt' 11:44:10 PM\nversion=1\nlast_client=kicad\n[pcbnew]\n"
        self.assertEqual(mirror.category(kicad5, "feather.pro"), ("cad", "kicad"))
        self.assertEqual(mirror.category(b"[Design]\r\nVersion=1.0\r\n", "board.PrjPcb"), ("cad", "altium"))
        self.assertEqual(mirror.category(b'(ExpressProject ""\r\n  (ProjectVersion "19981106")', "a.opj"),
                         ("cad", "orcad"))
        pads = b"\x00\xfe\x0b\x00" + b"\x00" * 28 + b"\x01\x00\x00\x00L\x02\x00\x00\x15\x00\x00\x00" + b"\x00" * 64
        self.assertEqual(mirror.category(pads, "POWERXEL.sch"), ("cad", "pads"))
        self.assertIsNone(mirror.category(b"\x00\xfe\x0b\x00" + b"\x07" * 80, "mystery.sch")[0])

    def test_prose_json_and_a_readme_are_not_cad(self) -> None:
        self.assertIsNone(mirror.category(b"Order these boards in green.\n", "ordering_instructions.txt")[0])
        self.assertIsNone(mirror.category(b'{"name": "package"}', "package.json")[0])
        self.assertIsNone(mirror.category(b"update=1\n[general]\n", "qt.pro")[0])
        self.assertIsNone(mirror.category(b"EAGLE AutoRouter Statistics:\n\nJob : jig.brd\n", "jig.pro")[0])
        self.assertIsNone(mirror.category(b";\tSTMicroelectronics Project file\n\n[Version]\n", "firmware_v01.stp")[0])


class RepositoryIndexTests(unittest.TestCase):
    TREE = [
        {"path": "hw/board.kicad_pcb", "type": "blob", "sha": "1" * 40, "size": 10},
        {"path": "hw/power.kicad_sch", "type": "blob", "sha": "2" * 40, "size": 10},
        {"path": "fab/board.GTL", "type": "blob", "sha": "3" * 40, "size": 10},
        {"path": "fab/board.TXT", "type": "blob", "sha": "4" * 40, "size": 10},
        {"path": "fab/ordering_instructions.txt", "type": "blob", "sha": "5" * 40, "size": 10},
        {"path": "docs/notes.txt", "type": "blob", "sha": "6" * 40, "size": 10},
        {"path": "docs/schematic.pdf", "type": "blob", "sha": "7" * 40, "size": 10},
        {"path": "fab", "type": "tree", "sha": "8" * 40},
    ]

    def test_every_design_file_at_the_pinned_commit_is_indexed(self) -> None:
        record = _repo_record({"hw/board.kicad_pcb": KICAD_PCB})
        calls = []

        def gh_api(path: str):
            calls.append(path)
            return {"tree": self.TREE, "truncated": False}
        boards, notes = mirror.build_index([record], gh_api, "2026-10-09T00:00:00Z")
        self.assertEqual(calls, [f"repos/vendor/board/git/trees/{COMMIT}?recursive=1"])
        self.assertEqual([f["path"] for f in boards["vendor:board"]["files"]],
                         ["fab/board.GTL", "fab/board.TXT", "hw/board.kicad_pcb", "hw/power.kicad_sch"])
        self.assertEqual(notes, [])

    def test_a_board_that_is_a_folder_indexes_only_that_folder(self) -> None:
        record = _repo_record({"hw/board.kicad_pcb": KICAD_PCB})
        record["sources"] = {"official_cad_repository": f"https://github.com/vendor/board/tree/{COMMIT}/hw"}
        boards, _ = mirror.build_index([record], lambda path: {"tree": self.TREE}, "now")
        self.assertEqual([f["path"] for f in boards["vendor:board"]["files"]],
                         ["hw/board.kicad_pcb", "hw/power.kicad_sch"])

    def test_a_record_spanning_two_commits_is_not_indexed(self) -> None:
        record = _record("vendor:board", {
            "pcb_source": _entry(f"{RAW}/a.kicad_pcb", KICAD_PCB),
            "schematic": _entry(f"https://raw.githubusercontent.com/vendor/board/{'d' * 40}/a.kicad_sch", KICAD_SCH),
        })
        boards, notes = mirror.build_index([record], lambda path: {"tree": []}, "now")
        self.assertEqual(boards, {})
        self.assertIn("2 commits", notes[0])

    def test_the_index_adds_files_and_the_record_file_gains_its_blob(self) -> None:
        files = {"hw/board.kicad_pcb": KICAD_PCB, "hw/power.kicad_sch": KICAD_SCH}
        sources = mirror.select([_repo_record(files)], _index(files))
        self.assertEqual([s.repo_path for s in sources], ["hw/board.kicad_pcb", "hw/power.kicad_sch"])
        self.assertEqual(sources[0].blob, _blob(KICAD_PCB))
        self.assertIsNotNone(sources[0].sha256)
        self.assertIsNone(sources[1].sha256)


class RepositoryBuildTests(unittest.TestCase):
    FILES = {"hw/board.kicad_pcb": KICAD_PCB, "hw/power.kicad_sch": KICAD_SCH, "fab/drill.drl": PADS_DRILL}

    def _build(self, files: Dict[str, bytes], served: Dict[str, bytes], record: Optional[dict] = None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        record = record or _repo_record(files)
        report = mirror.build(root, [record], FakeFetcher(served), index=_index(files))
        return root, record, report

    def test_the_whole_design_is_written_in_the_repository_layout(self) -> None:
        root, record, report = self._build(self.FILES, {f"{RAW}/{p}": d for p, d in self.FILES.items()})
        self.assertTrue(report.ok, report.refused)
        for path, data in self.FILES.items():
            self.assertEqual((root / "boards/cad/vendor/board/cad" / path).read_bytes(), data)
        manifest = json.loads((root / mirror.MANIFEST_PATH).read_text(encoding="utf-8"))
        self.assertEqual({e["git_blob"] for e in manifest["entries"]}, {_blob(d) for d in self.FILES.values()})
        self.assertEqual(mirror.check(root, [record], _index(self.FILES)), [])

    def test_bytes_that_are_not_the_commit_blob_are_refused(self) -> None:
        served = {f"{RAW}/{p}": d for p, d in self.FILES.items()}
        served[f"{RAW}/hw/power.kicad_sch"] = KICAD_SCH + b"; edited\n"
        root, record, report = self._build(self.FILES, served)
        self.assertIn("git blob", report.refused[0])
        self.assertIn(f"missing: vendor:board {RAW}/hw/power.kicad_sch", mirror.check(root, [record], _index(self.FILES)))

    def test_a_git_lfs_pointer_is_resolved_and_checked_against_its_oid(self) -> None:
        step = b"ISO-10303-21;\nHEADER;\nENDSEC;\n"
        pointer = (b"version https://git-lfs.github.com/spec/v1\noid sha256:" + _sha(step).encode()
                   + b"\nsize " + str(len(step)).encode() + b"\n")
        files = {"hw/board.kicad_pcb": KICAD_PCB, "3d/board.step": pointer}
        served = {f"{RAW}/hw/board.kicad_pcb": KICAD_PCB, f"{RAW}/3d/board.step": pointer,
                  f"https://media.githubusercontent.com/media/vendor/board/{COMMIT}/3d/board.step": step}
        root, record, report = self._build(files, served)
        self.assertTrue(report.ok, report.refused)
        self.assertEqual((root / "boards/cad/vendor/board/cad/3d/board.step").read_bytes(), step)

    def test_a_git_lfs_object_missing_from_github_is_left_out_and_listed(self) -> None:
        pointer = (b"version https://git-lfs.github.com/spec/v1\noid sha256:" + b"e" * 64 + b"\nsize 94254684\n")
        files = {"hw/board.kicad_pcb": KICAD_PCB, "3D/board-3d.zip": pointer}
        root, record, report = self._build(files, {f"{RAW}/hw/board.kicad_pcb": KICAD_PCB, f"{RAW}/3D/board-3d.zip": pointer})
        self.assertTrue(report.ok, report.refused)
        manifest = json.loads((root / mirror.MANIFEST_PATH).read_text(encoding="utf-8"))
        self.assertTrue(manifest["excluded"][0]["reason"].startswith(mirror.LFS_MISSING))
        self.assertEqual(mirror.check(root, [record], _index(files)), [])

    def test_an_archive_is_unpacked_to_its_cad_members_and_the_rest_listed(self) -> None:
        archive = _zip({"fab/top.GTL": GERBER, "fab/drill.TXT": PADS_DRILL, "schematic.pdf": PDF,
                        "BOM.xlsx": b"PK\x03\x04 not really", "ordering_instructions.txt": b"Order green.\n"})
        files = {"hw/board.kicad_pcb": KICAD_PCB, "Production/panel.zip": archive}
        root, record, report = self._build(files, {f"{RAW}/{p}": d for p, d in files.items()})
        self.assertTrue(report.ok, report.refused)
        folder = root / "boards/cad/vendor/board/cad/Production/panel"
        self.assertEqual(sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()),
                         ["fab/drill.TXT", "fab/top.GTL"])
        self.assertFalse(any(p.suffix.lower() in (".pdf", ".xlsx", ".zip", ".txt") and p.name != "drill.TXT"
                             for p in (root / "boards/cad").rglob("*")))
        attribution = (root / "boards/cad/vendor/board/ATTRIBUTION.md").read_text(encoding="utf-8")
        self.assertIn(mirror.NOT_COPIED_HEADING, attribution)
        self.assertIn("`schematic.pdf` in panel.zip: PDF document", attribution)
        self.assertEqual(mirror.check(root, [record], _index(files)), [])

    def test_a_licence_covering_only_the_schematic_copies_only_the_schematic(self) -> None:
        archive = _zip({"main.kicad_sch": KICAD_SCH, "main.kicad_pcb": KICAD_PCB,
                        "main.kicad_pro": b'{"meta": {"filename": "main.kicad_pro", "version": 1}}\n'})
        files = {"hw/board.kicad_pcb": KICAD_PCB, "hw/power.kicad_sch": KICAD_SCH,
                 "case/lid.step": b"ISO-10303-21;\nHEADER;\nENDSEC;\n", "kicad.zip": archive}
        record = _repo_record(files)
        record["licenses"].update({"hardware_license": "CC BY-SA 4.0 (schematic only)", "cad_license": None,
                                   "schematic_license": "CC BY-SA 4.0", "pcb_license": None,
                                   "mechanical_cad_license": None})
        root, record, report = self._build(files, {f"{RAW}/{p}": d for p, d in files.items()}, record)
        self.assertTrue(report.ok, report.refused)
        store = root / "boards/cad/vendor/board/cad"
        self.assertEqual(sorted(p.relative_to(store).as_posix() for p in store.rglob("*") if p.is_file()),
                         ["hw/power.kicad_sch", "kicad/main.kicad_sch"])
        attribution = (root / "boards/cad/vendor/board/ATTRIBUTION.md").read_text(encoding="utf-8")
        self.assertIn(mirror.NOT_COVERED_HEADING, attribution)
        for item in ("- `case/lid.step`", "- `hw/board.kicad_pcb`", "- `main.kicad_pcb` in kicad.zip",
                     "- `main.kicad_pro` in kicad.zip"):
            self.assertIn(item, attribution)
        self.assertNotIn(mirror.NOT_COPIED_HEADING, attribution)
        self.assertEqual(mirror.check(root, [record], _index(files)), [])

    @staticmethod
    def _scoped(record: dict, **fields: Optional[str]) -> dict:
        record["licenses"].update({"cad_license": None, "schematic_license": None, "pcb_license": None,
                                   "mechanical_cad_license": None, **fields})
        return record

    def test_an_archive_whose_cad_members_are_all_outside_the_licence_is_left_out_not_missing(self) -> None:
        archive = _zip({"fab/top.GTL": GERBER, "fab/drill.TXT": PADS_DRILL})
        files = {"hw/board.kicad_pcb": KICAD_PCB, "hw/power.kicad_sch": KICAD_SCH, "Production/panel.zip": archive}
        record = self._scoped(_repo_record(files), hardware_license="CC BY-SA 4.0 (schematic only)",
                              schematic_license="CC BY-SA 4.0")
        root, record, report = self._build(files, {f"{RAW}/{p}": d for p, d in files.items()}, record)
        self.assertTrue(report.ok, report.refused)
        manifest = json.loads((root / mirror.MANIFEST_PATH).read_text(encoding="utf-8"))
        self.assertEqual(sorted((e["url"].rsplit("/", 1)[-1], e["reason"]) for e in manifest["excluded"]),
                         [("board.kicad_pcb", mirror.NOT_COVERED_REASON), ("panel.zip", mirror.NOT_COVERED_REASON)])
        self.assertEqual([e["sha256"] for e in manifest["excluded"] if e["url"].endswith("board.kicad_pcb")],
                         [_sha(KICAD_PCB)])
        self.assertEqual(mirror.check(root, [record], _index(files)), [])

    def test_check_fails_when_a_mirrored_file_is_no_longer_covered(self) -> None:
        root, record, report = self._build(self.FILES, {f"{RAW}/{p}": d for p, d in self.FILES.items()})
        self.assertTrue(report.ok, report.refused)
        self._scoped(record, schematic_license="CC BY-SA 4.0")
        problems = mirror.check(root, [record], _index(self.FILES))
        self.assertIn(f"{mirror.NOT_COVERED_REASON}: vendor:board boards/cad/vendor/board/cad/hw/board.kicad_pcb", problems)
        self.assertIn(f"{mirror.NOT_COVERED_REASON}: vendor:board boards/cad/vendor/board/cad/fab/drill.drl", problems)
        self.assertNotIn(f"{mirror.NOT_COVERED_REASON}: vendor:board boards/cad/vendor/board/cad/hw/power.kicad_sch",
                         problems)

    def test_fabrication_files_and_models_are_matched_to_a_licence_by_content(self) -> None:
        cases = {("hw/a.kicad_sch", None): "schematic_license", ("hw/a.SchDoc", "ole"): "schematic_license",
                 ("fab/a.GTL", "gerber"): "pcb_license", ("fab/drill.TXT", "excellon"): "pcb_license",
                 ("fab/a.gl5", "gerber"): "pcb_license", ("case/lid", "step:AUTOMOTIVE_DESIGN"): "mechanical_cad_license",
                 ("a.fzz", "fritzing"): "cad_license", ("a.kicad_pro", "kicad"): "cad_license",
                 ("lib/a.kicad_sym", "kicad"): "cad_license", ("lib/a.SchLib", "ole"): "cad_license"}
        for (name, detected), field_name in cases.items():
            with self.subTest(name=name):
                self.assertEqual(mirror.licence_field(name, detected), field_name)

    def test_a_scoped_licence_does_not_reach_project_and_library_files(self) -> None:
        record = self._scoped(_record("raspberry-pi:5", {}), cad_license="MIT", mechanical_cad_license="MIT")
        self.assertTrue(mirror.covered(record, "rpi-5b.step", "step"))
        for name in ("rpi-5b.kicad_pro", "lib/footprints.kicad_mod", "rpi-5b.kicad_pcb", "drill.TXT"):
            with self.subTest(name=name):
                self.assertFalse(mirror.covered(record, name, "excellon" if name.endswith("TXT") else None))

    def test_a_record_without_per_kind_licence_fields_is_covered_whole(self) -> None:
        record = _record("open:a", {})
        for name in ("a.kicad_sch", "a.kicad_pcb", "a.step", "a.kicad_pro", "fab.zip"):
            with self.subTest(name=name):
                self.assertTrue(mirror.covered(record, name))

    def test_an_indexed_archive_of_documents_is_left_out_not_failed(self) -> None:
        files = {"hw/board.kicad_pcb": KICAD_PCB, "docs/datasheets.zip": _zip({"a.pdf": PDF})}
        root, record, report = self._build(files, {f"{RAW}/{p}": d for p, d in files.items()})
        self.assertTrue(report.ok, report.refused)
        manifest = json.loads((root / mirror.MANIFEST_PATH).read_text(encoding="utf-8"))
        self.assertEqual([e["reason"] for e in manifest["excluded"]], ["archive holds no CAD files"])
        self.assertEqual(mirror.check(root, [record], _index(files)), [])

    def test_a_recorded_archive_of_documents_is_refused(self) -> None:
        record = _record("open:a", {"gerbers": _entry("https://x/fab.zip", _zip({"a.pdf": PDF}), detected="zip")})
        with tempfile.TemporaryDirectory() as tmp:
            report = mirror.build(Path(tmp), [record], FakeFetcher({"https://x/fab.zip": _zip({"a.pdf": PDF})}))
        self.assertIn("archive holds no CAD files", report.refused[0])

    def test_an_archive_holding_a_folder_of_its_own_name_is_not_nested_twice(self) -> None:
        archive = _zip({"panel/panel.GTL": GERBER})
        files = {"hw/board.kicad_pcb": KICAD_PCB, "Production/panel.zip": archive}
        root, record, report = self._build(files, {f"{RAW}/{p}": d for p, d in files.items()})
        self.assertTrue((root / "boards/cad/vendor/board/cad/Production/panel/panel.GTL").is_file())

    def test_a_path_too_long_for_windows_is_flattened(self) -> None:
        deep = "/".join(["a-very-long-folder-name-from-the-vendor"] * 6) + "/board.kicad_sch"
        files = {"hw/board.kicad_pcb": KICAD_PCB, deep: KICAD_SCH}
        root, record, report = self._build(files, {f"{RAW}/{p}": d for p, d in files.items()})
        written = [p for p in (root / "boards/cad").rglob("*.kicad_sch")]
        self.assertEqual(len(written), 1)
        self.assertLessEqual(len(written[0].relative_to(root).as_posix()), mirror.MAX_PATH_LENGTH)
        self.assertEqual(mirror.check(root, [record], _index(files)), [])


class CommittedMirrorTests(unittest.TestCase):
    """The mirror in this repository is complete and every file is the verified one."""

    def test_committed_mirror_is_complete_and_intact(self) -> None:
        records = mirror.load_records(REPO_ROOT)
        self.assertTrue((REPO_ROOT / mirror.MANIFEST_PATH).is_file())
        self.assertEqual(mirror.check(REPO_ROOT, records), [])


if __name__ == "__main__":
    unittest.main()
