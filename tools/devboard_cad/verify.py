"""Verify development-board CAD availability claims against official sources (issue #28).

Availability in this database is tri-state, and each state has to be earned:

* ``true``  - the bytes were retrieved and their *content* matched the declared format.
* ``false`` - the source answered definitively that nothing is there (404/410).
* ``null``  - unknown. Every other outcome lands here, including blocks, timeouts and
  landing pages, because absence of evidence is not evidence of absence.

Two properties of real vendor endpoints drive the design and are not negotiable:

1. **HEAD is unusable.** ``datasheets.raspberrypi.com`` answers HEAD for the Pico STEP
   archive with ``content-type: text/html`` and ``content-length: 0``, while a GET of the
   same URL returns a 266,009-byte ZIP. HEAD produces false negatives, so this tool only
   ever issues GET.
2. **A 200 is not a file.** Vendors serve consent walls, login pages and SPA shells with
   status 200. Only the leading bytes say what was really delivered, so every response is
   content-sniffed and a payload that turns out to be HTML never satisfies a CAD claim.

The tool records a digest of what it fetched; it never adds vendor files to the repository.
Most board CAD is not redistributable, which is precisely why ``licenses`` is a field.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import OrderedDict
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

TOOL_ID = "devboard-cad-verifier@0.1.0"
USER_AGENT = (
    "Mozilla/5.0 (compatible; eCAD-devboard-cad-verifier/0.1; "
    "+https://github.com/embeddedos-org/eCAD-Hardware-Products)"
)
MAX_BYTES = 256 * 1024 * 1024
DEFAULT_TIMEOUT = 30.0
# urlopen's timeout is per socket operation, so a server that trickles bytes
# never trips it. A whole-transfer deadline is what actually bounds a run.
DEFAULT_DEADLINE = 120.0
DEFAULT_MIN_INTERVAL = 2.0

# --------------------------------------------------------------------------------------
# content sniffing
# --------------------------------------------------------------------------------------

_MAGIC: Tuple[Tuple[bytes, str], ...] = (
    (b"%PDF-", "pdf"),
    (b"PK\x03\x04", "zip"),
    (b"PK\x05\x06", "zip"),
    (b"PK\x07\x08", "zip"),
    (b"7z\xbc\xaf\x27\x1c", "7z"),
    (b"Rar!\x1a\x07", "rar"),
    (b"\x1f\x8b", "gzip"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "ole"),  # legacy Altium / xls / doc
    (b"ISO-10303-21", "step"),
    (b"AutoCAD Binary DXF", "dxf"),
    (b"EESchema", "kicad"),
    (b"(kicad_pcb", "kicad"),
    (b"(kicad_sch", "kicad"),
    (b"(kicad_symbol_lib", "kicad"),
    (b"(footprint", "kicad"),
    (b"(module", "kicad"),
)

_HTML_RE = re.compile(rb"<\s*(!doctype\s+html|html|head|body|script|meta)\b", re.IGNORECASE)


def detect_format(head: bytes) -> Optional[str]:
    """Identify a payload from its leading bytes. Returns None when nothing matches."""
    stripped = head.lstrip(b"\xef\xbb\xbf").lstrip()
    for magic, name in _MAGIC:
        if stripped.startswith(magic) or head.startswith(magic):
            return name
    if stripped.startswith(b"solid ") or stripped.startswith(b"solid\n"):
        return "stl"
    if stripped.startswith(b"<?xml") or stripped.startswith(b"<eagle"):
        return "eagle" if b"<eagle" in stripped[:4096] else "xml"
    # ASCII DXF. Group code 0 / SECTION / 2 / <section name>. It is not enough to anchor
    # at byte 0: group code 999 is a legal comment and writers put one there (Raspberry
    # Pi's mechanical DXFs open with "999\ndxfrw 0.6.3"), so the pattern is searched for
    # within the header and pinned to a real section name to stay specific.
    if re.search(rb"(?:^|[\r\n])\s*0\s*[\r\n]+\s*SECTION\s*[\r\n]+\s*2\s*[\r\n]+"
                 rb"\s*(HEADER|CLASSES|TABLES|BLOCKS|ENTITIES|OBJECTS)\b",
                 stripped[:2048]):
        return "dxf"
    # Excellon NC drill: the format's own header command, e.g. "M48\nINCH\nT01C.006".
    if re.match(rb"^M48\s*[\r\n]", stripped):
        return "excellon"
    # Gerber RS-274X. Both KiCad and Eagle open with a G04 comment; the extended-format
    # directives are the unambiguous marker when a writer omits the comment.
    if re.match(rb"^(G04[ *]|G75\*|%(FS|MO|AD|LP|IN))", stripped):
        return "gerber"
    if _HTML_RE.search(stripped[:4096]):
        return "html"
    if stripped.startswith(b"{") or stripped.startswith(b"["):
        return "json"
    if _looks_delimited(stripped):
        return "csv"
    return None


def _looks_delimited(head: bytes) -> bool:
    """Last-resort check for a delimited text table, as BOMs and centroid files are.

    Deliberately conservative: it must decode as text, contain a line break, and its first
    line must hold at least two delimiters. Anything binary or free-prose fails, so this
    never quietly upgrades an unrecognised payload into a satisfied claim.
    """
    sample = head[:4096]
    if b"\x00" in sample:
        return False
    try:
        text = sample.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if not text.strip() or "\n" not in text:
        return False
    first = text.splitlines()[0]
    return any(first.count(d) >= 2 for d in (",", ";", "\t"))


def is_binary_stl(payload: bytes) -> bool:
    """Binary STL has an 80-byte header, a uint32 triangle count, then 50 bytes each."""
    if len(payload) < 84:
        return False
    count = int.from_bytes(payload[80:84], "little")
    return len(payload) == 84 + count * 50 and count > 0


_STEP_HEADER_RE = re.compile(r"HEADER;(.*?)ENDSEC;", re.DOTALL | re.IGNORECASE)
_STEP_FILE_NAME_RE = re.compile(r"FILE_NAME\s*\((.*?)\)\s*;", re.DOTALL | re.IGNORECASE)
_STEP_SCHEMA_RE = re.compile(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']*)'", re.DOTALL | re.IGNORECASE)
_STEP_DESC_RE = re.compile(r"FILE_DESCRIPTION\s*\(\s*\(\s*'([^']*)'", re.DOTALL | re.IGNORECASE)


def parse_step_header(payload: bytes) -> Dict[str, Optional[str]]:
    """Read the ISO-10303-21 HEADER block. Pure text parsing; no CAD kernel required.

    The header names the authoring tool, the timestamp and the AP schema, and its
    ``FILE_NAME`` field frequently carries the board revision, which lets a record's
    ``verified_revision`` be corroborated by the file itself rather than by a human.
    """
    text = payload[:65536].decode("latin-1", errors="replace")
    out: Dict[str, Optional[str]] = {
        "step_schema": None, "authoring_tool": None,
        "internal_name": None, "timestamp": None,
    }
    block = _STEP_HEADER_RE.search(text)
    if not block:
        return out
    body = block.group(1)
    schema = _STEP_SCHEMA_RE.search(body)
    if schema:
        out["step_schema"] = schema.group(1).strip() or None
    desc = _STEP_DESC_RE.search(body)
    name = _STEP_FILE_NAME_RE.search(body)
    if name:
        fields = re.findall(r"'([^']*)'", name.group(1))
        if fields:
            out["internal_name"] = fields[0].strip() or None
        if len(fields) > 1:
            out["timestamp"] = fields[1].strip() or None
        tools = [f.strip() for f in fields[2:] if f.strip()]
        if tools:
            out["authoring_tool"] = " / ".join(tools[-2:]) if len(tools) > 1 else tools[-1]
    if out["step_schema"] is None and desc:
        out["step_schema"] = desc.group(1).strip() or None
    return out


# Layer names that assert "this is the board edge". Layer "0" is deliberately
# absent: it is the DXF default layer, where sheet borders and title blocks
# also land, so treating it as the outline reports the paper size as the board.
OUTLINE_LAYERS = frozenset({
    "OUTLINE", "BOARD_OUTLINE", "BOARDOUTLINE", "BOARD-OUTLINE",
    "EDGE.CUTS", "EDGE_CUTS", "EDGECUTS", "EDGE",
    "DIMENSION_OUTLINE", "PCB_OUTLINE", "CONTOUR", "MECHANICAL", "MECH",
})


def parse_dxf_geometry(payload: bytes) -> Dict[str, Any]:
    """Parse ASCII DXF payload, validating the ENTITIES section and overall file structure.

    Extracts outline dimensions, dimension annotations, and geometry extents.
    Raises ValueError if the DXF structure is truncated, malformed, or missing ENTITIES.
    """
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("latin-1", errors="replace")

    text = text.lstrip("\ufeff")
    lines = [line.strip() for line in text.splitlines()]
    if len(lines) < 2:
        raise ValueError("DXF payload is empty or too short")

    # Fast verification that file ends with 0 / EOF
    has_eof = False
    for i in range(len(lines) - 1, max(-1, len(lines) - 30), -1):
        if lines[i] == "EOF" and i > 0 and lines[i - 1] == "0":
            has_eof = True
            break
    if not has_eof:
        raise ValueError("DXF file is truncated: missing 0 / EOF marker")

    pairs: List[Tuple[int, str]] = []
    i = 0
    while i < len(lines) - 1:
        code_str = lines[i]
        val_str = lines[i + 1]
        try:
            code = int(code_str)
        except ValueError:
            raise ValueError(f"invalid DXF group code at line {i + 1}: {code_str!r}")
        pairs.append((code, val_str))
        i += 2
        if code == 0 and val_str == "EOF":
            break

    # Locate sections: ENTITIES and optionally BLOCKS
    entities_start = None
    entities_end = None
    in_section = False
    current_sec = None
    for idx, (code, val) in enumerate(pairs):
        if code == 0 and val == "SECTION":
            in_section = True
        elif in_section and code == 2:
            current_sec = val
            if val == "ENTITIES":
                entities_start = idx + 1
            in_section = False
        elif code == 0 and val == "ENDSEC":
            if current_sec == "ENTITIES":
                entities_end = idx
                break
            current_sec = None

    if entities_start is None:
        raise ValueError("DXF file missing ENTITIES section")
    if entities_end is None:
        raise ValueError("DXF file truncated: ENTITIES section missing ENDSEC")

    dimensions: set[float] = set()
    outline_points: List[Tuple[float, float]] = []
    zero_layer_points: List[Tuple[float, float]] = []
    all_points: List[Tuple[float, float]] = []
    unit: Optional[str] = None

    # Check for unit in header variables
    for idx, (code, val) in enumerate(pairs[:entities_start]):
        if code == 9 and val == "$INSUNITS" and idx + 1 < len(pairs):
            ins_code = pairs[idx + 1][1]
            if ins_code == "4":
                unit = "mm"
            elif ins_code == "1":
                unit = "in"

    # Scan ENTITIES
    k = entities_start
    has_geometry = False
    while k < entities_end:
        code, val = pairs[k]
        if code == 0:
            etype = val
            fields: Dict[int, List[str]] = {}
            k += 1
            while k < entities_end and pairs[k][0] != 0:
                c, v = pairs[k]
                fields.setdefault(c, []).append(v)
                k += 1

            layer = fields.get(8, ["0"])[0]

            if etype == "DIMENSION":
                has_geometry = True
                for m in fields.get(42, []):
                    try:
                        dimensions.add(round(float(m), 2))
                    except ValueError:
                        pass
                for t in fields.get(1, []):
                    clean = re.sub(r"\\[A-Za-z0-9]+;", "", t).strip()
                    m = re.search(r"[-+]?\d*\.?\d+", clean)
                    if m:
                        try:
                            dimensions.add(round(float(m.group(0)), 2))
                        except ValueError:
                            pass
            elif etype in ("TEXT", "MTEXT"):
                for t in fields.get(1, []):
                    if "unit:" in t.lower():
                        u_m = re.search(r"unit:\s*([a-zA-Z]+)", t, re.IGNORECASE)
                        if u_m:
                            unit = u_m.group(1).lower()
                    clean = re.sub(r"\\[A-Za-z0-9]+;", "", t).strip()
                    m = re.search(r"^[-+]?\d*\.?\d+$", clean)
                    if m:
                        try:
                            dimensions.add(round(float(m.group(0)), 2))
                        except ValueError:
                            pass
            elif etype in ("LWPOLYLINE", "LINE", "ARC", "CIRCLE", "POLYLINE", "VERTEX"):
                has_geometry = True
                xs = [float(x) for x in fields.get(10, []) if re.match(r"^[-+]?\d*\.?\d+", x)]
                ys = [float(y) for y in fields.get(20, []) if re.match(r"^[-+]?\d*\.?\d+", y)]
                if etype == "LINE":
                    xs += [float(x) for x in fields.get(11, []) if re.match(r"^[-+]?\d*\.?\d+", x)]
                    ys += [float(y) for y in fields.get(21, []) if re.match(r"^[-+]?\d*\.?\d+", y)]
                for x, y in zip(xs, ys):
                    all_points.append((x, y))
                    if layer.upper() in OUTLINE_LAYERS:
                        outline_points.append((x, y))
                    elif layer == "0":
                        zero_layer_points.append((x, y))
        else:
            k += 1

    if not has_geometry and not all_points:
        raise ValueError("DXF ENTITIES section contains no valid geometry entities")

    # Scan BLOCKS for anonymous dimension blocks (*D...) with MTEXT dimensions
    in_blocks = False
    for idx, (code, val) in enumerate(pairs):
        if code == 0 and val == "SECTION" and idx + 1 < len(pairs) and pairs[idx + 1] == (2, "BLOCKS"):
            in_blocks = True
        elif in_blocks and code == 0 and val == "ENDSEC":
            in_blocks = False
        elif in_blocks and code == 1:
            clean = re.sub(r"\\[A-Za-z0-9]+;", "", val).strip()
            if re.match(r"^[-+]?\d*\.?\d+$", clean):
                try:
                    dimensions.add(round(float(clean), 2))
                except ValueError:
                    pass

    def _span(points: List[Tuple[float, float]]) -> Optional[Dict[str, Any]]:
        if not points:
            return None
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)
        return {
            "min_x": round(min_x, 2), "min_y": round(min_y, 2),
            "max_x": round(max_x, 2), "max_y": round(max_y, 2),
            "width": round(max_x - min_x, 2), "height": round(max_y - min_y, 2),
        }

    def _corroborated(span: Optional[Dict[str, Any]]) -> bool:
        """The file's own dimension annotations state both figures."""
        return bool(span) and span["width"] in dimensions and span["height"] in dimensions

    # The extents of whatever was measured. With an outline layer these are the
    # board; without one they are every entity in the file, which in a
    # mechanical drawing includes the sheet border and the title block.
    outline_span = _span(outline_points)
    zero_span = _span(zero_layer_points)
    all_span = _span(all_points)
    measured = outline_span or all_span
    extents_of = "outline_layer" if outline_points else "all_entities"

    # Only call a span the board outline when the file itself says so. A board
    # size guessed from drawing extents is wrong often enough to be useless:
    # one vendor's silkscreen drawing yields its A3 sheet, 420 x 294 mm.
    # Layer "0" is the DXF default layer, where some vendors put the board edge
    # and others put the sheet border, so it counts only when the dimension
    # annotations corroborate it.
    if outline_span:
        outline_source, chosen = "outline_layer", outline_span
    elif _corroborated(zero_span):
        outline_source, chosen = "layer_0_corroborated", zero_span
    elif _corroborated(all_span):
        outline_source, chosen = "dimension_annotations", all_span
    else:
        outline_source, chosen = "none", None

    extents = None
    if measured:
        extents = {k: measured[k] for k in ("min_x", "min_y", "max_x", "max_y")}

    outline_dim = None
    if chosen:
        outline_dim = {"width": chosen["width"], "height": chosen["height"],
                       "unit": unit or "mm"}

    return {
        "outline_dimensions": outline_dim,
        "outline_source": outline_source,
        "dimension_annotations": sorted(list(dimensions)),
        "extents": extents,
        "extents_of": extents_of,
    }


