"""Mirror the openly licensed development-board CAD files into the repository (issue #48).

The database (issue #28) records, for every board, where each design file lives and the
SHA-256 of the bytes that were verified. For the boards whose licence allows
redistribution, this tool keeps an unmodified copy of the board's CAD files under
``boards/cad/<vendor>/<board>/cad/`` so that the designs survive a vendor moving them.

What is copied, and the rules nothing gets past:

1. **Licence first.** Only records with ``licenses.redistribution_allowed`` set to
   ``true`` are mirrored. Unknown is not permission: those boards keep their link and
   digest and nothing else. A licence scoped to part of a design covers only the files of
   its kind (``schematic_license``, ``pcb_license``, ``mechanical_cad_license``; projects,
   libraries and rules need the whole design licensed); the rest are listed in
   ``ATTRIBUTION.md`` and the manifest's ``excluded``, and not copied.
2. **The whole design, not one file per format.** A record names one file per format, but
   a design is more than that: a KiCad project has several schematic sheets, a project file
   and footprints; a board has fabrication outputs and 3D models beside its sources. When a
   record's files are pinned to one commit of the manufacturer's repository, ``index``
   lists every CAD file in that commit (``repo-cad-index.json``) and all of them are
   mirrored, under the repository's own folder layout so that sheets and models still
   resolve.
3. **The bytes must be the verified bytes.** A file the record names must match its
   recorded SHA-256. A file from the repository index must match its git blob ID at the
   pinned commit, the identifier git itself uses, so it is the manufacturer's file exactly.
   A file the repository stores in Git LFS is fetched from LFS and must match the pointer's
   SHA-256.
4. **CAD and nothing else.** Every payload is identified from its content: Eagle, KiCad,
   Altium, OrCAD and Allegro sources and libraries, KiCad project and rule files, Gerber and
   drill files, STEP, IGES, STL, VRML and DXF models. An archive is unpacked and only its
   CAD members are kept; schematic PDFs, BOM spreadsheets, readmes and reports inside it
   are left out and listed in ``ATTRIBUTION.md``. A web page, JSON or anything unrecognised
   is refused and reported, never skipped silently.

Each board's ``ATTRIBUTION.md`` credits the manufacturer, names the licence, and lists every
file with its source and digest. For MIT, BSD and Apache-2.0, whose terms require the
licence text itself to accompany every copy, it also carries that text verbatim from
``licence-notices.json``, and ``check`` fails without it.

The files are committed as regular files (``.gitattributes`` exempts them from the
repository's LFS rules and from line-ending conversion, so the bytes stay identical).
``check`` also accepts Git LFS pointer files, whose ``oid`` is the SHA-256 of the object,
so the mirror can move to LFS later without the check changing.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import urllib.parse
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from devboard_cad.verify import Fetcher, detect_format, is_binary_stl  # noqa: E402

TOOL_ID = "devboard-cad-mirror@0.2.0"
MIRROR_DIR = Path("boards") / "cad"
MANIFEST_PATH = Path("tools") / "devboard_cad" / "mirror-manifest.json"
INDEX_PATH = Path("tools") / "devboard_cad" / "repo-cad-index.json"
NOTICES_PATH = Path("tools") / "devboard_cad" / "licence-notices.json"
ATTRIBUTION_NAME = "ATTRIBUTION.md"
LICENCE_TEXT_HEADING = "## Licence text"
NOT_COPIED_HEADING = "## Not copied"
NOT_COVERED_HEADING = "## Not covered by the licence"
# Licences whose terms require their text to accompany every copy.
NOTICE_LICENCES = frozenset({"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"})
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"
# Marks a problem that is a fact about the repository rather than a failed check.
LFS_MISSING = "its Git LFS object is not on GitHub"
# Windows checkouts fail on paths over 260 characters, and the runner's own prefix takes
# about 50; longer mirror paths are flattened under a digest prefix.
MAX_PATH_LENGTH = 200
# GitHub rejects any single file over 100 MiB; an archive member that large is left out.
GITHUB_FILE_LIMIT = 100 * 1024 * 1024

CAD_FORMATS = frozenset({"eagle", "kicad", "gerber", "excellon", "step", "stl", "dxf",
                         "iges", "vrml", "obj", "allegro"})
DOC_FORMATS = frozenset({"pdf", "csv"})
ALTIUM_SUFFIXES = (".schdoc", ".pcbdoc", ".prjpcb", ".schlib", ".pcblib")
OFFICE_SUFFIXES = (".xls", ".xlsx", ".doc", ".docx")
# Native formats the byte signatures above do not name, accepted by suffix only when the
# content is not a web page or a document: OrCAD and SolidWorks compound files, KiCad's
# JSON project and rule files, binary Eagle 5 and Allegro boards.
NATIVE_SUFFIXES = {
    ".dsn": "orcad", ".opj": "orcad", ".sldprt": "solidworks", ".sldasm": "solidworks",
    ".kicad_pro": "kicad", ".kicad_dru": "kicad",
}
# Native formats that are ZIP containers; kept whole, never unpacked.
CONTAINER_SUFFIXES = {".f3d": "fusion360", ".f3z": "fusion360", ".fcstd": "freecad", ".fzz": "fritzing"}
GERBER_SUFFIXES = (
    ".gbr", ".ger", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gtp", ".gbp", ".gko",
    ".gm1", ".gm2", ".gml", ".gpt", ".gpb", ".g1", ".g2", ".g3", ".g4", ".gl1", ".gl2", ".gl3",
    ".gl4", ".gp1", ".gp2", ".pho", ".art",
)
# Files in a manufacturer's repository that belong to a board's design: native ECAD and
# MCAD sources, projects and libraries, fabrication outputs, 3D models, and archives of
# them (unpacked, CAD members only).
DESIGN_SUFFIXES = (
    ".brd", ".sch", ".lbr", ".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_dru",
    ".kicad_sym", ".kicad_mod", ".step", ".stp", ".iges", ".igs", ".stl", ".wrl", ".obj", ".dxf",
    ".drl", ".xln", ".exc", ".pro", ".zip",
) + GERBER_SUFFIXES + ALTIUM_SUFFIXES + tuple(NATIVE_SUFFIXES) + tuple(CONTAINER_SUFFIXES)
# Eagle writes the drill file of a Gerber set as .TXT; a .txt beside Gerber layers is indexed
# and kept only if its content is Excellon. Names that are plainly prose are not fetched.
PROSE_NAME = re.compile(r"(readme|licen[cs]e|copying|order|instruction|note)", re.IGNORECASE)
CAD_MEMBER_SUFFIXES = tuple(s for s in DESIGN_SUFFIXES if s != ".zip")
# Which licence field covers a file. A statement scoped to part of a design leaves the other
# fields empty (Raspberry Pi 5: only its 3D model), so only the files it covers are copied.
# Fabrication files and models are known by their content, whatever their suffix; a native
# design document by its suffix. Projects, libraries and rules belong to the whole design and
# fall under cad_license, which a scoped licence does not reach.
FABRICATION_FORMATS = frozenset({"gerber", "excellon"})
MODEL_FORMATS = frozenset({"step", "iges", "stl", "vrml", "obj", "dxf"})
SCHEMATIC_SUFFIXES = (".sch", ".kicad_sch", ".schdoc", ".dsn")
PCB_SUFFIXES = (".brd", ".kicad_pcb", ".pcbdoc", ".drl", ".xln", ".exc") + GERBER_SUFFIXES
MECHANICAL_SUFFIXES = (".step", ".stp", ".iges", ".igs", ".stl", ".wrl", ".obj", ".dxf",
                       ".sldprt", ".sldasm", ".f3d", ".f3z", ".fcstd")
KIND_FIELDS = ("schematic_license", "pcb_license", "mechanical_cad_license")
NOT_COVERED_REASON = "not covered by the licence"
EXTENSION_FOR_FORMAT = {
    "pdf": ".pdf", "zip": ".zip", "step": ".step", "stl": ".stl", "dxf": ".dxf",
    "gerber": ".gbr", "excellon": ".drl", "csv": ".csv", "eagle": ".xml",
}
RAW_GITHUB = re.compile(r"^https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([0-9a-f]{40})/(.+)$")
# A record for one board of a repository that holds several names the board's folder.
TREE_FOLDER = re.compile(r"github\.com/[^/]+/[^/]+/tree/[0-9a-f]{40}/(.+?)/?$")


# --------------------------------------------------------------------------------------
# selection
# --------------------------------------------------------------------------------------

@dataclass
class Source:
    """One file of one board: from its record (with a SHA-256) or its repository (a blob)."""

    record: Dict[str, Any]
    url: str
    sha256: Optional[str]
    size_bytes: Optional[int]
    captured_at: Optional[str]
    detected: Optional[str] = None
    formats: List[str] = field(default_factory=list)
    blob: Optional[str] = None
    repo_path: Optional[str] = None

    @property
    def board_id(self) -> str:
        return str(self.record["board_id"])


def redistributable(record: Dict[str, Any]) -> bool:
    return (record.get("licenses") or {}).get("redistribution_allowed") is True


def licence_field(name: str, detected: Optional[str] = None) -> str:
    """The record's licence field that covers the file ``name`` of format ``detected``.

    >>> licence_field("hw/power.kicad_sch")
    'schematic_license'
    >>> licence_field("fab/drill.TXT", "excellon")
    'pcb_license'
    """
    fmt = (detected or "").split(":", 1)[0]
    if fmt in FABRICATION_FORMATS:
        return "pcb_license"
    if fmt in MODEL_FORMATS:
        return "mechanical_cad_license"
    ext = suffix(name)
    if ext in SCHEMATIC_SUFFIXES:
        return "schematic_license"
    if ext in PCB_SUFFIXES:
        return "pcb_license"
    if ext in MECHANICAL_SUFFIXES:
        return "mechanical_cad_license"
    return "cad_license"


def covered(record: Dict[str, Any], name: str, detected: Optional[str] = None) -> bool:
    """Whether the board's licence covers the file ``name`` of format ``detected``.

    A field the record does not carry falls back to cad_license, so a record licensed as a
    whole is unaffected. A project, library or rule file needs the whole design licensed: a
    licence that leaves any kind of file out does not reach it, even when cad_license is set.

    >>> covered({"licenses": {"cad_license": None, "schematic_license": "CC BY-SA 4.0"}}, "a.kicad_pcb")
    False
    """
    licences = record.get("licenses") or {}
    field_name = licence_field(name, detected)
    if field_name == "cad_license" and any(k in licences and not licences[k] for k in KIND_FIELDS):
        return False
    return bool(licences.get(field_name, licences.get("cad_license")))


def recorded_kind(detected: Optional[str], url: str) -> str:
    """``cad`` or ``docs`` from the format the verifier recorded, before any bytes are read.

    The verifier records STEP with its schema, e.g. ``step:AUTOMOTIVE_DESIGN { ... }``, so
    only the part before the colon names the format.
    """
    detected = (detected or "").split(":", 1)[0] or None
    if detected in CAD_FORMATS or detected == "zip":
        return "cad"
    if detected == "ole" and file_name(url, None).lower().endswith(ALTIUM_SUFFIXES):
        return "cad"
    return "docs"


def pinned_path(url: str) -> Optional[Tuple[str, str, str, str]]:
    """``(owner, repo, commit, path)`` for a raw GitHub URL pinned to a commit, else None."""
    match = RAW_GITHUB.match(url)
    if not match:
        return None
    owner, repo, commit, path = match.groups()
    return owner, repo, commit, urllib.parse.unquote(path)


def raw_url(owner: str, repo: str, commit: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{commit}/{urllib.parse.quote(path)}"


def select(records: Iterable[Dict[str, Any]],
           index: Optional[Dict[str, Any]] = None) -> List[Source]:
    """Every CAD file of every redistributable board, one entry per URL per board.

    The record's verified files come first; the repository index adds every other CAD
    file at the same pinned commit.
    """
    index = index or {}
    out: List[Source] = []
    for record in records:
        if not redistributable(record):
            continue
        by_url: Dict[str, Source] = {}
        for name, entry in sorted((record.get("files") or {}).items()):
            if not isinstance(entry, dict) or entry.get("available") is not True:
                continue
            evidence = entry.get("evidence") or {}
            url, digest = entry.get("url"), evidence.get("sha256")
            if not url or not digest:
                continue
            if recorded_kind(evidence.get("detected_format"), url) != "cad":
                continue
            source = by_url.get(url)
            if source is None:
                pinned = pinned_path(url)
                source = Source(record, url, digest, evidence.get("size_bytes"),
                                evidence.get("captured_at"), evidence.get("detected_format"),
                                repo_path=pinned[3] if pinned else None)
                by_url[url] = source
            source.formats.append(name)
        repo = index.get(str(record["board_id"]))
        if repo:
            owner, name = repo["repository"].split("/", 1)
            by_path = {s.repo_path: s for s in by_url.values() if s.repo_path}
            for item in repo["files"]:
                known = by_path.get(item["path"])
                if known is not None:
                    known.blob = item["blob"]
                    continue
                url = raw_url(owner, name, repo["commit"], item["path"])
                by_url[url] = Source(record, url, None, item.get("size"), repo.get("indexed_at"),
                                     blob=item["blob"], repo_path=item["path"])
        out.extend(by_url.values())
    out.sort(key=lambda s: (s.board_id, s.url))
    return out


# --------------------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------------------

_EXCELLON = re.compile(rb"^M48\s*$", re.MULTILINE)
# Header-less Excellon, as PADS writes it: a tool definition and drill coordinates.
_EXCELLON_TOOL = re.compile(rb"^T\d+C\d*\.?\d+", re.MULTILINE)
_EXCELLON_HIT = re.compile(rb"^X-?\d+\.?\d*Y-?\d+", re.MULTILINE)
# Allegro NC drill: a ';' comment header, then '%' and G90, then bare coordinates.
_EXCELLON_START = re.compile(rb"^(%|G90|M48|;HEADER:)\s*$", re.MULTILINE)
# Gerber whose header is not on the first line: PADS opens with '*' lines, X2 with %TF.
_GERBER_LINE = re.compile(rb"^(G04[ *]|G75\*|%(FS|MO|AD|LP|IN|TF|TA|TO)[A-Z.])", re.MULTILINE)
_ALLEGRO_MAJOR = range(0x12, 0x18)
# Every Allegro board seen so far (16.x to 23.x) carries this after its format word.
_ALLEGRO_TAIL = b"\x03\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00"
_OBJ_VERTEX = re.compile(rb"^v\s+-?[\d.]+(e-?\d+)?\s+-?[\d.]+", re.MULTILINE)
_OBJ_FACE = re.compile(rb"^f\s+\d+", re.MULTILINE)


def identify(payload: bytes) -> Optional[str]:
    """Name the payload's format from its bytes, or None when it is not recognised."""
    head = payload[:8192]
    found = detect_format(head)
    if found is None and is_binary_stl(payload):
        return "stl"
    # Gerber X2 attributes and drill comments carry commas, so CSV is no verdict for them.
    if found in (None, "csv"):
        stripped = head.lstrip()
        hits = len(_EXCELLON_HIT.findall(payload[:65536]))
        if _EXCELLON.search(head[:4096]) or (hits and _EXCELLON_TOOL.search(head)) \
                or (hits >= 3 and _EXCELLON_START.search(head)):
            return "excellon"
        if _GERBER_LINE.search(head[:2048]):
            return "gerber"
    if found is None:
        if stripped.startswith(b"#VRML"):
            return "vrml"
        first = stripped.split(b"\n", 1)[0].rstrip(b"\r")
        if len(first) == 80 and first[72:73] == b"S" and first[73:].strip().isdigit():
            return "iges"
        # Cadence Allegro databases open with a little-endian format word 0x..1N...., then a
        # fixed run of section counts.
        if len(head) >= 16 and head[3] == 0 and head[2] in _ALLEGRO_MAJOR and head[4:16] == _ALLEGRO_TAIL:
            return "allegro"
        if len(_OBJ_VERTEX.findall(head)) >= 3 and b"\x00" not in head and _OBJ_FACE.search(payload):
            return "obj"
    return found


