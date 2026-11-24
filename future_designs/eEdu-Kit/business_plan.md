# 🎓 eEdu-Kit — Business / Donor Plan (concept)

> **Status:** Concept (curriculum draft + enclosure design TBD)
> **Donor tier:** $1 K — equip one classroom of 30 with kits and curriculum.

## What a donor funds

Imported $80 dev boards lock low-income classrooms out of embedded-systems education. eEdu-Kit is a sturdy, repairable, ship-in-one-bag dev board that runs the full EmbeddedOS kernel and the 12-week “EoS for First-Time Builders” curriculum out of the box. One donation → one classroom × one year × 30 students.

## Cost outline (placeholder)

| Line | Estimate |
|---|---|
| BOM (qty 1, major parts only) | $28.50 |
| BOM (qty 5k, major parts only) | ~$15 (estimate, not costed) |
| Curriculum (12-week, video + workbook) | $25 K one-time |
| Logistics (per classroom delivery) | ~$50/class |

BOM figures are major parts only — they exclude the PCB, power (charger IC,
regulator), connectors, passives, crystal/oscillator, USB-C cable, and printed
lab notebook (see `eedu-kit-spec.md` §2, §9). Classroom arithmetic at qty-1
pricing: 30 × $28.50 + $50 = $905, within the $1K tier.

## Regulatory path

RoHS, FCC Part 15B (USB-C only).

## Go-to-market / distribution

Donate-a-classroom model; ship-and-train via local NGO partners; curriculum localised per language.

## EmbeddedOS components leveraged

- eos (kernel)
- eApps (example apps preloaded)
- ebuild (one-click flash)
- EoSim (browser-based simulator for offline use)

> All numbers are **concept-stage estimates**. They will be sharpened when
> this design graduates from `future_designs/` to its own top-level
> directory under [`eCAD-Hardware-Products`](https://github.com/embeddedos-org/eCAD-Hardware-Products).