def parse_dxf_revision(payload: bytes) -> Optional[str]:
    """Scan DXF for explicit revision information.

    Checks group 999 comments, header variables ($PROJECTNAME, $REV), and text annotations.
    Returns None when the DXF genuinely carries no machine-verifiable revision.
    """
    text = payload[:65536].decode("latin-1", errors="replace")
    for match in re.finditer(r"(?:^|[\r\n])\s*999\s*[\r\n]+([^\r\n]+)", text):
        val = match.group(1).strip()
        rev_m = re.search(r"\b(?:rev(?:ision)?|v)\s*[:#.-]?\s*([A-Za-z0-9_.-]+)", val, re.IGNORECASE)
        if rev_m:
            return rev_m.group(1).strip()
    for var in ("$PROJECTNAME", "$REV", "$REVISION"):
        m = re.search(rf"(?:^|[\r\n])\s*9\s*[\r\n]+\s*{re.escape(var)}\s*[\r\n]+\s*1\s*[\r\n]+([^\r\n]+)", text)
        if m:
            val = m.group(1).strip()
            if val:
                return val
    return None


def check_geometry_contradiction(parsed: Dict[str, Any], expected: Dict[str, Any]) -> Optional[str]:
    """Return an error string if parsed geometry contradicts expected geometry from record."""
    exp_outline = expected.get("outline_dimensions")
    if exp_outline and parsed.get("outline_dimensions"):
        exp_w = exp_outline.get("width")
        exp_h = exp_outline.get("height")
        got_w = parsed["outline_dimensions"].get("width")
        got_h = parsed["outline_dimensions"].get("height")
        if exp_w is not None and exp_h is not None and got_w is not None and got_h is not None:
            direct_match = abs(got_w - exp_w) <= 0.05 and abs(got_h - exp_h) <= 0.05
            rotated_match = abs(got_w - exp_h) <= 0.05 and abs(got_h - exp_w) <= 0.05
            if not (direct_match or rotated_match):
                return (f"outline dimensions ({got_w} x {got_h}) contradict record "
                        f"({exp_w} x {exp_h})")

    exp_annotations = expected.get("dimension_annotations")
    if exp_annotations:
        got_annotations = parsed.get("dimension_annotations") or []
        for ann in exp_annotations:
            if not any(abs(ann - g) <= 0.05 for g in got_annotations):
                return f"expected dimension annotation {ann} not found in annotations {got_annotations}"

    return None