def _zip_members(payload: bytes) -> List[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = [n for n in archive.namelist() if not n.endswith("/")]
    except (zipfile.BadZipFile, OSError):
        return []
    return [n for n in names if not n.startswith("__MACOSX/") and not Path(n).name.startswith("._")]


def suffix(filename: str) -> str:
    return PurePosixPath(filename.lower()).suffix


def category(payload: bytes, filename: str) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(category, detected_format)``; category is ``cad``, ``docs`` or None."""
    found = identify(payload)
    ext = suffix(filename)
    if found in CAD_FORMATS:
        return "cad", found
    if found == "zip":
        if ext in CONTAINER_SUFFIXES:
            return "cad", CONTAINER_SUFFIXES[ext]
        members = _zip_members(payload)
        if not members:
            return None, found
        if any(m.lower().endswith(CAD_MEMBER_SUFFIXES) for m in members):
            return "cad", "zip"
        return "docs", "zip"
    head = payload[:65536]
    text = head.lstrip(b"\xef\xbb\xbf").lstrip()
    if ext == ".kicad_pro" and found == "json":
        return "cad", "kicad"
    if ext == ".kicad_dru" and text.startswith(b"(version"):
        return "cad", "kicad"
    # KiCad 5 projects are INI text whose first line, a date, can read as CSV.
    if ext == ".pro" and found in (None, "csv") and (
            b"[pcbnew]" in head or b"[eeschema]" in head or b"last_client=kicad" in head):
        return "cad", "kicad"
    # Altium projects are INI text opening with [Design], which reads as JSON.
    if ext in (".prjpcb", ".prjpcbstructure") and found in (None, "json") and text.startswith(b"[Design]"):
        return "cad", "altium"
    if ext == ".opj" and found is None and text.startswith(b"(ExpressProject"):
        return "cad", "orcad"
    # PADS Logic binary schematics: a 0x00FE marker, then a fixed section table.
    if ext == ".sch" and found is None and head[:2] == b"\x00\xfe" \
            and head[32:44] == b"\x01\x00\x00\x00L\x02\x00\x00\x15\x00\x00\x00":
        return "cad", "pads"
    if found in DOC_FORMATS and not (found == "csv" and ext in NATIVE_SUFFIXES):
        return "docs", found
    if found == "ole":
        if ext in ALTIUM_SUFFIXES:
            return "cad", "altium"
        if ext in NATIVE_SUFFIXES:
            return "cad", NATIVE_SUFFIXES[ext]
        if ext in OFFICE_SUFFIXES:
            return "docs", "office"
        return None, found
    return None, found


def unpack(payload: bytes) -> Tuple[List[Tuple[str, bytes, str]], List[Tuple[str, str]]]:
    """Split an archive into its CAD members and the members left out, with the reason."""
    kept: List[Tuple[str, bytes, str]] = []
    left: List[Tuple[str, str]] = []
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for name in _zip_members(payload):
            data = archive.read(name)
            kind, detected = category(data, name)
            if detected == "zip":
                left.append((name, "archive inside the archive"))
            elif kind == "cad":
                kept.append((name, data, str(detected)))
            else:
                left.append((name, describe(detected, name)))
    return kept, left


def describe(detected: Optional[str], name: str) -> str:
    ext = suffix(name)
    if detected == "pdf":
        return "PDF document"
    if ext in OFFICE_SUFFIXES or detected == "office":
        return "spreadsheet or document"
    if detected == "csv" or ext in (".csv", ".txt", ".rep", ".lst", ".ipc", ".md"):
        return "text, report or list"
    return f"not CAD ({detected or 'unrecognised'})"


def git_blob_id(payload: bytes) -> str:
    """The SHA-1 git stores a file under, so a file can be proven identical to a commit's."""
    return hashlib.sha1(b"blob %d\0" % len(payload) + payload).hexdigest()


def lfs_pointer_oid(data: bytes) -> Optional[str]:
    """Return the sha256 oid when ``data`` is a Git LFS pointer file, else None."""
    if not data.startswith(LFS_POINTER_PREFIX) or len(data) > 1024:
        return None
    match = re.search(rb"^oid sha256:([0-9a-f]{64})$", data, re.MULTILINE)
    return match.group(1).decode("ascii") if match else None


# --------------------------------------------------------------------------------------
# paths
# --------------------------------------------------------------------------------------

_SAFE = re.compile(r"[^A-Za-z0-9._+-]+")


def safe_component(text: str) -> str:
    cleaned = _SAFE.sub("-", text).strip("-.")
    return cleaned or "file"


def board_dir(board_id: str) -> Path:
    vendor, _, board = board_id.partition(":")
    if not board:
        vendor, board = "unknown", board_id
    return MIRROR_DIR / safe_component(vendor.lower()) / safe_component(board.lower())


def file_name(url: str, detected: Optional[str]) -> str:
    """The URL's own file name, made filesystem-safe, with an extension when it has none."""
    path = urllib.parse.unquote(urllib.parse.urlsplit(url).path)
    name = safe_component(Path(path).name) if Path(path).name else "file"
    if not Path(name).suffix and detected in EXTENSION_FOR_FORMAT:
        name += EXTENSION_FOR_FORMAT[detected]
    return name


def relative_parts(source: Source, detected: Optional[str], member: Optional[str]) -> List[str]:
    """Where a file sits under the board's ``cad/``: the repository's own layout when known.

    A member of an archive goes in a folder named after the archive.
    """
    if source.repo_path:
        parts = [safe_component(p) for p in PurePosixPath(source.repo_path).parts]
    else:
        parts = [file_name(source.url, "zip" if member is not None else detected)]
    if member is not None:
        folder = parts[-1][:-4] if parts[-1].lower().endswith(".zip") else parts[-1]
        inner = [safe_component(p) for p in PurePosixPath(member).parts]
        # "X.zip" usually holds "X/...": one folder named X, not two.
        if len(inner) > 1 and inner[0] == folder:
            inner = inner[1:]
        parts = parts[:-1] + [folder] + inner
    return parts


@dataclass
class Item:
    """One file to write: a whole source, or one CAD member of an archive source."""

    source: Source
    payload: bytes
    detected: Optional[str]
    member: Optional[str] = None
    archive_sha256: Optional[str] = None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()

    @property
    def key(self) -> Tuple[str, str, Optional[str]]:
        return self.source.board_id, self.source.url, self.member


def plan_paths(items: Sequence[Item]) -> Dict[Tuple[str, str, Optional[str]], Path]:
    """Assign each item a path, adding a digest prefix only when names collide or run long."""
    paths: Dict[Tuple[str, str, Optional[str]], Path] = {}
    taken: Dict[Path, str] = {}
    for item in items:
        base = board_dir(item.source.board_id) / "cad"
        parts = relative_parts(item.source, item.detected, item.member)
        candidate = base.joinpath(*parts)
        if len(candidate.as_posix()) > MAX_PATH_LENGTH:
            candidate = base / f"{item.sha256[:8]}-{parts[-1]}"
        if candidate in taken and taken[candidate] != item.sha256:
            candidate = candidate.parent / f"{item.sha256[:8]}-{candidate.name}"
        taken[candidate] = item.sha256
        paths[item.key] = candidate
    return paths


# --------------------------------------------------------------------------------------
# manifest and attribution
# --------------------------------------------------------------------------------------

def manifest_entry(item: Item, path: Path) -> Dict[str, Any]:
    source = item.source
    licences = source.record.get("licenses") or {}
    entry: Dict[str, Any] = {
        "board_id": source.board_id,
        "manufacturer": source.record.get("manufacturer"),
        "board": source.record.get("board"),
        "path": path.as_posix(),
        "category": "cad",
        "detected_format": item.detected,
        "formats": sorted(source.formats),
        "url": source.url,
        "sha256": item.sha256,
        "size_bytes": len(item.payload),
        "retrieved_at": source.captured_at,
        "licence": licences.get("cad_license") or licences.get("hardware_license"),
        "licence_url": licences.get("license_url"),
    }
    if source.repo_path:
        entry["repository_path"] = source.repo_path
    if source.blob:
        entry["git_blob"] = source.blob
    if item.member is not None:
        entry["archive"] = {"member": item.member, "sha256": item.archive_sha256}
    return entry


def render_attribution(record: Dict[str, Any], entries: Sequence[Dict[str, Any]],
                       notice: Optional[Dict[str, Any]] = None,
                       left_out: Sequence[Tuple[str, str, str]] = (),
                       uncovered: Sequence[str] = ()) -> str:
    licences = record.get("licenses") or {}
    licence = licences.get("cad_license") or licences.get("hardware_license") or "see source"
    licence_url = licences.get("license_url")
    lines = [
        f"# {record.get('board')}",
        "",
        f"Design files published by **{record.get('manufacturer')}**, copied here without",
        "modification from the official sources listed below: the files named in",
        "[`tools/devboard_cad/records/`](../../../../tools/devboard_cad/records/), each matching",
        "its recorded SHA-256, and every other CAD file in the manufacturer's repository at",
        "the commit the record pins, each matching its git blob ID there. Archives are",
        "unpacked and only their CAD members kept.",
        "",
        f"- Board ID: `{record.get('board_id')}`",
        f"- Part number: {record.get('part_number')}",
        f"- Licence: {licence}" + (f" ({licence_url})" if licence_url else ""),
        f"- Attribution: {record.get('manufacturer')}",
        "- Changes: none",
        f"- CAD files: {len(entries)}",
        "",
        "| File | Format | Source | SHA-256 |",
        "|---|---|---|---|",
    ]
    for entry in sorted(entries, key=lambda e: e["path"]):
        rel = Path(entry["path"]).relative_to(board_dir(record["board_id"])).as_posix()
        link = urllib.parse.quote(rel)
        origin = f"[source]({entry['url']})"
        if entry.get("archive"):
            origin += f", member `{entry['archive']['member']}`"
        lines.append(f"| [`{rel}`]({link}) | {entry['detected_format'] or ''} | {origin} "
                     f"| `{entry['sha256'][:16]}…` |")
    if left_out:
        lines += ["", NOT_COPIED_HEADING, "",
                  "Members of the archives above that are not CAD, left out of the mirror:", ""]
        for archive, member, reason in sorted(left_out):
            lines.append(f"- `{member}` in {file_name(archive, 'zip')}: {reason}")
    if uncovered:
        lines += ["", NOT_COVERED_HEADING, "",
                  f"CAD files of this design outside its licence, {licence}, left out:", ""]
        lines += [f"- {item}" for item in sorted(uncovered)]
    if notice:
        why = (f"{notice['licence']} requires its text to accompany every copy."
               if notice["licence"] in NOTICE_LICENCES else
               "The licence notice and copyright lines, as the licensor wrote them.")
        lines += [
            "",
            LICENCE_TEXT_HEADING,
            "",
            f"{why} Verbatim from",
            f"[the manufacturer's licence]({notice['source']}), SHA-256 `{notice['sha256'][:16]}…`:",
            "",
            "````text",
            notice["text"].replace("\r\n", "\n").rstrip("\n"),
            "````",
        ]
    lines.append("")
    return "\n".join(lines)


def load_notices(root: Path) -> Dict[str, Dict[str, Any]]:
    path = root / NOTICES_PATH
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("notices", {})


def load_index(root: Path) -> Dict[str, Any]:
    path = root / INDEX_PATH
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("boards", {})


def needs_notice(entry: Dict[str, Any]) -> bool:
    return entry.get("licence") in NOTICE_LICENCES


def load_manifest(root: Path) -> Dict[str, Any]:
    path = root / MANIFEST_PATH
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"tool": TOOL_ID, "entries": []}


