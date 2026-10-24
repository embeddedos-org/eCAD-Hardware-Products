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

- EoS Feather RP2040, an original board in the Feather form factor (50.8 × 22.86 mm, four layers),
  all rights reserved like the others: RP2040, 16 MB QSPI flash, USB-C, a LiPo charger with load
  sharing, STEMMA QT and a 3-pin SWD connector. Built with `tools/eos_boards` at ERC 0, DRC errors
  0, unconnected 0 and schematic parity 0; an independent review (0 blocker, 0 major, 9 minor), its
  findings fixed in the README or listed as rev B follow-ups, and a second independent check.
- Three more original EmbeddedOS boards (batch 3), all rights reserved like the others. Each was
  built with `tools/eos_boards` at ERC 0, DRC errors 0, unconnected 0 and schematic parity 0. Each
  had an independent review, its findings were fixed, and then a second reviewer checked the
  fixes against the rebuilt board.
  - EoS F280049C Board: a TI TMS320F280049C (C2000) board with two 40-pin BoosterPack sites, four
    layers; CP2102N USB-UART on SCIA; TI's 14-pin JTAG header in place of the on-board XDS110.
  - EoS RA4M2 Board: a Renesas RA4M2 board that fits Uno R3 shields; SPI and I²C Pmod ports, a
    40-pin GPIO header, the chip's USB device port, a CP2102N on the boot UART, and SWD.
  - EoS RL78G13 Board: a Renesas RL78/G13 (R5F100LEAFB) stick, 30 × 100 mm, with two 30-pin
    headers 25.4 mm apart, a USB-C serial port and an external TOOL0 debug connector.

  The vendor boards' on-board debug probes run proprietary firmware; these boards have a JTAG,
  SWD or TOOL0 header instead.
- `EoS_MCU` symbols for the R7FA4M2AD3CFP, R5F100LEAFB and TMS320F280049CPZ, each checked pin for
  pin against its data sheet (MIT, like the generator).
- `tools/eos_boards`:
  - no via in a surface pad, other than the vias a chip's exposed pad takes: every via keeps
    `VIA_PAD_GAP` (0.1 mm) from the pads of its own net, so the solder mask tents it. The maze
    router, the fan-out, the repair step, the fragment joins and the stitching keep to it; a new
    finish step, `ease_vias`, moves a router via that sits closer; the DSN states
    `via_at_smd off` for Freerouting;
  - `router_keepouts` takes `"B.Cu"` to keep the bottom layer clear (under a crystal);
  - `pour_keepouts`: one-layer areas no pour fills (the RL78 manual forbids ground under the
    X1/X2 wiring and resonator);
  - `ground_vias`: on two layers, a via beside each ground pad of the named parts;
  - `fanout_first`: the named parts get their plane vias before the priority routes;
  - the build refuses a malformed keep-out or an unknown part in these options.
- Tests: no via in or within `VIA_PAD_GAP` of a surface pad on any board built from now on, with
  the ten boards built before the rule listed until they are rebuilt; pour keep-outs hold no
  pour; the new options reach the board spec; the batch-3 symbols' supply and debug pins.

