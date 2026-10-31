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
   Finally writes a Specctra DSN for the router.
3. **Routing**. Freerouting, headless. The router is given 0.01 mm more clearance than the board's
   rules, so its grid rounding never reaches DRC.
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

   Up to six rounds.
6. **Outputs**. Gerbers and drill files (fabrication layers only), pick-and-place, BOM,
   STEP, schematic PDF and SVG, renders, `LICENSE.txt` and `build-report.json` with the ERC and
   DRC counts.

Outputs are written only when every check passes: 0 ERC violations, 0 DRC errors, 0
unconnected items and 0 parity problems. A failed build stops before step 6: the previous
fabrication outputs, `LICENSE.txt` and `build-report.json` stay as they were, while `hardware/`,
`erc.json` and `drc.json` hold the failed attempt, so it can be inspected. Rebuild until it
passes before committing a board.

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
  fine-pitch Power pad). `{"via": [x, y, diameter, drill]}` (mm) pins a via the line passes
  through, for a gap the maze grid cannot land in, such as the centre of four 0402 pads. The build
  stops unless the via meets the board's via rules, the board-edge and hole-to-hole limits, every
  net class's clearance, and `VIA_PAD_GAP` from its own net's pads. Lines that start at a
  reference design's pin follow its escape first.
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
- `reference_copper`, `local_footprints`, `rules`, `credits`.

Local libraries:

- `footprints/` holds footprints KiCad does not ship. `footprints/generate.py` writes
  `EoS_Packages.pretty`: NXP's HLQFP-100 (SOT1570-3) with its exposed pad, from the LPC55S6x
  data sheet's land pattern.
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