# --------------------------------------------------------------------------------------
# what content is acceptable for each declared format
# --------------------------------------------------------------------------------------

_ARCHIVES = {"zip", "7z", "rar", "gzip"}

ACCEPTED: Dict[str, Tuple[str, ...]] = {
    # Issue #28 section 8 lists "Schematic PDF" and "Native schematic" as separate items;
    # the v1 schema has a single `schematic` field, so both kinds satisfy it.
    "schematic": ("pdf", "kicad", "eagle", "xml", "ole") + tuple(_ARCHIVES),
    "pcb_source": ("kicad", "eagle", "ole", "xml") + tuple(_ARCHIVES),
    "gerbers": ("gerber", "excellon") + tuple(_ARCHIVES),
    "bom": ("pdf", "csv", "xlsx", "ole", "json") + tuple(_ARCHIVES),
    "pick_and_place": ("csv", "pdf", "ole") + tuple(_ARCHIVES),
    "step": ("step",) + tuple(_ARCHIVES),
    "iges": ("iges",) + tuple(_ARCHIVES),
    "dxf": ("dxf",) + tuple(_ARCHIVES),
    "stl": ("stl",) + tuple(_ARCHIVES),
    "kicad": ("kicad",) + tuple(_ARCHIVES),
    "eagle": ("eagle", "xml", "ole") + tuple(_ARCHIVES),
    "altium": ("ole",) + tuple(_ARCHIVES),
    "orcad": ("ole",) + tuple(_ARCHIVES),
    "allegro": ("ole",) + tuple(_ARCHIVES),
    "fusion360": tuple(_ARCHIVES),
    "solidworks": ("ole",) + tuple(_ARCHIVES),
    "mechanical": ("pdf", "dxf", "step") + tuple(_ARCHIVES),
    "nc_drill": ("excellon", "csv") + tuple(_ARCHIVES),
    "ipc2581": ("xml",) + tuple(_ARCHIVES),
    "odb": tuple(_ARCHIVES),
    "symbol_library": ("kicad", "eagle", "xml") + tuple(_ARCHIVES),
    "footprint_library": ("kicad", "eagle", "xml") + tuple(_ARCHIVES),
    "datasheet": ("pdf",) + tuple(_ARCHIVES),
    "user_manual": ("pdf",) + tuple(_ARCHIVES),
    "hardware_design_guide": ("pdf",) + tuple(_ARCHIVES),
    "assembly_drawing": ("pdf", "dxf") + tuple(_ARCHIVES),
    "pinout": ("pdf",) + tuple(_ARCHIVES),
    "reference_design": ("pdf",) + tuple(_ARCHIVES),
}