- Eight more original EmbeddedOS boards (batch 2), all rights reserved like the others. Each was
  built with `tools/eos_boards` at ERC 0, DRC errors 0, unconnected 0 and schematic parity 0. Each
  had an independent review, its findings were fixed, and then a second reviewer checked the
  fixes. On every board the USB pairs, crystal lines and decoupling are laid as priority routes.
  - EoS ATmega328P Board: fits Uno R3 shields; CH340C USB-UART with Ioff buffers and an open-drain
    auto-reset; ICSP header.
  - EoS MSP430G2 Board: an MSP430G2553 in a DIP-20 socket; takes 20-pin BoosterPacks; CP2102N
    USB-UART; Spy-Bi-Wire header.
  - EoS TM4C123 Board: takes 40-pin BoosterPacks; the chip's own USB device port, a CP2102N
    USB-UART and SWD.
  - EoS KL25 Board: an NXP KL25Z board that fits Uno R3 shields, with its USB device port, an
    accelerometer and SWD.
  - EoS STM32 64: an STM32F411RE in the 64-pin Nucleo format, with morpho and Uno headers, a 7–12 V
    buck and SWD.
  - EoS LPC55S69 Board: four layers; fits Uno R3 shields; two USB-C ports with a TPS2116 power mux
    and a TPS7A91 LDO.
  - EoS KE16Z Board: an NXP KE16Z board that fits Uno R3 shields; CP2102N USB-UART; the CAN pins on
    a header.
  - EoS RA2E1 Board: a Renesas RA2E1 board that fits Uno R3 shields; two Pmod headers; a CP2102N on
    the chip's boot UART.

  Each vendor board's on-board debug probe runs proprietary firmware. These boards have a standard
  SWD or Spy-Bi-Wire header instead.
- Generic libraries (MIT, like the generator):
  - `EoS_MCU` symbols for the TM4C123GH6PM, LPC55S69JBD100 and R7FA2E1A92DFM, each checked pin
    for pin against its data sheet;
  - `footprints/generate.py`, which writes `EoS_Packages.pretty`: NXP's HLQFP-100 (SOT1570-3) from
    the LPC55S6x data sheet's land pattern.

  A board that ships a copy of them credits them as MIT in its `LICENSE.txt`, not as the owner's.
- `tools/eos_boards`:
  - an exposed pad is now recognised as the biggest pad of a part with four or more pads, over
    1.5 mm across. A QFN-20's 1.8 mm centre pad counts; a two-pad part or a lone test pad doesn't.
  - the four vias move in on a small pad.
- EoS Motion Wing: a FeatherWing with an ADXL343 accelerometer and an ADT7410 temperature sensor
  on I2C. It has removable pull-ups and jumpers for the addresses and interrupts. The outline and
  headers come from Adafruit's published Feather specification. The ADT7410 symbol is new:
  `EoS_Sensors`, written by `symbols/generate.py`.
- EoS ESP32 DevKit: an ESP32-WROOM-32E board. It has a USB-C port, a CP2102N USB-UART with the
  esptool auto-program circuit, and a 1 A 3.3 V regulator. The headers follow Espressif's
  published DevKitC V4 grid, and the module antenna overhangs the edge.
- `tools/eos_boards` build fixes, all found while building these boards:
  - stacked pin numbers (`[1,15,38,39]`) reach every pad;
  - no-connect net names match KiCad's (`{slash}`, unnamed pins);
  - pre-routes and repairs use the net class's width;
  - the router gets a 0.01 mm clearance margin, and necks below the minimum width are widened
    (locked copper excepted);
  - a clearance clash between two routed items is ripped up and rerouted;
  - silkscreen strokes are at least 0.15 mm.
- Tests: a `spec_for` integration test, a check of the carriers against the datasheets' Figure 4,
  intent tests for the new boards, and a check that each board README's results table matches
  its build report.
- EoS CM4 Base, a carrier for the Raspberry Pi Compute Module 4. It is EoS CM5 Base's layout,
  changed where the CM4 differs:
  - USB-C with 5.1 kohm CC pull-downs, also routed to AnalogIP0/1;
  - one USB 2.0 port that a TS3USB30E switches between USB-C (device) and USB-A (host),
    by USB_OTG_ID;
  - a reset button on RUN_PG through 220 ohm, and a buffered power LED;
  - no copper under the CM4's antenna (`copper_keepouts`), as its datasheet requires.
  Every pin's net comes from the CM4 datasheet. `reference/cm4_pins.json` is written by
  `extract_cm4.py`. The tests check the connector pads and holes at 1 nm and every pin's net.
  Like the other EmbeddedOS boards, it is all rights reserved, not MIT.
- EoS CM4 Base and EoS ESP32 DevKit place their USB-C receptacles at `design.USB_C_EDGE`, like
  the first four boards (see Fixed), and are rebuilt.