def write_manifest(root: Path, entries: Sequence[Dict[str, Any]],
                   excluded: Sequence[Dict[str, Any]] = ()) -> None:
    path = root / MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "tool": TOOL_ID,
        "policy": ("CAD files only, and only from boards whose records set "
                   "licenses.redistribution_allowed to true: the record's verified files and "
                   "every other CAD file at the repository commit it pins. Archives are "
                   "unpacked to their CAD members."),
        "entries": sorted(entries, key=lambda e: (e["board_id"], e["path"])),
        "excluded": sorted(excluded, key=lambda e: (e["board_id"], e["url"])),
    }
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# index
# --------------------------------------------------------------------------------------

def build_index(records: Iterable[Dict[str, Any]], gh_api: Callable[[str], Any],
                indexed_at: str) -> Tuple[Dict[str, Any], List[str]]:
    """List every CAD file at the commit each redistributable record's files are pinned to.

    A record whose files are not all on one commit of one repository is left out, and said.
    """
    boards: Dict[str, Any] = {}
    notes: List[str] = []
    for record in records:
        if not redistributable(record):
            continue
        pins = set()
        for entry in (record.get("files") or {}).values():
            if isinstance(entry, dict) and entry.get("available") is True and entry.get("url"):
                pinned = pinned_path(entry["url"])
                pins.add(pinned[:3] if pinned else None)
        pins.discard(None)
        if len(pins) != 1:
            if pins:
                notes.append(f"{record['board_id']}: files span {len(pins)} commits; not indexed")
            continue
        owner, repo, commit = next(iter(pins))  # type: ignore[misc]
        folder_match = TREE_FOLDER.search((record.get("sources") or {}).get("official_cad_repository") or "")
        folder = urllib.parse.unquote(folder_match.group(1)) + "/" if folder_match else ""
        tree = gh_api(f"repos/{owner}/{repo}/git/trees/{commit}?recursive=1")
        if tree.get("truncated"):
            notes.append(f"{record['board_id']}: the tree listing of {owner}/{repo} is truncated")
        blobs = [e for e in tree.get("tree", []) if e.get("type") == "blob"
                 and e["path"].startswith(folder)]
        gerber_dirs = {PurePosixPath(e["path"]).parent for e in blobs
                       if e["path"].lower().endswith(GERBER_SUFFIXES)}
        files = [{"path": e["path"], "blob": e["sha"], "size": e.get("size")} for e in blobs
                 if e["path"].lower().endswith(DESIGN_SUFFIXES)
                 or (e["path"].lower().endswith(".txt")
                     and PurePosixPath(e["path"]).parent in gerber_dirs
                     and not PROSE_NAME.search(PurePosixPath(e["path"]).name))]
        boards[str(record["board_id"])] = {
            "repository": f"{owner}/{repo}", "commit": commit, "indexed_at": indexed_at,
            "files": sorted(files, key=lambda f: f["path"]),
        }
    return boards, notes


