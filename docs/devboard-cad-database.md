# Development-Board CAD Database (issue #28)

A board-by-board master database of third-party development-board CAD
availability. Every record binds one exact board and hardware revision;
family-level claims are not permitted (see issue #28, sections 9–12).

## What a record may claim

Availability is tri-state per format: `true` (verified present), `false`
(verified absent), `null` (unknown). A positive query matches only `true`, so
unknown is never silently counted as a yes.

Contract `1.1.0` adds the constraint that makes those states mean something:
**a claim is not assertable by hand.**

| State   | What the record must carry                                                |
|---------|---------------------------------------------------------------------------|
| `true`  | a URL and an `evidence.sha256` of bytes that were actually retrieved        |
| `false` | either a 404/410 from the official URL, or an `index_ref` naming an exhaustive official file index, pinned to an immutable revision |
| `null`  | no evidence at all                                                          |

The last row is the one that keeps the database honest. "We have not looked"
and "we looked and it is not published" are different facts, and an unknown
that carried evidence would blur them.

## Why availability is decided from bytes, not from status codes

Both of these were observed against live vendor infrastructure while building
this, and both defeat the obvious implementation:

- `datasheets.raspberrypi.com` answers **HEAD** for the Pico STEP archive with
  `content-type: text/html` and `content-length: 0`, while a **GET** of the same
  URL returns a genuine 266,009-byte ZIP. HEAD produces false *negatives*, so
  `verify.py` only ever issues GET.
- `raspberrypi.com` answers an automated client with a Cloudflare interstitial
  at status **200**. A 200 is not a file, so every response is content-sniffed
  and an HTML body never satisfies a CAD claim.

A third rule follows from the same reasoning: a 404 on a *guessed* URL means the
guess was wrong, not that the vendor publishes nothing. `verify.py` records
`null` for it unless `--absent-on-404` is passed, which is only correct when the
URL came from the vendor's own index.

## Source hierarchy

Per issue #28, section 10, preferred source order is:

1. Manufacturer's official CAD/design-file repository
2. Manufacturer's official product page
3. Manufacturer's official GitHub repository
4. Manufacturer's official documentation
5. Authorized distributor documentation
6. Community repositories only when no official source exists

A manufacturer's GitHub repository has one property no product page has: its
tree is **exhaustive**. That is what makes `available: false` provable, and it is
why `harvest_github.py` exists.

## Record lifecycle

- `incomplete`: identity recorded; no availability determined.
- `partial`: some formats determined, or identity not yet pinned to an exact
  part number, MCU and revision.
- `verified`: every format determined and identity fully pinned.

`record_status` is **derived** from the record by `verify.derive_status()` and
checked in CI, so it cannot drift out of step with the data it summarises.

## Identity: findings and gaps are different facts

Three reserved values keep "nobody has looked" separate from "we looked and there is none".
Only the first blocks a record from reaching `verified`:

| Field | Gap | Finding |
|---|---|---|
| `revision` | `unverified` | `not-stated` — an exhaustive official index names no revision |
| `mcu_soc` | `UNVERIFIED` | `not-applicable` — a passive add-on board (FeatherWing, shield, HAT, cape) |
| `part_number` | `UNVERIFIED` | the manufacturer's own part number |

Collapsing the two would make an unfinished record look identical to a complete one about
a board that genuinely has no revision.

## Tools

The pipeline is: **propose candidates → verify from bytes → read licences → gate**.
No step ever asserts that a file exists; only `verify.py` decides that, and only from
content it retrieved.

```bash
# 1a. Enumerate manufacturer repositories and turn them into records.
#     Coverage grows by editing vendors.json, not by editing code.
python3 tools/devboard_cad/discover_github.py discover --out candidates.json
python3 tools/devboard_cad/discover_github.py emit --manifest candidates.json

# 1b. One repository at a time, when you already know it.
python3 tools/devboard_cad/harvest_github.py harvest \
    --repo adafruit/Adafruit-Feather-RP2040-PCB \
    --board-id adafruit:feather-rp2040 \
    --manufacturer "Adafruit Industries" --family Feather \
    --board "Adafruit Feather RP2040" --part-number 4884 \
    --mcu "Raspberry Pi RP2040" \
    --product-page https://www.adafruit.com/product/4884

# 1c. Manufacturers that do not publish on GitHub, from direct_sources.json.
python3 tools/devboard_cad/seed_direct.py

# 2. Decide availability by retrieving and content-checking each candidate.
python3 tools/devboard_cad/verify.py verify --apply --jobs 8 --quiet

# 3. Read the hardware licence from the manufacturer's own LICENSE or README.
python3 tools/devboard_cad/read_licenses.py

# 4. Gate: schema, uniqueness, filename agreement, derived status, licence citations.
python3 tools/devboard_cad/validate_records.py

# 5. Drift: re-fetch every claimed file and compare digests. Networked, advisory.
python3 tools/devboard_cad/validate_records.py --revalidate
```

### Coverage

29 of the 31 ecosystems in issue #28 §2 have at least one record. Two do not, and both are
access walls rather than gaps in this tooling — each was checked from three directions and
the result recorded rather than worked around:

| Ecosystem | What was tried | Result |
|---|---|---|
| 2.10 Silicon Labs | `silabs.com` document URLs; `docs.silabs.com`; the `SiliconLabs` GitHub org | every file URL returns **403** to an automated client; the org's two hardware repos hold 3 and 6 blobs, no CAD |
| 2.18 Digilent | `digilent.com/reference/...`; `files.digilent.com`; all 16 `Digilent/*-HW` repos | site returns **403**; every `-HW` repo is a *Vivado project* (HDL, constraints, block design), zero CAD files |

Two further negative results worth keeping, so they are not re-investigated:
`Xilinx/XilinxBoardStore` holds DRAM part CSVs, not board CAD, and Terasic's DE-series
pages carry no direct file links.

### Manufacturers that cannot be enumerated

Issue #28 section 10 ranks the official product page and documentation above a repository,
but neither is machine-enumerable, and two failure modes are permanent rather than
incidental:

* `raspberrypi.com` answers an automated client with a Cloudflare interstitial, and its
  document portal is JavaScript-rendered. Its URLs were recovered instead from
  `raspberrypi/documentation`, the manufacturer's own public documentation source, which
  cites official `pip.raspberrypi.com` document IDs.
* `st.com` does not answer an automated client at all. Boards whose files live only there
  cannot be verified by this pipeline, and no record claims otherwise.

Those manufacturers are served by `direct_sources.json`: a human supplies candidate URLs
from the official source and `verify.py` decides. Because a curated list is not
exhaustive, `seed_direct.py` never records `available: false` — absence is only provable
against an index that enumerates everything.

`verify.py` caches responses outside the repository (`~/.cache/devboard-cad`, or
`DEVBOARD_CAD_CACHE`) and rate-limits per host, and it never commits what it
fetched: records hold digests and URLs only. Most board CAD is not
redistributable, which is exactly why `licenses.redistribution_allowed` is a
field rather than an assumption. Only the [mirror](#mirror) copies files, and only
for boards where that field is `true`.

## Licensing

Licensing is tracked separately from file availability, per issue #28 section 12.
File availability is mechanical; reading a vendor's terms is not, and
`commercial_use_allowed` is the field with real downstream consequences. It is
left `null` unless the licence has been read, and CI requires that any non-null
permission is accompanied by a named `hardware_license` and a `license_url`.

`read_licenses.py` reads the manufacturer's own LICENSE or README and matches it against a
table of licences whose terms are already settled. It never interprets novel prose: an
unrecognised statement leaves the record `UNVERIFIED`, which the gate then requires. The
distinction is between reading and inferring — quoting "SparkFun hardware is released
under Creative Commons Share-alike 4.0 International" from `LICENSE.md` is a reading;
concluding a board is probably CC-licensed because its vendor usually is would not be.

One case recurs and is recorded rather than smoothed over: Adafruit's READMEs name
"Creative Commons Attribution/Share-Alike" with no version, and the `license.txt` they
point at is usually absent from the repository. Every CC BY-SA version permits commercial
use and modification under attribution and share-alike — the non-commercial variants are
separately named BY-NC-SA — so the permissions are determinable while the version is not.
Both facts go in the record.

Some manufacturers state their terms outside GitHub: inside the download package, or on a
documentation page. A person reads those and records them in
`tools/devboard_cad/licence_statements.json`, with the SHA-256 of the bytes read and the
sentences quoted. `read_licenses.py --statements` applies a statement only while the source
still has that digest and every quote is still in it, so a vendor changing its terms
leaves the record as it was and reports the refusal. A statement can be limited to the files
it covers: Raspberry Pi's MIT licence for the Raspberry Pi 5 covers the 3D model, so only
`cad_license` and `mechanical_cad_license` are set and `hardware_license` says
"MIT (3D model only)". The mirror honours that scope file by file. Gerber and drill files
need `pcb_license` and STEP, IGES, STL, VRML, OBJ and DXF models `mechanical_cad_license`,
known by their content whatever their suffix. A native design document is known by its
suffix: a schematic (`.sch`, `.kicad_sch`, `.SchDoc`, OrCAD `.dsn`) needs `schematic_license`,
a board (`.brd`, `.kicad_pcb`, `.PcbDoc`) `pcb_license`, and SolidWorks, Fusion 360 and
FreeCAD models `mechanical_cad_license`. Projects, libraries and rule files (`.kicad_pro`,
`.kicad_sym`, `.kicad_mod`, `.lbr`, `.SchLib`, `.PcbLib`, `.PrjPcb`, Fritzing `.fzz`) belong to
the whole design: they need `cad_license`, and a licence that leaves any kind of file out
does not reach them, so the Raspberry Pi 5's would not copy a project file. A file outside
the licence is not copied; it is listed in the board's `ATTRIBUTION.md` under "Not covered by
the licence" and in the manifest's `excluded`. A record without the per-kind fields is
covered as a whole by `cad_license`.

A statement's `embedded` names a file that a KiCad 9 design embeds in itself, such as its
drawing frame. KiCad stores it zstd-compressed, so the quotes are checked in the decoded
file. zstd is in Python's standard library from 3.14; an older interpreter refuses such a
statement rather than applying it unread.

| Board | Licence | Read from |
|---|---|---|
| `arduino:uno-rev3` | CC BY-SA 4.0 | `License.txt` in the CAD package linked from docs.arduino.cc. The older `content.arduino.cc` archive marks the same files `CC-SA-BY-NC`, so the record points at the package instead. |
| `raspberry-pi:5` | MIT (3D model only) | `LICENSE.txt` in the STEP package |
| `raspberry-pi:cmio` | BSD-3-Clause | `README.txt` in the design package, which carries the three clauses without naming them |
| `raspberry-pi:pico` | Permission grant in 0BSD wording | the Pico documentation, which grants use, copying, modification and distribution "for any purpose, with or without fee"; the design package repeats it in `LICENSE.txt` |
| 10 SparkFun boards | CC BY-SA 4.0 | the design file itself: "Released under the Creative Commons Attribution Share-Alike 4.0 License", on SparkFun's `CREATIVE_COMMONS` drawing frame placed on the schematic and board (Eagle) or as footprint text on the PCB (KiCad). Their READMEs point to a `LICENSE.md` that is not in the repository. |
| `seeed-studio:oshw-xiao-debug-mate` | CC BY-SA 4.0 (schematic only) | the drawing frame `Seeed_SCH_Open_Source.kicad_wks`, embedded in the root sheet of the KiCad design linked from the official wiki page, prints "CC BY-SA 4.0" in the title block of all seven sheets. The board layout, the project file and the housing models carry no licence and are not copied. |
| 11 BeagleBoard capes | CC BY 4.0 (9), CC BY-SA 4.0 (2) | the `LICENSE` file in each cape's folder of `beagleboard/capes`; each names its own copyright holder, so these statements are marked `notice` and the licence file goes into the board's `ATTRIBUTION.md` |

`beagleboard/capes` holds thirteen capes in one repository, under two licences and several
copyright holders, so it is recorded as one record per cape (`harvest_github.py harvest
--path beaglebone/Load`): the record's `official_cad_repository` is the cape's folder at the
pinned commit, and `mirror.py index` takes only that folder. The Servo and GamePup capes
have no licence file and are not recorded.

## Mirror

`boards/cad/` holds an unmodified copy of the **CAD files** of every board whose record
sets `licenses.redistribution_allowed` to `true` (issue #48). Boards without that
permission keep their link and digest only; nothing of theirs is copied. Documents (schematic
PDFs, drawings, BOMs, datasheets, readmes) are not copied either, so the folder holds CAD
and nothing else.

A record names one file per format, which is enough to say a format exists but not to
build the board: a KiCad project has several schematic sheets, a project file and its own
footprints, and fabrication outputs and 3D models sit beside the sources. So the mirror
takes the whole design. When a record's files are pinned to one commit of the
manufacturer's repository, `mirror.py index` lists every CAD file in that commit into
`tools/devboard_cad/repo-cad-index.json`, with its git blob ID, and every one of them is
mirrored in the repository's own folder layout, so hierarchical sheets and 3D model paths
still resolve.

```
boards/cad/<vendor>/<board>/
  ATTRIBUTION.md   manufacturer, licence, every file with its source and digest, what was
                   left out of archives, and what the licence does not cover
  cad/             the design in the manufacturer's layout: Eagle, KiCad, Altium, OrCAD and
                   Allegro sources, projects and libraries, Gerber and drill files, STEP,
                   IGES, STL, VRML and DXF models; archives unpacked to their CAD members
tools/devboard_cad/repo-cad-index.json
                   every CAD file at each board's pinned commit, with its git blob ID
tools/devboard_cad/mirror-manifest.json
                   one entry per file: board, path, source, sha256, git blob, archive member,
                   size, licence; and the indexed files left out, with the reason
```

`ATTRIBUTION.md` stays beside the files on purpose: CC BY and CC BY-SA require the credit
and the licence notice to travel with the material, so a board's folder copied on its own
still carries them. MIT, BSD and Apache-2.0 go further and require the licence text itself
in every copy, so for those boards `ATTRIBUTION.md` ends with the manufacturer's licence,
verbatim. `read_licenses.py --notices` collects it into
`tools/devboard_cad/licence-notices.json`, from the repository's licence file at the commit
the board's files are pinned to, or from the package member a statement was read from.
`mirror.py build` refuses such a board without its text, and `check` fails if an
`ATTRIBUTION.md` lacks it or the text no longer matches its digest. A statement marked
`notice` puts its licence file into `ATTRIBUTION.md` whatever the licence, for boards whose
licence file names copyright holders other than the publisher.

`mirror.py build` copies a file only when all of these hold:

1. the board's licence allows redistribution and covers the file's kind (see the licence
   statements above): a licence scoped to part of a design, such as the Raspberry Pi 5's 3D
   model or the XIAO Debug Mate's schematic, leaves the other files out;
2. the bytes are the verified bytes. A file the record names must have the SHA-256 in
   `evidence.sha256`. A file from the index must have its git blob ID at the pinned commit,
   the identifier git itself stores the file under, so it is the manufacturer's file
   exactly; one the repository keeps in Git LFS is fetched from LFS and must match the
   pointer's SHA-256;
3. the bytes are CAD when read: identified from content, with a suffix deciding only for
   native formats that have no signature (OrCAD, SolidWorks, KiCad's JSON project file).
   An archive is unpacked and only its CAD members are written, in a folder named after
   it; its PDFs, spreadsheets, readmes and reports are left out and listed in
   `ATTRIBUTION.md`.

A file the record names that fails any of these is refused and the build fails. A file the
index chose by its name alone may simply not be CAD (a `.sch` in an unidentified binary
format, a `.zip` of datasheets): it is left out, listed in `ATTRIBUTION.md` and in the
manifest's `excluded`, and `check` accepts it only for that exact blob. An archive named `X.zip`
that holds a folder `X/` is unpacked into one folder `X`, not two. Paths longer than
200 characters, which Windows checkouts cannot hold, are flattened under a digest prefix,
and an archive member over GitHub's 100 MiB limit is left out and listed.

A build rewrites the manifest for the vendors it covers and removes whatever the manifest
no longer names, including a board left without CAD files. `check` fails on a missing
file, a digest or git blob mismatch, a stray file anywhere in `boards/cad/`, a missing
attribution, or a board that has lost its licence.

The files are committed as regular files, exactly as published. `.gitattributes`
exempts `boards/cad/*/*/cad/` from the repository's LFS rules and from line-ending
conversion, so every byte matches its digest. Git LFS was the first choice, but GitHub
refuses LFS uploads to a public fork, which is how this repository takes contributions.
Every file is under GitHub's 100 MB limit.

```bash
# List every CAD file at each mirrored board's pinned commit (uses the GitHub API).
python3 tools/devboard_cad/mirror.py index

# Copy the CAD files of one vendor, or of all vendors, reusing files whose digest matches.
python3 tools/devboard_cad/mirror.py build --vendor sparkfun
python3 tools/devboard_cad/mirror.py build

# Fail unless every redistributable CAD file is mirrored and every digest matches.
python3 tools/devboard_cad/mirror.py check
```

To check out only the boards you need:

```bash
git sparse-checkout set --no-cone '/*' '!/boards/cad/*/*/' '/boards/cad/adafruit/feather-rp2040/'
```

`check` also reads Git LFS pointer files: a pointer's `oid` is the SHA-256 of the object
it stands for. If the mirror later moves to LFS
(`git lfs migrate import --include="boards/cad/*/*/cad/**"`), completeness and integrity
stay provable in CI without downloading the binaries. `tests/unit/test_devboard_mirror.py`
runs it against the committed mirror.

## Schema

`schemas/devboard-cad/v1/board-record.schema.json` (contract `1.1.0`; records
written against `1.0.0` remain valid).

## Query

```bash
python3 tools/devboard_cad/query.py list
python3 tools/devboard_cad/query.py with-formats step
python3 tools/devboard_cad/query.py with-formats kicad schematic
python3 tools/devboard_cad/query.py full-stack
python3 tools/devboard_cad/query.py commercial-reuse
python3 tools/devboard_cad/query.py mechanical
python3 tools/devboard_cad/query.py open-electrical
```

These correspond to the six example queries in issue #28, section 11.
