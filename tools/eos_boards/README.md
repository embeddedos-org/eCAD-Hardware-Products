# eos_boards: boards built from a design file

Each board here is written as data: its parts, the net on every pin, and where each part
sits. From that one file the generator writes the KiCad schematic and board, routes it, checks
it and exports everything a fab needs. The schematic and the board can't disagree, because
both come from the same file and `kicad-cli pcb drc --schematic-parity` proves it on every
build.

```
python3 tools/eos_boards/build.py eos_learn_rp2350              # -> boards/eos/eos-learn-rp2350/
python3 tools/eos_boards/build.py eos_learn_rp2350 --place-only # stop after placement, report overlaps
```

Needs KiCad 10 (`kicad-cli` plus its bundled Python with `pcbnew`), Freerouting 2.4.1, and
Java 25 or newer. Set `KICAD_APP`, `FREEROUTING_JAR` and `JAVA` if they are not at the default
paths that `kicad_env.py` and `build.py` use.

## What a build does

1. **Schematic** (`schematic.py`). Every pin gets a wire stub and a net label; unused pins get
   a no-connect flag. `kicad-cli sch erc` must report 0 violations or the build stops. A pin with
   KiCad's stacked number, such as `[1,15,38,39]` for a module's ground pins, lands on each of
   those pads.
2. **Placement** (`pcb_build.py place`). Places footprints and links each one to its symbol.
   Adds the outline, design rules, net classes, inner planes and any reference copper (below).
   Then lays any `priority_routes` (a bus the design routes first, in a set order), and gives each
   plane-net pad a short stub and a via into its plane. An exposed pad gets a 2 × 2 array of vias
   in the pad, on a two-layer board too, into the bottom pour, unless its footprint brings its own
   thermal vias. They sit in the pad's paste openings, as the vias in Raspberry Pi's RP2350A pad
   do; order them tented or plugged where solder wicking matters. No other via may sit in a
   surface pad: solder wicks down an open barrel and starves the joint. The maze router (priority
   routes and repairs), the fan-out, the repair step's plane vias and the ground stitching all keep
   their vias off every surface pad, their own net's included, by `VIA_PAD_GAP` (0.1 mm): a
   solder-mask web between the two tents the via. Freerouting 2.4.1 already does by
   default; the DSN states it (`via_at_smd off`) so that a later default cannot change it.
   The fan-out's vias and stubs are locked, so the router treats them as fixed and cannot delete
   or move a pad's way into its plane. They are recorded in the spec (`fanout_copper`), so a later
   step can still prune one that ends up leading nowhere, and a rip-up that names one lifts the
   other side of the clash instead; a `via_dangling` DRC finding, a warning to KiCad, fails the
   build. Finally writes a Specctra DSN for the router.
3. **Routing**. Freerouting, headless. The router is given 0.01 mm more clearance than the board's
   rules, so its grid rounding never reaches DRC. Freerouting 2.4.1 routes a given DSN the same way
   every time and takes no seed, so a retry changes its own costs instead: when the repair rounds
   (step 5) still leave connections that a route could close, the build starts again from the placed
   board with the cost of a via doubled (`--router.scoring.via_costs=100`, default 50), then with the
   cost of ripping up routed copper tripled (`--router.scoring.start_ripup_costs=300`, default 100),
   up to three runs, and keeps the run that left the fewest connections open. On EoS Learn RP2350's
   placement these settings each gave a different route, and the via-cost run closed /GPIO5, which
   the default run had left open. A zone island left unconnected is no reason to route again. Logs go
   to `.build/freerouting.log`, `freerouting-2.log`, `freerouting-3.log`; `build-report.json`
   records `routing_runs` and `routing_run_kept`.
4. **Finish** (`pcb_build.py finish`). Imports the routes, widens any track the router necked
   below the board's minimum width, steps any router via that sits within `VIA_PAD_GAP` of a pad
   of its own net away from it (up to 0.5 mm, its tracks following, only where it still clears
   every other net), pours ground on the outer layers, stitches the pours and joins any pour
   fragments.