def write_index(root: Path, boards: Dict[str, Any]) -> None:
    body = {
        "tool": TOOL_ID,
        "purpose": ("Every CAD file in each mirrored board's repository at the commit its "
                    "record pins, with the git blob ID mirror.py verifies the bytes against."),
        "boards": dict(sorted(boards.items())),
    }
    (root / INDEX_PATH).write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n",
                                   encoding="utf-8")


# --------------------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------------------

@dataclass
class Report:
    written: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)
    refused: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.refused


def lfs_url(source: Source) -> Optional[str]:
    pinned = pinned_path(source.url)
    if not pinned:
        return None
    owner, repo, commit, path = pinned
    return f"https://media.githubusercontent.com/media/{owner}/{repo}/{commit}/{urllib.parse.quote(path)}"


def verified_payload(source: Source, payload: bytes, fetcher: Any) -> Tuple[Optional[bytes], Optional[str]]:
    """The source's real bytes and None, or None and why they cannot be trusted."""
    if source.blob is not None:
        blob = git_blob_id(payload)
        if blob != source.blob:
            return None, f"git blob {blob[:12]} != {source.blob[:12]} at the pinned commit"
        oid = lfs_pointer_oid(payload)
        if oid is not None:
            url = lfs_url(source)
            result = fetcher.get(url) if url else None
            if result is not None and result.status in (404, 410):
                return None, f"{LFS_MISSING} (HTTP {result.status})"
            if result is None or result.payload is None:
                return None, f"Git LFS object not retrieved ({result.error if result else 'no URL'})"
            payload = result.payload
            if hashlib.sha256(payload).hexdigest() != oid:
                return None, "Git LFS object does not match its pointer"
    if source.sha256 is not None:
        digest = hashlib.sha256(payload).hexdigest()
        if digest != source.sha256:
            return None, f"sha256 {digest[:16]} != recorded {source.sha256[:16]}"
    return payload, None


