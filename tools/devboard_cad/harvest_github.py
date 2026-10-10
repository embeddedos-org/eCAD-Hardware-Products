"""Derive board-record candidates from a manufacturer's official GitHub repository.

Issue #28 section 10 ranks the manufacturer's own GitHub repository third in the source
hierarchy, above distributor and community sources. For the vendors that publish hardware
that way - Adafruit, SparkFun, Seeed, Espressif, Arduino, BeagleBoard - a repository tree
is something no product page provides: an **exhaustive** list of what the vendor ships.

That exhaustiveness is what makes ``available: false`` recordable at all. A 404 on a guessed
URL proves only that the guess was wrong. A pinned repository tree that contains no ``.step``
file is positive evidence that the vendor publishes no STEP model there, so this tool emits
``false`` with ``verification_method: official_index_absent`` and an ``index_ref`` naming the
exact commit consulted.

The tool only ever *proposes*. Every positive candidate is written with ``available: null``
and a raw URL pinned to the indexed commit; ``verify.py`` then downloads it, content-checks
it and decides. Nothing here asserts that a file is present.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from devboard_cad.verify import derive_status  # noqa: E402

TOOL_ID = "devboard-cad-github-harvester@0.1.0"
RAW = "https://raw.githubusercontent.com"

# A single file can satisfy several format claims: an Eagle .brd is both the native PCB
# source and the Eagle-format answer. Order matters only for picking a representative file.
SUFFIX_FORMATS: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...]], ...] = (
    ((".kicad_pcb",), ("pcb_source", "kicad")),
    ((".kicad_sch",), ("schematic", "kicad")),
    ((".kicad_sym",), ("symbol_library", "kicad")),
    ((".kicad_mod",), ("footprint_library", "kicad")),
    ((".kicad_pro",), ("kicad",)),
    ((".brd",), ("pcb_source", "eagle")),
    ((".sch",), ("schematic", "eagle")),
    ((".lbr",), ("symbol_library", "footprint_library", "eagle")),
    ((".pcbdoc",), ("pcb_source", "altium")),
    ((".schdoc",), ("schematic", "altium")),
    ((".prjpcb",), ("altium",)),
    ((".step", ".stp"), ("step",)),
    ((".iges", ".igs"), ("iges",)),
    ((".stl",), ("stl",)),
    ((".dxf",), ("dxf",)),
    ((".f3d", ".f3z"), ("fusion360",)),
    ((".sldprt", ".sldasm"), ("solidworks",)),
    ((".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gko", ".gm1", ".gbr", ".ger",
      ".gl2", ".gl3", ".gtp", ".gbp"), ("gerbers",)),
    ((".drl", ".xln", ".nc"), ("nc_drill",)),
)

# Filename hints, applied to PDFs and to ambiguous archives.
NAME_HINTS: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    (("pinout",), "pinout"),
    (("datasheet",), "datasheet"),
    (("schematic", "-sch", "_sch", " sch"), "schematic"),
    (("mechanical", "dimension", "drawing", "outline"), "mechanical"),
    (("assembly",), "assembly_drawing"),
    (("user manual", "user-manual", "usermanual"), "user_manual"),
    (("design guide", "hardware guide"), "hardware_design_guide"),
    (("reference design",), "reference_design"),
    (("gerber", "production", "fab"), "gerbers"),
    (("bom", "bill of material", "bill-of-material"), "bom"),
    (("pick", "place", "centroid", "cpl", "-pos", "_pos"), "pick_and_place"),
    (("step",), "step"),
)

# Formats this tool is competent to declare absent. It does not list every schema format,
# because a repository containing no user manual is weak evidence that none is published:
# manuals live on product pages. Only formats that live in hardware repositories qualify.
ABSENCE_CLAIMABLE = (
    "pcb_source", "schematic", "gerbers", "step", "dxf", "stl",
    "kicad", "eagle", "altium", "nc_drill", "bom", "pick_and_place",
    "mechanical",
)


class GitHubError(RuntimeError):
    """A GitHub API call did not return a result. A 404 is an ordinary outcome here."""


def _gh_api(path: str) -> Any:
    """Call the GitHub API through `gh` when available, else an authenticated urllib GET.

    When `gh` is present and answers, its answer is final. Falling through to urllib on a
    non-zero exit would turn every 404 -- a repository with no LICENSE file, say -- into an
    extra *unauthenticated* request against a 60/hour limit, which stalls any bulk run.
    """
    try:
        out = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=60)
        if out.returncode == 0:
            return json.loads(out.stdout)
        raise GitHubError(f"gh api {path}: {(out.stderr or '').strip()[:120]}")
    except FileNotFoundError:
        pass  # gh is not installed; fall back to urllib
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise GitHubError(f"gh api {path}: {exc}") from exc
    request = urllib.request.Request(
        f"https://api.github.com/{path.lstrip('/')}",
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": TOOL_ID})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def repo_index(repo: str, ref: Optional[str] = None) -> Tuple[str, List[str], Dict[str, Any]]:
    """Return (commit_sha, blob paths, repo metadata) for an immutable view of the repo."""
    meta = _gh_api(f"repos/{repo}")
    branch = ref or meta.get("default_branch") or "HEAD"
    commit = _gh_api(f"repos/{repo}/commits/{branch}")
    sha = commit["sha"]
    tree = _gh_api(f"repos/{repo}/git/trees/{sha}?recursive=1")
    if tree.get("truncated"):
        raise RuntimeError(
            f"{repo}: tree listing is truncated, so absence cannot be proven from it")
    paths = [item["path"] for item in tree.get("tree", []) if item.get("type") == "blob"]
    return sha, paths, meta


def classify_paths(paths: Sequence[str]) -> Dict[str, List[str]]:
    """Map each format name to the repository paths that satisfy it."""
    found: Dict[str, List[str]] = {}
    for path in paths:
        name = Path(path).name
        if name.startswith(".") or name.startswith("._") or path.startswith("__MACOSX/"):
            continue
        lower = path.lower()
        formats: List[str] = []
        for suffixes, names in SUFFIX_FORMATS:
            if lower.endswith(suffixes):
                formats.extend(names)
        if lower.endswith(".pdf"):
            formats.extend(fmt for hints, fmt in NAME_HINTS if any(h in lower for h in hints))
        if lower.endswith((".zip", ".7z")):
            formats.extend(fmt for hints, fmt in NAME_HINTS if any(h in lower for h in hints))
        if lower.endswith((".csv", ".xlsx", ".xls")):
            formats.extend(fmt for hints, fmt in NAME_HINTS
                           if any(h in lower for h in hints) and fmt in ("bom", "pick_and_place"))
        for fmt in dict.fromkeys(formats):
            found.setdefault(fmt, []).append(path)
    return found


def _raw_url(repo: str, sha: str, path: str) -> str:
    return f"{RAW}/{repo}/{sha}/{urllib.parse.quote(path)}"


# For the format-neutral slots the question is "is there a PCB source at all?", so the
# answer should be the file the most people can open. The vendor-specific slots (kicad,
# eagle, altium) still point at their own format, so nothing is hidden by this preference.
_NEUTRAL_SLOTS = {"pcb_source", "schematic"}
_FORMAT_PREFERENCE = (".kicad_pcb", ".kicad_sch", ".pdf", ".brd", ".sch", ".pcbdoc", ".schdoc")


def _pick(paths: Sequence[str], format_name: Optional[str] = None) -> str:
    """Choose one representative path.

    Vendors keep the current board at the root and superseded revisions in subdirectories
    or behind 'rev'/'original' in the filename, so shallow and short wins. For a
    format-neutral slot an interoperable format wins first.
    """
    prefer_open = format_name in _NEUTRAL_SLOTS

    def rank(path: str) -> Tuple[int, int, int, int, str]:
        low = path.lower()
        stale = 1 if any(w in low for w in
                         ("original", "old", "archive", "deprecated", "rev ")) else 0
        if prefer_open:
            openness = next((i for i, suffix in enumerate(_FORMAT_PREFERENCE)
                             if low.endswith(suffix)), len(_FORMAT_PREFERENCE))
        else:
            openness = 0
        return (stale, openness, path.count("/"), len(path), path)

    return sorted(paths, key=rank)[0]


# Vendors encode the board revision in the filename far more often than they state it in
# prose: "Pico-R3.step", "BeagleBone Black_PCB_RevD_250403.brd", "Feather RP2040 rev B.brd".
_REVISION_PATTERNS: Tuple[str, ...] = (
    r"[-_ ]rev(?:ision)?[-_ ]?([A-Z]\d?|\d+(?:\.\d+)?)(?![A-Za-z0-9])",
    r"[-_ ]([A-Z]?R\d+(?:\.\d+)?)(?![A-Za-z0-9])",
    r"(?<![A-Za-z0-9])v(\d+\.\d+)(?![A-Za-z0-9])",
)


def infer_revision(paths: Sequence[str]) -> Optional[str]:
    """Return the highest revision token the manufacturer put in its own filenames.

    Returns None when no file names one, which is a different fact from 'we did not look'
    and is recorded as such by the caller.
    """
    seen: List[str] = []
    for path in paths:
        stem = Path(path).name
        for pattern in _REVISION_PATTERNS:
            for match in re.finditer(pattern, stem, re.I):
                token = match.group(1).upper()
                if token and token not in seen:
                    seen.append(token)
    if not seen:
        return None

    def order(token: str) -> Tuple[int, float, str]:
        digits = re.findall(r"\d+(?:\.\d+)?", token)
        letters = re.findall(r"[A-Z]", token)
        return (ord(letters[0]) if letters else 0,
                float(digits[0]) if digits else 0.0,
                token)

    return sorted(seen, key=order)[-1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_files(repo: str, sha: str, found: Dict[str, List[str]],
                claim_absence: bool = True) -> "OrderedDict[str, Any]":
    """Candidates for what the index shows, proven absence for what it does not."""
    files: "OrderedDict[str, Any]" = OrderedDict()
    index_ref = f"{repo}@{sha}"
    for fmt in sorted(set(list(found) + list(ABSENCE_CLAIMABLE))):
        if fmt in found:
            files[fmt] = OrderedDict([
                ("available", None),  # verify.py decides; the index only proposes
                ("url", _raw_url(repo, sha, _pick(found[fmt], fmt))),
                ("verified_revision", None),
                ("evidence", None),
            ])
        elif claim_absence and fmt in ABSENCE_CLAIMABLE:
            files[fmt] = OrderedDict([
                ("available", False),
                ("url", None),
                ("verified_revision", None),
                ("evidence", OrderedDict([
                    ("sha256", None),
                    ("captured_at", _now()),
                    ("producer_tool_id", TOOL_ID),
                    ("verification_method", "official_index_absent"),
                    ("index_ref", index_ref),
                ])),
            ])
    for required in ("schematic", "pcb_source", "gerbers", "bom", "mechanical"):
        files.setdefault(required, OrderedDict([
            ("available", None), ("url", None),
            ("verified_revision", None), ("evidence", None)]))
    return files


def build_record(board_id: str, repo: str, sha: str, meta: Dict[str, Any],
                 found: Dict[str, List[str]], identity: Dict[str, Any],
                 claim_absence: bool = True, folder: Optional[str] = None) -> "OrderedDict[str, Any]":
    revision = identity.get("revision", "unverified")
    if str(revision).strip().lower() in ("", "unverified"):
        every_path = sorted({p for paths in found.values() for p in paths})
        # The tree is exhaustive, so "no file names a revision" is a finding about the
        # manufacturer's design-file distribution, not an unfilled gap in this record.
        revision = infer_revision(every_path) or "not-stated"
    # One repository can hold several boards, each in its own folder: the record is then
    # that folder at the commit, and its repository link says so.
    cad_repository = (f"{meta.get('html_url')}/tree/{sha}/{folder}" if folder
                      else meta.get("html_url"))
    where = f"{repo} pinned at {sha[:12]}" + (f", folder {folder}" if folder else "")
    spdx = (meta.get("license") or {}).get("spdx_id")
    license_name = spdx if spdx and spdx != "NOASSERTION" else "UNVERIFIED"
    record: "OrderedDict[str, Any]" = OrderedDict([
        ("$schema", "https://embeddedos.org/schemas/devboard-cad/v1/board-record.schema.json"),
        ("contract_version", "1.1.0"),
        ("board_id", board_id),
        ("manufacturer", identity["manufacturer"]),
        ("family", identity["family"]),
        ("board", identity["board"]),
        ("part_number", identity.get("part_number", "UNVERIFIED")),
        ("revision", revision),
        ("mcu_soc", identity.get("mcu_soc", "UNVERIFIED")),
        ("hardware_revision", identity.get("hardware_revision")),
        ("fpga", identity.get("fpga")),
        ("cpu_architecture", identity.get("cpu_architecture")),
        ("product_status", identity.get("product_status", "unknown")),
        ("files", build_files(repo, sha, found, claim_absence)),
        ("licenses", OrderedDict([
            ("hardware_license", license_name),
            ("cad_license", None), ("schematic_license", None), ("pcb_license", None),
            ("mechanical_cad_license", None),
            ("redistribution_allowed", None), ("modification_allowed", None),
            ("commercial_use_allowed", None), ("attribution_required", None),
            ("license_url", None),
        ])),
        ("sources", OrderedDict([
            ("source_tier", "manufacturer_official"),
            ("official_product_page", identity["official_product_page"]),
            ("official_cad_repository", cad_repository),
            ("official_github_repository", meta.get("html_url")),
            ("official_documentation", identity.get("official_documentation")),
            ("direct_cad_download", None),
            ("direct_schematic_download", None),
            ("direct_gerber_download", None),
        ])),
        ("record_status", "incomplete"),  # replaced below once files are known
        ("notes", f"File candidates harvested from the manufacturer's official repository "
                  f"{where}. Availability is decided by verify.py from "
                  f"retrieved bytes, never from this index. Licensing is left unverified "
                  f"until the vendor's terms have been read; a GitHub SPDX tag describes the "
                  f"repository, not necessarily the hardware."),
    ])
    record["record_status"] = derive_status(record)
    return record


def cmd_harvest(args: argparse.Namespace) -> int:
    identity = {
        "manufacturer": args.manufacturer, "family": args.family, "board": args.board,
        "part_number": args.part_number, "revision": args.revision, "mcu_soc": args.mcu,
        "cpu_architecture": args.arch, "product_status": args.status,
        "official_product_page": args.product_page,
        "official_documentation": args.documentation,
    }
    sha, paths, meta = repo_index(args.repo, args.ref)
    folder = args.path.strip("/") if args.path else None
    if folder:
        paths = [p for p in paths if p.startswith(folder + "/")]
    found = classify_paths(paths)
    record = build_record(args.board_id, args.repo, sha, meta, found, identity,
                          claim_absence=not args.no_absence, folder=folder)
    out = Path(args.out) if args.out else (
        Path(args.root) / "tools" / "devboard_cad" / "records" /
        (args.board_id.replace(":", "__") + ".json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    proposed = sum(1 for e in record["files"].values() if e["url"])
    absent = sum(1 for e in record["files"].values() if e["available"] is False)
    print(f"{args.board_id}: {len(paths)} blobs at {sha[:12]} -> "
          f"{proposed} candidate(s), {absent} proven absent -> {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harvest_github.py",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    sub = parser.add_subparsers(dest="command", required=True)
    h = sub.add_parser("harvest", help="build a record from an official GitHub repository")
    h.add_argument("--repo", required=True, help="owner/name of the manufacturer's repository")
    h.add_argument("--board-id", required=True)
    h.add_argument("--manufacturer", required=True)
    h.add_argument("--family", required=True)
    h.add_argument("--board", required=True)
    h.add_argument("--product-page", required=True)
    h.add_argument("--part-number", default="UNVERIFIED")
    h.add_argument("--revision", default="unverified")
    h.add_argument("--mcu", default="UNVERIFIED")
    h.add_argument("--arch", default=None)
    h.add_argument("--status", default="unknown",
                   choices=["active", "not_recommended", "discontinued", "unknown"])
    h.add_argument("--documentation", default=None)
    h.add_argument("--ref", default=None, help="branch or tag; default: the default branch")
    h.add_argument("--path", default=None,
                   help="the board's folder, when the repository holds several boards")
    h.add_argument("--no-absence", action="store_true",
                   help="do not emit available=false for formats missing from the index")
    h.add_argument("--out", default=None)
    h.set_defaults(func=cmd_harvest)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