5. **DRC and repair**. Runs `kicad-cli pcb drc --schematic-parity`.
   - **Clearance clashes:** if two pieces of routed copper are too close (the autorouter can
     leave a via inside another net's clearance), `pcb_build.py ripup` lifts one net's copper
     there, and the next round sees it as open.
   - **Open connections:** any connection still open goes to `pcb_build.py repair`, which tries
     the options below in order. Pre-routes and repairs are laid at the net's class width. New
     copper avoids the board outline, the router keep-outs and every other net's copper, and
     keeps 0.25 mm between drilled holes:
   - a straight or dog-leg track;
   - a via into the net's plane;
   - a maze search on both outer layers;
   - lifting the router's own tracks next to the pin, then searching again.

   After each repair the pour fragments are joined again (`join_all_fragments`, as in step 4):
   new tracks can cut a pour into pieces that no via reaches. Up to six rounds.

   Every `pcb_build.py` step's exit code is checked: a place, finish, repair or rip-up step that
   crashes stops the build with its exit code, instead of passing for a round that found nothing to
   do. KiCad 10's bindings can crash when the proxy of an item taken off the board is freed, so
   every removal goes through one helper, `_remove`, which keeps the item referenced until the
   process exits.
   Then the saved board is read back for what a fab or an assembler would reject
   (`metrics.fab_problems`): no stack-up, or one whose copper is not the board's, and a side with
   surface-mount parts but fewer than three fiducials, or fiducials too near the edge or in a line.
   Any of these stops the build too.
6. **Outputs**. Gerbers and drill files (fabrication layers only), pick-and-place, BOM,
   STEP, schematic PDF and SVG, renders, `LICENSE.txt`, `build-report.json` with the ERC and
   DRC counts, and `metrics.json` (below).

Outputs are written only when every check passes: 0 ERC violations, 0 DRC errors, 0
unconnected items and 0 parity problems. A failed build stops before step 6: the previous
fabrication outputs, `LICENSE.txt` and `build-report.json` stay as they were, while `hardware/`,
`erc.json` and `drc.json` hold the failed attempt, so it can be inspected. Rebuild until it
passes before committing a board.

## Fabrication data in every board

`fabrication.py` holds what a fab reads from the board file itself.

**Stack-up.** Every `.kicad_pcb` carries its layer stack-up in the board setup, and KiCad copies it
into the Gerber job file (`fab/gerbers/*-job.gbrjob`, `MaterialStackup` and `Finish`). The numbers
are JLCPCB's published standard stack-ups for 1.6 mm boards, read on 24 October 2026:

| Layers | Stack-up | Source |
|---|---|---|
| 2 | copper 0.035 / FR-4 core 1.51, εr 4.5 / copper 0.035 mm | [capabilities](https://jlcpcb.com/capabilities/pcb-capabilities): FR-4 εr "4.5 (2-Layer PCB)", 1 oz outer copper. No two-layer core thickness is published there: 1.51 mm makes copper, core and masks add up to 1.6 mm |
| 4 | JLC04161H-7628: copper 0.035 / prepreg 7628 0.2104, εr 4.4 / copper 0.0152 / core 1.065, εr 4.6 / copper 0.0152 / prepreg 7628 0.2104 / copper 0.035 mm | [impedance page](https://jlcpcb.com/impedance) |
| 6 | JLC06161H-2116B: copper 0.035 / 2116 0.1164, εr 4.16 / 0.0152 / core 0.5 / 0.0152 / 1080 × 2 0.1528, εr 3.91 / 0.0152 / core 0.5 / 0.0152 / 2116 0.1164 / copper 0.035 mm | [impedance page](https://jlcpcb.com/impedance), read again 29 Oct 2026. Chosen for EoS TM4C1294, the only six-layer board: its 0.15 mm Ethernet lines 0.25 mm apart come out about 100 Ω under solder mask and 107 Ω bare (2D field solve with JLCPCB's mask model), its 0.13 mm device USB pair about 103 Ω under mask; about 94 Ω on JLC06161H-3313, well above 110 Ω on JLC06161H-7628 |

Solder mask 0.01 mm each side, green; silkscreen white; surface finish ENIG (BENCH-READY A5: ENIG
wherever a pitch is 0.5 mm or finer or a part is a QFN). The loss tangent is not published there;
KiCad writes its default, 0.02. Every JLCPCB standard multilayer stack has 0.5 oz (0.0152 mm) inner
copper: size inner supply tracks for it. A board whose pairs need controlled impedance sets
`{"impedance_controlled": True}`: KiCad then puts each dielectric's εr and loss tangent, and
`"ImpedanceControlled": true`, into the Gerber job file. A stack-up must add up to the board's thickness within JLCPCB's
±10 %. KiCad 10's Python does not wrap the board's stack-up object, so `pcb_build.py place` writes
the node into the saved file, and KiCad keeps it through every later load and save. A board of
another thickness, or for another fab, gives its own with the `stackup` option.

**Fiducials.** Every side the assembler populates gets three global fiducials, KiCad's
`Fiducial_1mm_Mask2mm` (a 1 mm copper dot in a 2 mm solder-mask opening), for the placement
machine's camera. A side counts when it has a fitted part (not DNP), in the position file, with a
surface-mount pad that gets paste (`fabrication.carries_smd_parts`, the one definition the placement
step, `metrics.py` and the tests share): EoS STM32 64's unfitted, paste-less bottom test pads do not
make it two-sided. For each corner the generator takes the 25 free spots nearest to it in its
quarter of the board, then the trio from three corners whose closest two are furthest apart, each at
least 5 mm off the line through the other two. Where fewer than three corners have room, it places
two diagonally opposite ones (the free spots nearest two opposite corners, at least 5 mm apart in x
and in y), records why in `build-report.json` (`fiducial_notes`), and the board's README must say so
(BENCH-READY A2). Each mask opening is at least 3 mm from the board edge, and a 3 mm square round each
dot is clear of every courtyard, pad, drilled hole, silkscreen text, keep-out and earlier copper on
that side: other copper stays 1.0 mm beyond the dot's edge, outside the mask opening, which meets
IPC-7351B's clear area of at least twice the mark's radius. That square is a rule area on the saved
board, so no track, via or pour enters it on the fiducial's side, and the generator's own vias keep
out of it on every layer, its tracks on that side. Fiducials are placed after the reference copper,
pre-routes and priority routes, the copper a design lays first, and before the main plane fan-out.
Fiducials are board-only footprints excluded from the BOM: not in the schematic or the BOM, but in the
placement file; the build's fabrication check fails a fiducial that is not. Where neither three nor
two fit, the build stops and names the `fiducials` option.

**Jumper shunts.** A 2.54 mm jumper header's shunts are BOM lines (BENCH-READY B3): Samtec
SNT-100-BK-G, one for each `Jumper:Jumper_2_*`/`Jumper_3_*` symbol drawn on a 2.54 mm pin header,
and the count the `shunts` option gives for a jumper header drawn with a connector symbol. Each is
a BOM-only symbol, JS1, JS2 ... (KiCad's pinless `Mechanical:Housing`, not on the board), so the
board and its parity check do not change. The BOM's Assembly column marks the line "Loose: supplied
with the board, not placed", so an assembler matching BOM lines to placement rows does not look for
it, and its description names a second source, Sullins QPC02SXGN-RC. `spec_for` refuses a `shunts`
count for anything but a 2.54 mm pin header, a jumper symbol on a header of another pitch unless
`shunts` gives it 0 (no 2.54 mm shunt fits it; the README names its shunt), and a part with pins
marked `on_board=False`.

**Board identity.** The silkscreen carries the board's name, revision and year,
"EoS Motion Wing  rev A  2026", beside its ownership line ("(c) 2026 <owner>"), on the same layer
and mirrored as it is. A design's own name line there, one ending in "rev <letter or number>", is
replaced where it stands; otherwise the line goes 2 mm above the ownership line. A design with no
ownership line is refused. The line must never sit on a pad or other silkscreen: the placement step
puts every design text down first, then checks the line against every pad of its side and every
drilled pad (0.15 mm, JLCPCB's pad-to-silkscreen minimum), the board edge (0.3 mm) and the other
silkscreen of its layer that the design's own name line did not already touch (the ownership line
below it, say), moves it up or down by up to 2 mm, then tries 0.8 mm text (the boards'
ownership-line size), and stops the build when it fits nowhere. A DRC `silk_over_copper`,
`silk_edge_clearance` or `silk_overlap` finding on the line, which KiCad grades a warning, fails the
build too. The revision is the board's `revision` (default "A"). The board file's title block
says what the schematic's does: title, date, revision, owner, copyright and licence, and for an
all-rights-reserved board whom to ask for permission.

**Metrics.** `metrics.py` reads a built board's own files (no KiCad needed) and the build writes
the result to `metrics.json` in the board folder: size and copper layers, the stack-up, parts by
side, pads, nets, track length per layer, the track widths used and where the narrowest run, vias by
size and drill, the smallest drilled hole, plated slots, pours and rule areas, the BOM's lines,
parts and MPN coverage (with the lines that have no MPN), test points and fiducials, and the
build's check counts. `python3 tools/eos_boards/metrics.py boards/eos/<name>` prints them for any
built board. A test checks each board README's Fabrication numbers (narrowest track, smallest
drill, via size and drill) against them.

## Reusing a reference design's layout exactly

Some layouts should be copied, not redrawn. Raspberry Pi's RP2350 datasheet says the core
regulator's inductor must be "placed on the layout as indicated in Figure 26", and Raspberry Pi
publishes that layout, the RP2350A Minimal Design R4, under the MIT licence.
`reference/extract_rpi_minimal.py` reads that design's `.kicad_pcb` and writes:

- `footprints/EoS_RPi_Reference.pretty`: the footprints of the parts around the chip. Their
  3D models are embedded, except the inductor's, which uses KiCad's stock 2016 inductor.
- `reference/rp2350a_minimal_r4_core.json`: where those parts sit and the copper between them,
  relative to the chip's centre, at KiCad's 1 nm resolution.

A board opts in with `reference_copper={"file": ..., "origin": <chip centre>}`. The build then
enforces three things:

- **Same footprints and pad nets.** Each reused part must use the reference footprint, and
  every pad the copper touches must be on the same net in our schematic. Otherwise the build
  stops before placing anything.
- **Fixed copper.** The copper is laid down locked, so the autorouter treats it as fixed. A board
  may list `"moved_vias": [((x, y), (new_x, new_y)), ...]` in reference coordinates to move a
  reference via off a pad. The build refuses a via the reference does not have, or a move of more
  than 0.25 mm.
- **No router interference.** The area inside the chip's pins, and each reused zone, is closed
  to the autorouter. Nets the reused copper completes on its own are taken away from it, so it
  cannot add a second path. Plane nets are not included: their fan-out vias are not locked.

`tests/unit/test_eos_boards.py` reads the built board and checks every reused footprint, track
end, via and zone corner against the reference file, in integer nanometres; a moved via is
checked at the position the board gives it. The reference file
records the SHA-256 of the design it was taken from. With `RPI_MINIMAL_PCB` pointing at
Raspberry Pi's file, a test re-extracts it and compares the two.

To regenerate the reference files from Raspberry Pi's zip:

```
python3 tools/eos_boards/reference/extract_rpi_minimal.py RPI-RP2350A-MINIMAL_R4-S1.kicad_pcb
```

## Design-file options

Most boards need only parts, nets and positions. These options cover the rest:

- `planes`: inner layers given over to one net each (ground, a supply).
- `ground_vias`: on a two-layer board, parts whose pads on a net poured on both layers get a via
  beside each such pad (never in it), as a plane net's pads do: a decoupling capacitor's ground
  end then closes its loop through the bottom pour.
- `fanout_first`: parts whose plane-net pads get their vias before the priority routes, which
  then go round them. A supply route laid first can otherwise box in a decoupling capacitor's
  via spots (EoS F280049C's C11, after VIA_PAD_GAP moved the /VDD4 route). A pad that finds no
  spot then is not tried again after the priority routes: the autorouter joins it.
- `priority_routes`: lines routed before the autorouter, in the order given. Add `"join"` to end
  a route at any copper the net already has; that suits a branch such as an ESD part's pad.
  An optional width in mm overrides the net class for that one line (a 0.15 mm neck off a
  fine-pitch Power pad, or a supply branch wider than its class: `(("U1", "1"), ("C1", "1"), 0.4)`).
  `{"via": [x, y, diameter, drill]}` (mm) pins a via the line passes through, for a gap the maze
  grid cannot land in, such as the centre of four 0402 pads. The build stops unless the via meets
  the board's via rules, the board-edge and hole-to-hole limits, every net class's clearance from
  other nets' copper on every copper layer and from their reference zones, and `VIA_PAD_GAP` from
  its own net's pads. A board's own planes are filled afterwards and are not treated as obstacles.
  Lines that start at a reference design's pin follow its escape first.
- `escape_footprints`: fine-pitch connectors whose pads keep a clear way out. The channel
  between the pad rows is closed, and each pad keeps a 1 mm corridor for its own net.
- `maze_via_cost_mm`: how much track the maze router will lay to avoid one via.
- `copper_keepouts`: rectangles with no copper on any layer, no track, via, pad or pour, kept
  on the saved board as a rule area. This is for a module's antenna cut-out.
- `router_keepouts`: rectangles `(x0, y0, x1, y1)` that Freerouting and the maze router may not
  enter, on the top layer; add `"B.Cu"` as a fifth item to keep the bottom layer clear instead,
  e.g. under a crystal whose own lines are laid on top. The pours still fill a keep-out. In a
  `"B.Cu"` keep-out the generator's own vias (fan-out, stitching) may join the bottom pour, and a
  fan-out via of any other net stays out; a top keep-out binds the routers only.
- `pour_keepouts`: rectangles `(x0, y0, x1, y1, layer)` that no pour fills on that one layer, though
  tracks and pads may enter. They stay on the saved board as rule areas, and no stitching via goes
  in one. Renesas's RL78 manual forbids a ground pattern under the X1/X2 wiring and the resonator
  (R01UH0146 Figure 5-13(d)); its RA parts want the opposite, a bottom ground (R01AN7202 §6.1.3).
- `fiducials`: `{"F": [(x, y), (x, y), (x, y)]}` (or `"B"`; or two diagonally opposite positions):
  fiducial positions for a side where the automatic choice finds no room. They are checked against
  the same rules.
- `shunts`: `{"JP1": 2}`: how many 2.54 mm shunts come with a jumper header drawn with a connector
  symbol (a 2 × 2 header taking two, say); `0` for none.
- `stackup`: changes to the fab stack-up: `{"finish": "HAL lead-free"}`, `mask_color`,
  `silk_color`, `mask_thickness`, `impedance_controlled`, or a whole `"layers"` list of copper and dielectric rows with its
  `"source"` (see Fabrication data in every board).
- `reference_copper`, `local_footprints`, `rules`, `credits`.

Local libraries:

- `footprints/` holds footprints KiCad does not ship. `footprints/generate.py` writes
  `EoS_Packages.pretty`: NXP's HLQFP-100 (SOT1570-3) with its exposed pad, from the LPC55S6x
  data sheet's land pattern; a 2 × 49 pin header; and Samtec's FTSH-105 (the 1.27 mm 10-pin Arm
  Cortex debug header) on Samtec's recommended land pattern (Rev H, 27 Aug 2019: pads 0.74 × 2.79 mm,
  6.86 mm across both rows), larger than KiCad's generic 1.27 mm SMD header's 2.4 mm pads, with the
  same pad order and orientation.
- `symbols/` holds symbols KiCad does not ship (`symbols/generate.py` writes them): the ADT7410
  temperature sensor (`EoS_Sensors`), the TM4C123GH6PM, LPC55S69JBD100 and R7FA2E1A92DFM
  (`EoS_MCU`), a 2×50
  connector for the CM5, and a flow-through TPD4EUSB30.

A board that uses either gets its own copy beside its KiCad project, with a project library
table.

## Mechanical facts from other boards

- `reference/pocketbeagle_headers.json` (`extract_pocketbeagle.py`): PocketBeagle's P1 and P2
  header pins, from BeagleBoard.org's board file (CC BY 4.0).
- `reference/cm5_carrier.json` (`extract_cm5.py`): the CM5's 200-pin list from its datasheet, and
  its connector pads and mounting holes from the CM5 footprint in Raspberry Pi's CM5 IO Board files.
- `reference/cm4_pins.json` (`extract_cm4.py`): the CM4's 200-pin list from its datasheet. Figure 4
  of the CM4 and CM5 datasheets shows the same outline, holes, connector offsets and wireless
  cut-out, so a CM4 carrier uses `cm5_carrier.json`'s pads and holes.

Only positions and pin names are taken; no file from either source is copied into this
repository. The tests check the cape's sockets and the carrier's connectors and holes against
these files, pad by pad.

## Licence

Everything in this folder is under the repository's MIT licence except the EmbeddedOS
boards' own files: their design files (`boards/eos_*.py`, `boards/owner.py`), their licence
terms (`boards/licence_terms.txt`) and the footprint library drawn for them
(`footprints/EoS_Connectors.pretty`). Those, and the boards' folders in `boards/eos/`, are
Kartikeydheer Srivastava's, all rights reserved. See
[boards/eos/README.md](../../boards/eos/README.md#licence). The generic libraries
(`symbols/`, and `footprints/EoS_Packages.pretty` with `footprints/generate.py`) stay MIT, also
when a board ships a copy of them.

A board's `licence` is `"MIT"` or `design.ALL_RIGHTS_RESERVED`. The second needs two more
fields, and a build refuses the board without them:

- `contact`: whom to ask for permission;
- `licence_terms`: the terms file, relative to this folder. The build fills in its `{year}`,
  `{owner}`, `{contact}`, `{title}`, `{revision}`, `{name}`, `{module}` (the design file it
  loaded) and `{libraries}` (the owner's footprint libraries the board uses) fields. The terms
  belong to the board's owner, not to the generator, so a board brings its own.

Each board states its designer and licence in its design file. These appear in the schematic
title block, on the back silkscreen and in the board's `LICENSE.txt`. Material reused from
another design keeps its own notice: it is listed in the board's `credits`, and its full
licence text is shipped next to the footprints (`footprints/EoS_RPi_Reference.LICENSE.txt`).