def build(root: Path, records: Sequence[Dict[str, Any]], fetcher: Any,
          vendors: Sequence[str] = (), index: Optional[Dict[str, Any]] = None,
          log: Optional[Callable[[str], None]] = None) -> Report:
    """Write the selected boards' CAD files, their attribution and the manifest.

    Boards are written one at a time, so memory holds one board's files, not a vendor's.
    """
    report = Report()
    wanted = {v.lower() for v in vendors}
    index = load_index(root) if index is None else index
    sources = [s for s in select(records, index)
               if not wanted or s.board_id.partition(":")[0].lower() in wanted]
    manifest = load_manifest(root)
    held = {(e["board_id"], e["url"]): root / e["path"] for e in manifest.get("entries", [])
            if not e.get("archive")}
    entries = [e for e in manifest.get("entries", [])
               if wanted and e["board_id"].partition(":")[0].lower() not in wanted]
    excluded = [e for e in manifest.get("excluded", [])
                if wanted and e["board_id"].partition(":")[0].lower() not in wanted]
    notices = load_notices(root)
    by_board: Dict[str, List[Source]] = {}
    for source in sources:
        by_board.setdefault(source.board_id, []).append(source)
    for board_id, board_sources in by_board.items():
        board_entries = build_board(root, board_sources, fetcher, held, notices, report, excluded)
        entries.extend(board_entries)
        if log:
            log(f"{board_id}: {len(board_entries)} CAD files")
    write_manifest(root, entries, excluded)
    report.removed = prune(root, entries)
    return report


