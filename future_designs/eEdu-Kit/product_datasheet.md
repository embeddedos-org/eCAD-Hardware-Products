# 🎓 eEdu-Kit — Concept Datasheet

> **Status:** Concept (curriculum draft + enclosure design TBD)
> **Category:** Robotics, Education, Research
> **EmbeddedOS components:** eos (kernel), eApps (example apps preloaded), ebuild (one-click flash), EoSim (browser-based simulator for offline use)

## Tagline

Classroom-ready all-in-one STEM dev board + 12-week curriculum.

## Why this exists (donor pitch)

Imported $80 dev boards lock low-income classrooms out of embedded-systems education. eEdu-Kit is a sturdy, repairable, ship-in-one-bag dev board that runs the full EmbeddedOS kernel and the 12-week “EoS for First-Time Builders” curriculum out of the box. One donation → one classroom × one year × 30 students.

## Target users

Secondary-school STEM teachers, rural-school computer-science programs, after-school clubs, refugee-education programs.

## Suggested donor tier

$1 K — equip one classroom of 30 with kits and curriculum.

## Hardware sketch

- STM32H723 (Cortex-M7, 550 MHz)
- 128×64 SSD1306 OLED display
- BNO086 IMU + DHT22 T/RH + LDR + microphone (AI tutorial-ready)
- Dual H-bridge motor driver (DRV8833) + servo header
- LiPo charger + 1500 mAh cell + USB-C
- Plenty of GPIO breakout headers + breadboard-friendly pinout
- Sturdy PC enclosure with snap-fit cover (kid-proofed)
- No-soldering build; printed lab notebook included

## EmbeddedOS stack

- eos (kernel)
- eApps (example apps preloaded)
- ebuild (one-click flash)
- EoSim (browser-based simulator for offline use)

## BOM target

$28.50 at quantity 1 — major parts only (see [`bom.csv`](bom.csv)). The total
excludes the PCB, power (charger IC, regulator), connectors, passives,
crystal/oscillator, USB-C cable, and printed lab notebook; see
[`eedu-kit-spec.md`](eedu-kit-spec.md) §2 and §11.5. At 5k volume the business
plan estimates ~$15 (estimate, not costed).

> Full BOM placeholder lives at [`bom.csv`](bom.csv). Schematics will be
> added under `kicad/` when the design graduates from concept to draft.

## Standards (design target)

IEC 61010-1:2010 + AMD1:2016 + AMD2:2026 (FDIS, publication pending) — see
[`eedu-kit-spec.md`](eedu-kit-spec.md) §6.2. RoHS; FCC Part 15B (USB-C only).
This datasheet certifies nothing.

## Status

This page is a **concept-stage placeholder**. It exists so that donors,
contributors, and curators can browse the design as a real GitHub URL
before any silicon is committed.

To take this design to draft:

1. Open an issue on
   [embeddedos-org/eCAD-Hardware-Products](https://github.com/embeddedos-org/eCAD-Hardware-Products/issues/new)
   titled `[future_designs/eEdu-Kit] graduate to draft`.
2. Stand up `kicad/eedu_kit_schematic.kicad_sch` and start filling in
   the BOM at [`bom.csv`](bom.csv).
3. Cross-reference the eFab manifest if a curated stack profile makes
   sense (e.g. `eai-edge` for designs that lean on ENI + EIPC + eAI).

See the org-wide guide at
[`embeddedos-org/.github/CONTRIBUTING.md`](https://github.com/embeddedos-org/.github/blob/main/CONTRIBUTING.md).