# Members inside an archive that satisfy a format claim, by suffix.
ARCHIVE_SUFFIXES: Dict[str, Tuple[str, ...]] = {
    "step": (".step", ".stp"),
    "iges": (".iges", ".igs"),
    "dxf": (".dxf",),
    "stl": (".stl",),
    "kicad": (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".sch", ".kicad_mod", ".kicad_sym"),
    "eagle": (".brd", ".sch", ".lbr"),
    "altium": (".pcbdoc", ".schdoc", ".prjpcb"),
    "orcad": (".dsn", ".opj"),
    "allegro": (".brd", ".dra"),
    "gerbers": (".gbr", ".ger", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".drl", ".txt", ".gm1", ".gko"),
    "pcb_source": (".kicad_pcb", ".brd", ".pcbdoc", ".pcb"),
    "schematic": (".pdf", ".kicad_sch", ".sch", ".schdoc"),
    "bom": (".csv", ".xlsx", ".xls", ".bom", ".txt", ".pdf"),
    "pick_and_place": (".csv", ".pos", ".xy", ".txt"),
    "nc_drill": (".drl", ".txt", ".nc", ".xln"),
    "ipc2581": (".xml", ".cvg"),
    "odb": (".tgz", ".tar.gz"),
    "solidworks": (".sldprt", ".sldasm"),
    "fusion360": (".f3d", ".f3z"),
    "mechanical": (".pdf", ".dxf", ".step", ".stp"),
    "symbol_library": (".kicad_sym", ".lib", ".lbr"),
    "footprint_library": (".kicad_mod", ".pretty", ".lbr"),
}


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------