def build_board(root: Path, sources: Sequence[Source], fetcher: Any,
                held: Dict[Tuple[str, str], Path], notices: Dict[str, Dict[str, Any]],
                report: Report, excluded: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fetch, verify, unpack and write one board's sources; return its manifest entries."""
    record = sources[0].record
    board_id = sources[0].board_id
    items: List[Item] = []
    left_out: List[Tuple[str, str, str]] = []
    uncovered: List[str] = []

    def exclude(source: Source, reason: str) -> None:
        # A file the record names is claimed to be CAD, so it failing is an error. A file the
        # index picked by its name alone may simply not be CAD: it is left out and listed.
        if source.sha256 is not None:
            report.refused.append(f"{board_id}: {source.url}: {reason}")
            return
        excluded.append({"board_id": board_id, "url": source.url,
                         "repository_path": source.repo_path, "git_blob": source.blob,
                         "reason": reason})
        left_out.append((source.url, source.repo_path or source.url, reason))

    def leave_uncovered(source: Source) -> None:
        # Verified and CAD, but outside the licence: listed, and recorded so check knows it.
        excluded.append({"board_id": board_id, "url": source.url,
                         "repository_path": source.repo_path, "git_blob": source.blob,
                         "sha256": source.sha256, "reason": NOT_COVERED_REASON})

    for source in sources:
        payload: Optional[bytes] = None
        kept = held.get((board_id, source.url))
        if kept is not None and kept.is_file():
            data = kept.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest == source.sha256 or (source.sha256 is None and source.blob is not None
                                           and git_blob_id(data) == source.blob):
                payload = data
        if payload is None:
            result = fetcher.get(source.url)
            if result.payload is None:
                report.refused.append(f"{board_id}: {source.url}: not retrieved ({result.error})")
                continue
            payload, problem = verified_payload(source, result.payload, fetcher)
            if payload is None:
                if problem and problem.startswith(LFS_MISSING):
                    exclude(source, str(problem))
                else:
                    report.refused.append(f"{board_id}: {source.url}: {problem}")
                continue
        name = source.repo_path or file_name(source.url, identify(payload))
        kind, detected = category(payload, name)
        if detected == "zip":
            members, skipped = unpack(payload)
            if not members:
                exclude(source, "archive holds no CAD files")
                continue
            archive_sha = hashlib.sha256(payload).hexdigest()
            inside = [m for m in members if covered(record, m[0], m[2])]
            uncovered.extend(f"`{member}` in {file_name(source.url, 'zip')}"
                             for member, _, member_format in members
                             if not covered(record, member, member_format))
            left_out.extend((source.url, member, reason) for member, reason in skipped)
            if not inside:
                leave_uncovered(source)
                continue
            for member, data, member_format in inside:
                if len(data) >= GITHUB_FILE_LIMIT:
                    left_out.append((source.url, member, "larger than GitHub's 100 MiB file limit"))
                    continue
                items.append(Item(source, data, member_format, member, archive_sha))
            continue
        if kind != "cad":
            exclude(source, f"not a CAD file ({describe(detected, name)})")
            continue
        if not covered(record, name, detected):
            uncovered.append(f"`{source.repo_path or source.url}`")
            leave_uncovered(source)
            continue
        items.append(Item(source, payload, detected))

    paths = plan_paths(items)
    board_entries: List[Dict[str, Any]] = []
    for item in items:
        path = paths[item.key]
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == item.sha256:
            report.unchanged.append(path.as_posix())
        else:
            target.write_bytes(item.payload)
            report.written.append(path.as_posix())
        board_entries.append(manifest_entry(item, path))
    if not board_entries:
        return board_entries
    notice = notices.get(board_id)
    if needs_notice(board_entries[0]) and notice is None:
        report.refused.append(f"{board_id}: {board_entries[0]['licence']} needs its licence "
                              f"text; run read_licenses.py --notices")
    attribution = root / board_dir(board_id) / ATTRIBUTION_NAME
    attribution.write_text(render_attribution(record, board_entries, notice, left_out, uncovered),
                           encoding="utf-8")
    return board_entries


def prune(root: Path, entries: Sequence[Dict[str, Any]]) -> List[str]:
    """Delete whatever the manifest no longer names: stray files and boards left empty."""
    removed: List[str] = []
    base = root / MIRROR_DIR
    if not base.is_dir():
        return removed
    keep = {(root / e["path"]).resolve() for e in entries}
    boards = {board_dir(e["board_id"]) for e in entries}
    for path in sorted(base.rglob("*"), reverse=True):
        parts = path.relative_to(base).parts
        if path.is_file() and len(parts) < 3:
            path.unlink()
            removed.append(path.relative_to(root).as_posix())
            continue
        if len(parts) < 3:
            continue
        board = MIRROR_DIR / parts[0] / parts[1]
        if path.is_file() and (path.resolve() not in keep) and (board not in boards or len(parts) >= 4):
            path.unlink()
            removed.append(path.relative_to(root).as_posix())
    for path in sorted(base.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    return removed


# --------------------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------------------

def check(root: Path, records: Sequence[Dict[str, Any]],
          index: Optional[Dict[str, Any]] = None) -> List[str]:
    """Problems with the mirror, or an empty list when it is complete and intact.

    Works on a checkout without LFS content: a pointer file's oid is the SHA-256 of the
    object it stands for, so integrity is provable from the pointer alone.
    """
    problems: List[str] = []
    manifest = load_manifest(root)
    entries = manifest.get("entries", [])
    notices = load_notices(root)
    index = load_index(root) if index is None else index
    by_url: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for entry in entries:
        by_url.setdefault((entry["board_id"], entry["url"]), []).append(entry)
    allowed = {r["board_id"] for r in records if redistributable(r)}
    by_id = {r["board_id"]: r for r in records}
    excluded = {(e["board_id"], e["url"]): e for e in manifest.get("excluded", [])}

    for source in select(records, index):
        mirrored = by_url.get((source.board_id, source.url))
        left = excluded.get((source.board_id, source.url))
        if not mirrored and left is not None and (
                (source.sha256 is None and left.get("git_blob") == source.blob)
                or (left.get("reason") == NOT_COVERED_REASON and source.sha256 is not None
                    and left.get("sha256") == source.sha256)):
            continue
        if not mirrored:
            problems.append(f"missing: {source.board_id} {source.url}")
            continue
        for entry in mirrored:
            archive = entry.get("archive")
            if archive and source.sha256 and archive.get("sha256") != source.sha256:
                problems.append(f"archive digest differs from the record: {source.board_id} {entry['path']}")
            if not archive and source.sha256 and entry["sha256"] != source.sha256:
                problems.append(f"digest differs from the record: {source.board_id} {entry['path']}")
            if source.blob and entry.get("git_blob") != source.blob:
                problems.append(f"git blob differs from the index: {source.board_id} {entry['path']}")

    for entry in entries:
        label = f"{entry['board_id']} {entry['path']}"
        if entry["board_id"] not in allowed:
            problems.append(f"not redistributable: {label}")
        elif not covered(by_id[entry["board_id"]], (entry.get("archive") or {}).get("member") or entry["path"],
                         entry.get("detected_format")):
            problems.append(f"{NOT_COVERED_REASON}: {label}")
        path = root / entry["path"]
        if not path.is_file():
            problems.append(f"file absent: {label}")
            continue
        data = path.read_bytes()
        oid = lfs_pointer_oid(data)
        digest = oid or hashlib.sha256(data).hexdigest()
        if digest != entry["sha256"]:
            problems.append(f"digest mismatch: {label}")
        if oid is None and category(data, path.name)[0] != entry["category"]:
            problems.append(f"content is not {entry['category']}: {label}")
        attribution = root / board_dir(entry["board_id"]) / ATTRIBUTION_NAME
        if not attribution.is_file():
            problems.append(f"no {ATTRIBUTION_NAME}: {entry['board_id']}")
        elif needs_notice(entry):
            notice = notices.get(entry["board_id"])
            body = attribution.read_text(encoding="utf-8")
            if notice is None or LICENCE_TEXT_HEADING not in body \
                    or notice["text"].replace("\r\n", "\n").strip() not in body:
                problems.append(f"no {entry['licence']} licence text in {ATTRIBUTION_NAME}: {entry['board_id']}")
            elif hashlib.sha256(notice["text"].encode("utf-8")).hexdigest() != notice["sha256"]:
                problems.append(f"licence text does not match its digest: {entry['board_id']}")

    mirrored_paths = {(root / e["path"]).resolve() for e in entries}
    boards = {board_dir(e["board_id"]) for e in entries}
    base = root / MIRROR_DIR
    if base.is_dir():
        for path in base.rglob("*"):
            parts = path.relative_to(base).parts
            if not path.is_file():
                continue
            if len(parts) < 3:
                problems.append(f"stray file in mirror: {path.relative_to(root).as_posix()}")
                continue
            board = MIRROR_DIR / parts[0] / parts[1]
            if board not in boards:
                problems.append(f"board without CAD files in mirror: {path.relative_to(root).as_posix()}")
            elif len(parts) >= 4 and path.resolve() not in mirrored_paths:
                problems.append(f"untracked file in mirror: {path.relative_to(root).as_posix()}")
            elif len(parts) == 3 and path.name != ATTRIBUTION_NAME:
                problems.append(f"stray file in mirror: {path.relative_to(root).as_posix()}")
    return sorted(set(problems))


# --------------------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------------------

def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_records(root: Path) -> List[Dict[str, Any]]:
    directory = root / "tools" / "devboard_cad" / "records"
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.json"))]


def summarise(root: Path) -> str:
    # Two sources can yield one identical file (the same member of two backup archives),
    # so files are counted by path.
    entries = list({e["path"]: e for e in load_manifest(root).get("entries", [])}.values())
    boards = {e["board_id"] for e in entries}
    by_kind: Dict[str, int] = {}
    for entry in entries:
        by_kind[entry["category"]] = by_kind.get(entry["category"], 0) + 1
    size = sum(e["size_bytes"] for e in entries)
    kinds = ", ".join(f"{k} {v}" for k, v in sorted(by_kind.items()))
    return f"{len(entries)} files for {len(boards)} boards ({kinds}), {size / 1e6:.1f} MB"


def cmd_index(args: argparse.Namespace) -> int:
    from datetime import datetime, timezone

    from devboard_cad.harvest_github import _gh_api

    import time

    def gh_api(path: str) -> Any:
        # One listing per repository over hundreds of repositories: retry a transient failure.
        for attempt in range(3):
            try:
                return _gh_api(path)
            except Exception:  # noqa: BLE001 - re-raised on the last attempt
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))
        raise AssertionError("unreachable")

    root = repo_root()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    boards, notes = build_index(load_records(root), gh_api, now)
    write_index(root, boards)
    for line in notes:
        print(f"NOTE {line}", file=sys.stderr)
    total = sum(len(b["files"]) for b in boards.values())
    print(f"indexed {total} CAD files in {len(boards)} repositories")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    root = repo_root()
    fetcher = Fetcher(cache_dir=args.cache, offline=args.offline)
    report = build(root, load_records(root), fetcher, args.vendor,
                   log=lambda line: print(line, flush=True))
    for line in report.refused:
        print(f"REFUSED {line}", file=sys.stderr)
    print(f"written {len(report.written)}, unchanged {len(report.unchanged)}, "
          f"removed {len(report.removed)}, refused {len(report.refused)}")
    print(summarise(root))
    return 0 if report.ok else 1


def cmd_check(args: argparse.Namespace) -> int:
    root = repo_root()
    problems = check(root, load_records(root))
    for line in problems:
        print(line, file=sys.stderr)
    print(f"{summarise(root)}; {len(problems)} problem(s)")
    return 1 if problems else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    i = sub.add_parser("index", help="list every CAD file at each mirrored board's pinned repository commit")
    i.set_defaults(func=cmd_index)
    b = sub.add_parser("build", help="copy the CAD files of redistributable boards into boards/cad/")
    b.add_argument("--vendor", action="append", default=[],
                   help="only this vendor prefix of board_id (repeatable), e.g. --vendor sparkfun")
    b.add_argument("--offline", action="store_true", help="use only the verifier's local cache")
    b.add_argument("--cache", type=Path, default=None, help="cache directory (default: the verifier's)")
    b.set_defaults(func=cmd_build)
    c = sub.add_parser("check", help="fail unless the mirror is complete and every digest matches")
    c.set_defaults(func=cmd_check)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
