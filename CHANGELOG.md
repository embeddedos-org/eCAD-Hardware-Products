# Changelog

## [Unreleased]

`feat/domain-electrical`, published as PR #38 (stacked on #37 and #36), not released. It had
two independent reviews at `bf04f1b` (2026-09-28), whose findings are fixed
below (plan §7.6); the fixes have had no review of their own, and the CI
`spice` job has never run.

On it, `feat/domain-digital`, stacked on PR #38, not released.
It had two independent reviews at `905294f` (`6fbae29` after its rebase onto
PR #38's head), whose findings are fixed below
(plan §7.7); the fixes have had no review of their own, and the CI `hdl` job
has never run.

### Added

- The dev-board CAD mirror (issue #48): `tools/devboard_cad/mirror.py` copies the CAD
  design of every board whose licence allows redistribution into
  `boards/cad/<vendor>/<board>/cad/`, unmodified, with an `ATTRIBUTION.md` per board;
  the index is `tools/devboard_cad/mirror-manifest.json`. A record names one file per
  format, so `mirror.py index` lists every CAD file at the repository commit the record
  pins (`repo-cad-index.json`) and the whole design is mirrored in the manufacturer's
  layout: every schematic sheet, project file, library, fabrication output and 3D model.
  A file is copied only if its SHA-256 matches the record or its git blob ID matches the
  commit (Git LFS objects against their pointer), and only if its content is CAD.
  Archives are unpacked to their CAD members; documents (PDFs, BOMs, readmes, reports) are
  never copied, and what was left out is listed. `mirror.py check` proves completeness and
  integrity (from the bytes, or from Git LFS pointers if the mirror moves to LFS) and runs
  in the test suite.
- Licences read from a manufacturer's own package or page
  (`tools/devboard_cad/licence_statements.json`, `read_licenses.py --statements`), each
  applied only while the source keeps its reviewed SHA-256 and every quote. Four boards
  gain an open licence this way: Arduino UNO R3 (CC BY-SA 4.0), Raspberry Pi 5 (MIT, 3D
  model only), Raspberry Pi Compute Module IO board (BSD-3-Clause) and Raspberry Pi Pico
  (a grant in 0BSD wording). The Pico record gains Raspberry Pi's Cadence Allegro design
  package, and the UNO R3 record points at the CC BY-SA 4.0 package instead of the
  archive marked `CC-SA-BY-NC`.
- Ten more SparkFun boards under CC BY-SA 4.0, read from the notice SparkFun places on the
  design itself (the `CREATIVE_COMMONS` drawing frame on the Eagle schematic and board, or
  footprint text on the KiCad PCB), and eleven BeagleBoard capes (CC BY 4.0 and CC BY-SA
  4.0) from the licence file in each cape's folder. `beagleboard:capes`, one record for
  thirteen capes under two licences, is replaced by one record per licensed cape:
  `harvest_github.py harvest --path` records one folder of a shared repository, and
  `mirror.py index` takes only that folder (issue #51).
- The XIAO Debug Mate's KiCad schematic (seven sheets) under CC BY-SA 4.0, read from the
  drawing frame Seeed embeds in the design. A licence statement can quote a file that a
  KiCad design embeds in itself (`embedded`), and `mirror.py` copies only the files a
  scoped licence covers, listing the rest in `ATTRIBUTION.md` under "Not covered by the
  licence": here the board layout, the project file and the four housing models. Gerber,
  drill and model files are matched to a licence by their content, and a scoped licence does
  not reach project, library or rule files. `check` fails on a mirrored file its licence no
  longer covers.
- The digital domain (issue #27, plan §21 item 5): Verilog sources are read
  by a strict allow-list grammar (`tools/ecad_model/verilog.py`) into the
  engineering model, the adapter (`tools/ecad_model/domains/digital.py`)
  writes one simulation file from the model -- each module's text verbatim,
  then a harness that drives the clock, reset and stimulus and measures --
  and Icarus Verilog runs it. Nine `SIMPLIFIED` metrics are compared with
  closed-form references (V3) and requirements (V4). One design class is
  validated: the UART 8N1 loopback.
- The dataset item `datasets/cad/uart_loopback_001`: `rtl/uart_tx.v` and
  `rtl/uart_rx.v`, copied unmodified, in a self-authored loopback testbench.
  Its receipt is `BLOCKED` by design: V0-V3 `PASS`, six illustrative limits
  met (`WARNING`), and REQ-DIG-007 `BLOCKED` because no target device is
  selected.
- Engineering-model format 1.2.0: a component's `hdl` member (module,
  source, ports, signals, parameter facets and the module's text verbatim);
  annotations 1.2.0: a `digital` facet on a component without CAD;
  `digital-vocabulary.schema.json`.
- REUSE-1: a provenance artefact may record the repository file it is a
  byte-identical copy of (`copied_from`, provenance format 1.1.0), which
  `check` and V0 re-hash; the origin must lie outside the item, compared by
  file identity. `VALIDATOR_VERSION` is 1.1.0.
- `run_process` can copy the files a request declares out of its workspace
  (`collect`, `collect_into`: regular files of at most 64 MiB, after a
  completed run only) and give the child an empty stdin (`stdin_devnull`);
  both are opt-in, so no other caller changes.
- A CI `hdl` job that installs Icarus Verilog and runs the complete suite
  with `ECAD_REQUIRE_HDL_TOOLS=1`, `check` and `validate` on the digital
  item.
- `docs/digital-domain-v1.md` and `docs/design/digital-domain-design.md`.

- The electrical domain (issue #27, plan §21 item 4): a SPICE netlist is
  read by a strict allow-list parser (`tools/ecad_model/spice.py`) into the
  engineering model, the adapter (`tools/ecad_model/domains/electrical.py`)
  writes the ngspice deck from the model, and ten `SIMPLIFIED` metrics are
  compared with closed-form references (V3) and requirements (V4). One
  network class is validated: a series-precharge supply input.
- The dataset item `datasets/cad/servo_supply_001`: the eServo-200 drive's
  48 V supply input as a self-authored testbench in which no element is a
  real part. Its receipt is `BLOCKED` by design: V0-V3 `PASS`, five
  illustrative limits met (`WARNING`), three part-rating limits `BLOCKED`
  because no part is selected.
- Engineering-model format 1.1.0: a component's `circuit` member (designator,
  element, terminals, switch model), six electrical component kinds, and
  `circuit_elements` in the design annotations; the schemas require 1.1.0 for
  a document that uses them. `electrical-vocabulary.schema.json`.
- A CI `spice` job that installs ngspice and runs the complete suite with
  `ECAD_REQUIRE_SPICE_TOOLS=1`, `check` and `validate` on the electrical item.
- `docs/electrical-domain-v1.md`.

### Changed

- The Icarus Verilog tool adapter runs both of its steps, and its version
  probe, through `run_process`, with the scrubbed environment, the output cap
  and an empty stdin (ARCH-10); it returns the metrics its inputs declare as
  `ECAD_METRIC` lines, read from vvp's stdout (ARCH-2, iverilog half); and it
  refuses case arguments rather than passing them to `iverilog`.
- The robotic joint's and the servo supply's digital domain is
  `NOT_APPLICABLE` rather than `NOT_IMPLEMENTED`; no derived number changed.
- `.gitattributes` keeps `rtl/uart_tx.v` and `rtl/uart_rx.v`, the origins
  the digital item copies, byte-exact on checkout.
- The ngspice tool adapter runs `ngspice -b <deck>` only and returns the
  `.meas` results the deck declares, read from stdout (ARCH-2, ngspice half);
  it read none before. Its version comes from the `--version` banner
  (RESULT-8), and a failed version probe gives a reason code the receipt
  accepts (RESULT-2, ngspice path only).
- `Extraction.producer` is required: each domain adapter names the producer
  of its engineering model. The domain adapter protocol is no longer
  provisional.
- The robotic joint's electrical domain is `NOT_APPLICABLE` rather than
  `NOT_IMPLEMENTED`; no derived number changed.
- `.gitattributes` keeps every dataset file, `LICENSE` and the cited product
  sheet byte-exact on checkout.

### Fixed

- `read_licenses.py` finds the licence file whatever its case. It asked GitHub
  for fixed spellings (`LICENSE.md`, `LICENSE`, ...), and GitHub paths are
  case-sensitive, so SparkFun's `license.md` and `License.md` were never read:
  10 boards whose manufacturer states "SparkFun hardware is released under
  Creative Commons Share-alike 4.0 International" stayed UNVERIFIED. It now
  lists the repository root, and reads the README through GitHub's readme
  endpoint. A README that points at a licence file which is not there still
  leaves the board UNVERIFIED.
- The mirror carries the licence text where the licence requires it. MIT, BSD
  and Apache-2.0 require their text in every copy, and the five mirrored boards
  under them (M5Stack, Radxa `hw`, Seeed XIAO, Seeed Wio Terminal, ROBOTIS
  XelNetwork) had only the licence's name. `ATTRIBUTION.md` now ends with the
  manufacturer's licence file, verbatim, from the commit the files are pinned
  to (`tools/devboard_cad/licence-notices.json`, `read_licenses.py --notices`);
  `mirror.py check` fails without it.

### Fixed (review of the electrical branch, plan §7.6)

- Netlist node names start with `n_` and switch model names with `SW_`:
  ngspice read a node named `time` in a `.meas` as the time axis, so a real
  limit on the bus peak passed at 0.1, and other names crashed or stopped
  it (CS-1).
- Extraction refuses a netlist the deck's windows cannot measure: a fault
  switch that does not close and settle before T_END (a limit on the fault
  current had passed on the pre-fault current), a non-positive resistance,
  capacitance or switch resistance, and a ramp still rising at the bypass
  command; a closed form that divides by zero or overflows is
  `REFERENCE_NOT_APPLICABLE`, and no item can cost the receipt (CS-2, CS-3).
- The precharge closed forms include the open fault switch's off
  resistance (CS-4).
- A tenth metric, `startup_peak_current_a`, sees the surge when an early
  bypass closes, which the inrush window missed; REF-EL-010 and REQ-EL-008
  compare and limit it (CS-5).
- Documentation that said ngspice only runs the regenerated deck, or that
  V2's invariants read the committed deck; untested conditions and
  branches; a CI test that let a skip hide (HT-1 to HT-8).

### Fixed (review of the digital branch, plan §7.7)

- A byte that never arrives counts its 8 bits in `rx_bit_errors`, and no
  framing-error count of 0 is reported while a byte is missing: a receiver
  that never set `rx_valid` had passed the bit and framing checks (CS-1).
- The grammar refuses the names Icarus reserves (`bool`, `wone`, `wreal`) and
  a unary operator applied to another (CS-2); extraction refuses a parameter
  above 2^31 - 1, which the harness's unsized decimal cannot hold (CS-4).
- REUSE-1 tells an origin inside the item by file identity, not spelling
  (CS-3); the adapter's version probe runs through `run_process` (CS-6).
- V1 compares an instance's clock with the harness's in whole Hz (HT-1);
  REQ-DIG-006 names the one instant its metric is measured at (HT-6).
- Rules and guards no test reached, a stuck receiver bit, depth limits at
  5000 levels, a CI step under `if: false`, and `MEMORY.md` rows that
  overstated what was tested or checked (CS-5, HT-3, HT-4, HT-7, HT-8).

## [3.0.1] - 2026-05-16

### Production Release — Unified EmbeddedOS-org v3.0.1

This is the synchronized production release across all 18 EmbeddedOS-org repos.

- Refreshed governance: LICENSE, NOTICE, CITATION.cff, SECURITY.md
- CI/CD pipelines hardened: release.yml, book-build.yml, video-build.yml, deploy-pages.yml
- Release artifacts produced for: Linux x64/arm64, macOS x64/arm64, Windows x64, Docker, plus per-repo embedded/mobile/extension targets
- mdBook documentation built and deployed to GitHub Pages
- Promo video rendered and attached as a release asset

## [3.0.0] - 2026-05-13

### Production Release — Unified EmbeddedOS-org v3.0.0

This is the synchronized production release across all 18 EmbeddedOS-org repos.

- Refreshed governance: LICENSE, NOTICE, CITATION.cff, SECURITY.md
- CI/CD pipelines hardened: release.yml, book-build.yml, video-build.yml, deploy-pages.yml
- Release artifacts produced for: Linux x64/arm64, macOS x64/arm64, Windows x64, Docker, plus per-repo embedded/mobile/extension targets
- mdBook documentation built and deployed to GitHub Pages
- Promo video rendered and attached as a release asset