class FetchResult:
    """Outcome of a single GET. ``payload`` is None when nothing was retrieved."""

    def __init__(self, url: str, status: Optional[int], payload: Optional[bytes],
                 media_type: Optional[str], final_url: Optional[str],
                 error: Optional[str], from_cache: bool = False) -> None:
        self.url = url
        self.status = status
        self.payload = payload
        self.media_type = media_type
        self.final_url = final_url
        self.error = error
        self.from_cache = from_cache

    @property
    def sha256(self) -> Optional[str]:
        return hashlib.sha256(self.payload).hexdigest() if self.payload is not None else None

    @property
    def size(self) -> Optional[int]:
        return len(self.payload) if self.payload is not None else None


def default_cache_dir() -> Path:
    env = os.environ.get("DEVBOARD_CAD_CACHE")
    if env:
        return Path(env).expanduser()
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "devboard-cad"


class Fetcher:
    """GET with a per-host rate limit and an on-disk cache keyed by URL.

    The cache lives outside the repository by default so that vendor payloads are never
    staged for commit; only their digests end up in a record.
    """

    def __init__(self, cache_dir: Optional[Path] = None, timeout: float = DEFAULT_TIMEOUT,
                 min_interval: float = DEFAULT_MIN_INTERVAL, offline: bool = False,
                 refresh: bool = False, deadline: float = DEFAULT_DEADLINE) -> None:
        self.cache_dir = cache_dir or default_cache_dir()
        self.timeout = timeout
        self.deadline = deadline
        self.min_interval = min_interval
        self.offline = offline
        self.refresh = refresh
        self._last_hit: Dict[str, float] = {}
        self._lock = threading.Lock()

    def _paths(self, url: str) -> Tuple[Path, Path]:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.bin", self.cache_dir / f"{key}.json"

    def _throttle(self, url: str) -> None:
        """Reserve the next slot for this host, then wait for it outside the lock."""
        if self.min_interval <= 0:
            return
        host = urllib.parse.urlsplit(url).netloc
        with self._lock:
            now = time.monotonic()
            nxt = max(now, self._last_hit.get(host, 0.0) + self.min_interval)
            self._last_hit[host] = nxt
        wait = nxt - time.monotonic()
        if wait > 0:
            time.sleep(wait)

    def get(self, url: str) -> FetchResult:
        blob, meta = self._paths(url)
        if meta.exists() and not self.refresh:
            info = json.loads(meta.read_text(encoding="utf-8"))
            cached: Optional[bytes] = blob.read_bytes() if blob.exists() else None
            usable = cached is not None or info.get("status") in (404, 410)
            # A cached failure is not a result. Timeouts, bot challenges and transport
            # errors are transient by nature, so serving one back would freeze a record at
            # 'unknown' for every future run. Only a payload, or a definitive 404/410, is
            # worth replaying; anything else is retried unless we are explicitly offline.
            if usable or self.offline:
                return FetchResult(url, info.get("status"), cached, info.get("media_type"),
                                   info.get("final_url"), info.get("error"), from_cache=True)
        if self.offline:
            return FetchResult(url, None, None, None, None, "offline: not in cache")

        self._throttle(url)
        request = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en",
        })
        status: Optional[int] = None
        payload: Optional[bytes] = None
        media_type: Optional[str] = None
        final_url: Optional[str] = None
        error: Optional[str] = None
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status = response.status
                media_type = (response.headers.get("Content-Type") or "").split(";")[0].strip() or None
                final_url = response.geturl()
                buffer = BytesIO()
                started = time.monotonic()
                while True:
                    chunk = response.read(262144)
                    if not chunk:
                        break
                    buffer.write(chunk)
                    if buffer.tell() > MAX_BYTES:
                        error = f"payload exceeds {MAX_BYTES} bytes; refusing"
                        break
                    elapsed = time.monotonic() - started
                    if elapsed > self.deadline:
                        error = (f"transfer exceeded {self.deadline:.0f}s "
                                 f"({buffer.tell()} bytes read); treating as unknown")
                        break
                payload = None if error else buffer.getvalue()
        except urllib.error.HTTPError as exc:
            status = exc.code
            media_type = (exc.headers.get("Content-Type") or "").split(";")[0].strip() or None
            final_url = url
            error = f"HTTP {exc.code}"
        except urllib.error.URLError as exc:
            error = f"url error: {exc.reason}"
        except socket.timeout:
            error = "timeout"
        except (OSError, ValueError) as exc:  # pragma: no cover - environment dependent
            error = f"{type(exc).__name__}: {exc}"

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if payload is not None:
            blob.write_bytes(payload)
        meta.write_text(json.dumps({
            "url": url, "status": status, "media_type": media_type,
            "final_url": final_url, "error": error,
            "cached_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }, indent=2) + "\n", encoding="utf-8")
        return FetchResult(url, status, payload, media_type, final_url, error)


# --------------------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------------------

class Verdict:
    def __init__(self, available: Optional[bool], evidence: Optional[Dict[str, Any]],
                 reason: str, verified_revision: Optional[str] = None,
                 verified_geometry: Optional[Dict[str, Any]] = None) -> None:
        self.available = available
        self.evidence = evidence
        self.reason = reason
        # Set only when the retrieved file itself names the revision the record claims,
        # or an explicit format verdict (e.g. 'revision not machine-verifiable for dxf').
        self.verified_revision = verified_revision
        self.verified_geometry = verified_geometry


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _archive_member(payload: bytes, format_name: str) -> Optional[str]:
    """Return the first archive member that satisfies ``format_name``, if any."""
    suffixes = ARCHIVE_SUFFIXES.get(format_name)
    if not suffixes:
        return None
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            names = [n for n in archive.namelist() if not n.endswith("/")]
    except (zipfile.BadZipFile, OSError):
        return None
    # __MACOSX/._* are resource forks, not content.
    names = [n for n in names if not n.startswith("__MACOSX/") and not Path(n).name.startswith("._")]
    for name in names:
        if name.lower().endswith(tuple(s.lower() for s in suffixes)):
            return name
    return None


def classify(format_name: str, result: FetchResult,
             absent_on_404: bool = False,
             claimed_revision: Optional[str] = None,
             expected_geometry: Optional[Dict[str, Any]] = None) -> Verdict:
    """Turn one fetch into a tri-state availability determination plus its evidence.

    ``absent_on_404`` must only be set when the URL came from the vendor's own index or
    documentation. A 404 on a *guessed* URL says the guess was wrong, not that the vendor
    publishes nothing, and recording ``false`` for it would put a false claim in the
    database. Unknown is the correct answer for a dead candidate URL.
    """
    common: Dict[str, Any] = {
        "captured_at": _now(),
        "producer_tool_id": TOOL_ID,
        "http_status": result.status,
    }
    if result.final_url and result.final_url != result.url:
        common["source_url"] = result.final_url

    if result.status in (404, 410):
        if not absent_on_404:
            return Verdict(None, None,
                           f"HTTP {result.status} on a candidate URL: the URL is wrong or "
                           f"moved; this is not evidence the vendor publishes nothing")
        evidence = dict(common)
        evidence["verification_method"] = "http_get_absent"
        evidence["sha256"] = None
        return Verdict(False, evidence,
                       f"official source reports the file is gone (HTTP {result.status})")

    if result.payload is None:
        return Verdict(None, None, result.error or "no payload retrieved")

    detected = detect_format(result.payload[:8192])
    if detected is None and is_binary_stl(result.payload):
        detected = "stl"

    if detected == "html":
        return Verdict(None, None, "server returned an HTML page, not a file "
                                   "(consent wall, login or landing page)")

    accepted = ACCEPTED.get(format_name)
    if accepted is None:
        return Verdict(None, None, f"no acceptance rule for format '{format_name}'")

    if detected not in accepted:
        return Verdict(None, None,
                       f"content is '{detected or 'unrecognised'}', which does not satisfy "
                       f"a '{format_name}' claim")

    evidence = dict(common)
    evidence["sha256"] = result.sha256
    evidence["size_bytes"] = result.size
    evidence["media_type"] = result.media_type
    evidence["detected_format"] = detected
    evidence["verification_method"] = "http_get_magic"

    dxf_payload: Optional[bytes] = None
    if detected in _ARCHIVES:
        member = _archive_member(result.payload, format_name)
        if member is None:
            return Verdict(None, None,
                           f"archive retrieved but contains no member satisfying "
                           f"'{format_name}'")
        evidence["contained_member"] = member
        evidence["verification_method"] = "http_get_archive_member"
        inner = _step_payload_from_archive(result.payload, member)
        if inner is not None:
            header = parse_step_header(inner)
            if header["step_schema"]:
                evidence["verification_method"] = "http_get_step_header"
                evidence["detected_format"] = f"step:{header['step_schema']}"
        inner_dxf = _dxf_payload_from_archive(result.payload, member)
        if inner_dxf is not None:
            dxf_payload = inner_dxf
    elif detected == "step":
        header = parse_step_header(result.payload)
        if header["step_schema"]:
            evidence["verification_method"] = "http_get_step_header"
            evidence["detected_format"] = f"step:{header['step_schema']}"
    elif detected == "dxf":
        dxf_payload = result.payload

    verified_geometry: Optional[Dict[str, Any]] = None
    if dxf_payload is not None:
        try:
            verified_geometry = parse_dxf_geometry(dxf_payload)
        except ValueError as exc:
            return Verdict(None, None, f"DXF geometry parsing failed: {exc}")

        if expected_geometry:
            contradiction = check_geometry_contradiction(verified_geometry, expected_geometry)
            if contradiction:
                return Verdict(None, None, f"DXF geometry contradicts record: {contradiction}")

        evidence["verification_method"] = "http_get_dxf_geometry"

    member = evidence.get("contained_member")
    probe = _text_probe(result.payload, member)
    revision = None
    if claimed_revision and revision_corroborated(probe, member, claimed_revision):
        revision = claimed_revision
        suffix = f"; revision '{revision}' corroborated by the file"
    elif dxf_payload is not None:
        revision = "revision not machine-verifiable for dxf"
        suffix = "; revision not machine-verifiable for dxf"
    else:
        suffix = ""

    return Verdict(True, evidence,
                   f"retrieved and content-verified as '{detected}'{suffix}",
                   verified_revision=revision,
                   verified_geometry=verified_geometry)


def _text_probe(payload: bytes, member: Optional[str]) -> bytes:
    """The bytes worth scanning for a revision string: the STEP header when there is one."""
    if member:
        inner = _step_payload_from_archive(payload, member)
        if inner is not None:
            return inner
        inner_dxf = _dxf_payload_from_archive(payload, member)
        if inner_dxf is not None:
            return inner_dxf
    return payload[:65536]


def _step_payload_from_archive(payload: bytes, member: str) -> Optional[bytes]:
    if not member.lower().endswith((".step", ".stp")):
        return None
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            with archive.open(member) as handle:
                return handle.read(65536)
    except (zipfile.BadZipFile, KeyError, OSError):
        return None


def _dxf_payload_from_archive(payload: bytes, member: str) -> Optional[bytes]:
    if not member.lower().endswith(".dxf"):
        return None
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            return archive.read(member)
    except (zipfile.BadZipFile, KeyError, OSError):
        return None


def revision_corroborated(payload: bytes, member: Optional[str], revision: str) -> bool:
    """True when the file itself mentions the revision the record claims.

    The Pico archive ships ``Pico-R3.step``; a record claiming revision ``Pico-R3`` is then
    corroborated by the vendor's own naming rather than by an editor's assertion.
    """
    if not revision or revision.lower() == "unverified":
        return False
    needle = revision.lower().replace(" ", "").replace("_", "-")
    haystacks: List[str] = []
    if member:
        haystacks.append(member.lower())
    header = parse_step_header(payload)
    for value in header.values():
        if value:
            haystacks.append(value.lower())
    dxf_rev = parse_dxf_revision(payload)
    if dxf_rev:
        haystacks.append(dxf_rev.lower())
    return any(needle in h.replace(" ", "").replace("_", "-") for h in haystacks)


# --------------------------------------------------------------------------------------
# record handling
# --------------------------------------------------------------------------------------

def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def records_dir(root: Path) -> Path:
    return root / "tools" / "devboard_cad" / "records"


def load_record(path: Path) -> "OrderedDict[str, Any]":
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=OrderedDict)


def write_record(path: Path, record: Any) -> None:
    """Write with LF endings and a trailing newline, matching the rest of the repository."""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")


# An identity field is resolved when it holds a real value, or when the manufacturer has
# been checked and demonstrably publishes none. "unverified" means nobody has looked yet;
# "not-stated" and "not-applicable" are findings. Collapsing the two would make an
# unfinished record indistinguishable from a complete one about a board with no revision.
IDENTITY_GAP = {"", "unverified", "unknown", "tbd", "n/a"}
IDENTITY_RESOLVED_SENTINELS = {"not-stated", "not-applicable"}


def identity_is_pinned(record: Dict[str, Any]) -> bool:
    for field in ("part_number", "mcu_soc", "revision"):
        value = str(record.get(field, "")).strip().lower()
        if value in IDENTITY_GAP:
            return False
    return True


def derive_status(record: Dict[str, Any]) -> str:
    """Derive record_status from the data so it cannot drift out of sync by hand."""
    entries = list(record.get("files", {}).values())
    if not entries:
        return "incomplete"
    known = [e for e in entries if e.get("available") is not None]
    if not known:
        return "incomplete"
    if len(known) == len(entries) and identity_is_pinned(record):
        return "verified"
    return "partial"


def verify_record(record: Dict[str, Any], fetcher: Fetcher,
                  only: Optional[Sequence[str]] = None,
                  verbose: bool = True,
                  absent_on_404: bool = False,
                  jobs: int = 1) -> List[Tuple[str, Verdict]]:
    targets = [(name, entry["url"]) for name, entry in record.get("files", {}).items()
               if entry.get("url") and not (only and name not in only)]

    def check(target: Tuple[str, str]) -> Tuple[str, Verdict, bool]:
        name, url = target
        result = fetcher.get(url)
        entry = record.get("files", {}).get(name, {})
        expected_geom = entry.get("verified_geometry") or record.get("verified_geometry")
        return (name,
                classify(name, result, absent_on_404=absent_on_404,
                         claimed_revision=record.get("revision"),
                         expected_geometry=expected_geom),
                result.from_cache)

    if jobs > 1 and len(targets) > 1:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            checked = list(pool.map(check, targets))
    else:
        checked = [check(t) for t in targets]

    outcomes: List[Tuple[str, Verdict]] = []
    for name, verdict, from_cache in checked:
        outcomes.append((name, verdict))
        if verbose:
            state = {True: "true ", False: "false", None: "null "}[verdict.available]
            print(f"    {name:22} -> {state}  {verdict.reason}"
                  f"{' (cached)' if from_cache else ''}")
    return outcomes


def apply_outcomes(record: Dict[str, Any], outcomes: Iterable[Tuple[str, Verdict]]) -> int:
    changed = 0
    for name, verdict in outcomes:
        entry = record["files"][name]
        def snapshot() -> Tuple[Any, Any, Any, Any]:
            return (entry.get("available"),
                    (entry.get("evidence") or {}).get("sha256"),
                    entry.get("verified_revision"),
                    entry.get("verified_geometry"))

        before = snapshot()
        # Preserve original capture timestamp if evidence digest and method did not change
        if (entry.get("available") == verdict.available
                and entry.get("evidence")
                and verdict.evidence
                and entry["evidence"].get("sha256") == verdict.evidence.get("sha256")
                and entry["evidence"].get("verification_method") == verdict.evidence.get("verification_method")):
            verdict.evidence["captured_at"] = entry["evidence"]["captured_at"]

        entry["available"] = verdict.available
        entry["evidence"] = verdict.evidence
        if verdict.verified_revision:
            entry["verified_revision"] = verdict.verified_revision
        if verdict.verified_geometry:
            entry["verified_geometry"] = verdict.verified_geometry
            record["verified_geometry"] = verdict.verified_geometry
        if snapshot() != before:
            changed += 1
    record["record_status"] = derive_status(record)
    return changed


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def _record_paths(root: Path, selectors: Sequence[str]) -> List[Path]:
    directory = records_dir(root)
    if not selectors:
        return sorted(directory.glob("*.json"))
    paths: List[Path] = []
    for selector in selectors:
        candidate = Path(selector)
        if candidate.is_file():
            paths.append(candidate)
            continue
        matches = sorted(directory.glob(f"*{selector}*.json"))
        if not matches:
            print(f"error: no record matches '{selector}'", file=sys.stderr)
        paths.extend(matches)
    return paths


def cmd_verify(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    fetcher = Fetcher(cache_dir=Path(args.cache).expanduser() if args.cache else None,
                      timeout=args.timeout, min_interval=args.min_interval,
                      offline=args.offline, refresh=args.refresh,
                      deadline=args.deadline)
    paths = _record_paths(root, args.records)
    if not paths:
        print("error: no records selected", file=sys.stderr)
        return 2
    total_changed = 0
    for path in paths:
        record = load_record(path)
        if not args.quiet:
            print(f"{record.get('board_id', path.stem)}  ({path.name})")
        outcomes = verify_record(record, fetcher, only=args.format or None,
                                 absent_on_404=args.absent_on_404,
                                 verbose=not args.quiet, jobs=args.jobs)
        if not outcomes and not args.quiet:
            print("    no URLs to check")
        if args.apply and outcomes:
            changed = apply_outcomes(record, outcomes)
            total_changed += changed
            if changed:
                write_record(path, record)
            if not args.quiet:
                print(f"    updated {changed} entr{'y' if changed == 1 else 'ies'}; "
                      f"record_status={record['record_status']}" if changed
                      else "    no change")
            elif changed:
                print(f"{record['board_id']:46} {changed:2} updated  "
                      f"[{record['record_status']}]", flush=True)
    if args.apply:
        print(f"\n{total_changed} entr{'y' if total_changed == 1 else 'ies'} updated")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify.py", description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(repo_root()))
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="fetch and content-check the URLs in records")
    verify.add_argument("records", nargs="*",
                        help="record paths or substrings; default: every record")
    verify.add_argument("--format", action="append",
                        help="restrict to this format (repeatable)")
    verify.add_argument("--apply", action="store_true",
                        help="write the determinations and evidence back into the records")
    verify.add_argument("--offline", action="store_true",
                        help="use only the cache; never touch the network")
    verify.add_argument("--absent-on-404", action="store_true",
                        help="record available=false on 404/410. Only correct when the URL "
                             "was taken from the vendor's own index, not guessed.")
    verify.add_argument("--refresh", action="store_true",
                        help="ignore cached responses and refetch")
    verify.add_argument("--cache", default=None, help="cache directory")
    verify.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help="per-socket-operation timeout")
    verify.add_argument("--deadline", type=float, default=DEFAULT_DEADLINE,
                        help="whole-transfer deadline; a slow trickle is not a file")
    verify.add_argument("--min-interval", type=float, default=DEFAULT_MIN_INTERVAL,
                        help="minimum seconds between requests to one host")
    verify.add_argument("--jobs", type=int, default=1,
                        help="files checked concurrently; the per-host interval still holds")
    verify.add_argument("--quiet", action="store_true",
                        help="one line per changed record instead of one per file")
    verify.set_defaults(func=cmd_verify)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