- `tools/eos_boards`: on a two-layer board, a chip's exposed ground pad now gets the same 2 × 2
  vias as on a four-layer one, into the bottom pour. EoS ESP32 DevKit's CP2102N centre pad had none
  and reached ground through one track; the board is rebuilt. A footprint that brings its own
  thermal vias (the RP2350A's, the ESP32-S3 module's) gets none added. A test checks every board.
- The board index and the tests take the list of boards from `boards/eos/` itself. A test
  checks that every index row matches its board's build report.
- `copper_keepouts` in `tools/eos_boards`: no copper on any layer inside a rectangle, kept as a
  rule area that zone fills, the router and DRC all honour. EoS CM5 Base keeps the CM5's
  antenna cut-out clear with it, as the CM5 datasheet requires (section 4.1.2).
- `tools/eos_boards`, a board generator, and four original boards built with it under
  `boards/eos/`: EoS Learn RP2350, EoS Sense Cape for PocketBeagle, EoS Probe S3 and EoS CM5
  Base. Each board is written in one design file. From it the generator writes the KiCad
  schematic and board, routes it, checks it, and exports the fabrication outputs. Routing is
  Freerouting, then a two-layer maze router with local rip-up for anything left open. All four
  report 0 ERC violations, 0 DRC errors, 0 unconnected items and 0 schematic-parity
  differences. A build that fails any check writes no outputs. The boards are (c) 2026
  Kartikeydheer Srivastava, all rights reserved, and not under the repository's MIT licence.
  Anyone may view them; any other use needs Kartikeydheer Srivastava's written permission.
  EmbeddedOS (EoS) Research Foundation has a limited, revocable permission
  (`boards/eos/README.md#licence`). The generator itself stays MIT.
- Reference reuse at 1 nm resolution: `tools/eos_boards/reference/extract_rpi_minimal.py`
  takes the RP2350A core layout from Raspberry Pi's MIT-licensed minimal design, which the
  RP2350 datasheet says the regulator layout must follow. EoS Learn RP2350 places it
  unchanged. `tests/unit/test_eos_boards.py` checks every reused footprint, track, via and zone
  corner in integer nanometres. It also checks:
  - the cape's 72 socket pads against PocketBeagle's header pins, from BeagleBoard.org's board
    file (CC BY 4.0);
  - the carrier's 200 connector pads and 4 mounting holes against the CM5 footprint in
    Raspberry Pi's CM5 IO Board files (facts only);
  - each board's documented straps, pull-ups, translator directions and power path, read back
    from the built boards.

  Each reference file records the SHA-256 of its source.

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

- `tools/eos_boards`: the finishing step no longer crashes in `prune_dangling`. KiCad 10's Python
  bindings broke when the proxies of removed tracks and vias were freed (`TypeError:
  'swig_runtime_data5.SwigPyObject' object is not iterable`, exit 139; 3 of the EoS Feather
  RP2040's first 4 full builds). The removed items are now kept referenced until the process
  exits. The output is unchanged: on EoS Probe S3, EoS Learn RP2350 and EoS CM5 Base the finished
  boards with and without the change are identical as sets of items (uuids dropped, order ignored).
- EmbeddedOS boards: each USB-C receptacle (HRO TYPE-C-31-M-12) now sits where HRO's recommended
  layout puts it, its footprint origin 3.19 mm from the board edge (`design.USB_C_EDGE`; HRO
  draws the PCB edge 5.79 mm from the locating pegs). At the old 3.8 mm the shell's face was
  0.15 mm behind the edge, so a plug's overmold could meet the board before the plug seated. It
  now stands about 0.46 mm proud. EoS Learn RP2350, EoS Probe S3 and EoS CM5 Base are rebuilt,
  and a test checks every board's receptacles. The review of a later board found it. On EoS CM5
  Base, GPIO2 (the header's SDA) is now routed before the autorouter: after the move the router
  boxed in its pad on the CM5 connector twice.
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

