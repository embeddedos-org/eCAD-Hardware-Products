# eCAD Hardware Products

[![CI](https://github.com/embeddedos-org/eCAD-Hardware-Products/actions/workflows/ci.yml/badge.svg)](https://github.com/embeddedos-org/eCAD-Hardware-Products/actions/workflows/ci.yml)
[![CodeQL](https://github.com/embeddedos-org/eCAD-Hardware-Products/actions/workflows/codeql.yml/badge.svg)](https://github.com/embeddedos-org/eCAD-Hardware-Products/actions/workflows/codeql.yml)
[![Scorecard](https://github.com/embeddedos-org/eCAD-Hardware-Products/actions/workflows/scorecard.yml/badge.svg)](https://github.com/embeddedos-org/eCAD-Hardware-Products/actions/workflows/scorecard.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Hardware / PCB CAD design collection for the **EmbeddedOS (EoS)** ecosystem.
The repository organizes hardware product designs by application domain. Each
domain holds one or more product lines, and each product line typically carries
a product datasheet, a bill of materials (`bom.csv`), power-budget simulation
scripts, and placeholder directories for PCB and mechanical CAD artifacts.
Several product lines also include KiCad schematics (`*.kicad_sch`).

> Status varies by design. Directories are at different maturity levels (many
> "Design" / "Pre-production"); PCB and CAD folders often contain `.gitkeep`
> placeholders rather than finished layouts. Check each design's own `README.md`
> and `docs/` for its current state.

## Domains

The repository contains **16** domain design collections:

| Domain | Focus |
|---|---|
| `eAerospace_CAD_Design` | Aircraft components, avionics, UAV/drone systems, space systems |
| `eConsumer_CAD_Design` | Smart home devices, personal wearables, AR/smart devices |
| `eCybersecurity_CAD_Design` | Security appliances and physical security systems |
| `eDefense_CAD_Design` | Surveillance, tactical communications, protection equipment |
| `eElectronics_CAD_Design` | PCBs, embedded controllers, RF modules, FPGAs, AI accelerators |
| `eEnergy_CAD_Design` | Battery products, renewable energy systems, power electronics |
| `eHealth365_CAD_Design` | Two-device health monitoring system (smart patch / smart ring) |
| `eIndustrial_CAD_Design` | Sensors, industrial electronics, infrastructure equipment |
| `eMedical_CAD_Design` | Diagnostic, surgical, patient-care, laboratory equipment |
| `eMining_CAD_Design` | Autonomous mining/construction equipment, industrial safety systems |
| `ePAM_CAD_Design` | Personal air/ground mobility — solar-hybrid transport, 4-product line |
| `eRadar360_CAD_Design` | 360° automotive safety radar + laser + V2X + AI threat detection |
| `eRobotics_CAD_Design` | Industrial robots, autonomous systems, robot components |
| `eSmartCity_CAD_Design` | Urban infrastructure, utilities, telecommunications |
| `eTransport_CAD_Design` | Automotive electronics, rail systems, maritime systems |
| `eosHealth_CAD_Design` | Four-device wearable health platform |

Plus:

- `future_designs/` — early/prospective concepts (e.g. `eBCI-Lite`)
- `docs/` — repository-level documentation

## Typical design layout

Most domains follow a common structure, for example:

```
eAerospace_CAD_Design/
  README.md
  docs/                      business_plan.md, regulatory_path.md
  ebuild_simulation/         eBuild simulation notes
  <product_line>/
    product_datasheet.md
    bom.csv
    simulation/power_budget_sim.py
    hardware/
      pcb/  cad/  antenna/   (artifact folders; often .gitkeep placeholders)
```

Artifact formats present in the repo include Markdown datasheets, CSV BOMs,
Python simulation scripts, and KiCad schematics (`*.kicad_sch`). Some product
lines also include TypeScript/Dart companion app sources and 3D-model notes.

## Simulations

Power-budget simulations are plain Python scripts, runnable per product line:

```bash
cd eAerospace_CAD_Design/<product_line>/simulation/
python3 power_budget_sim.py
```

Design docs reference the [EoSim](https://github.com/embeddedos-org/EoSim)
digital-twin platform for hardware-in-the-loop testing. Running one script alone
does not establish that a product is validated.

## Evidence-backed product validation

The committed `tools/catalog/product_inventory.json` is the complete product
execution set. The v1 contract schemas and policy requirements are documented in
`docs/hardware-validation-contract-v1.md`.

Discover inventory drift and inspect local tool capabilities:

```bash
python3 tools/validate_products.py discover
python3 tools/validate_products.py capabilities
```

Execute V0-V4 for every inventoried product and write hash-bound receipts:

```bash
python3 tools/validate_products.py validate \
  --all \
  --output /tmp/ecad-validation \
  --mode evidence
python3 tools/validate_products.py verify-bundle \
  /tmp/ecad-validation/bundle.json
```

`--mode evidence` succeeds when the selected inventory was executed and valid
receipts were written. Individual products may still be honestly `FAIL`,
`BLOCKED`, `INCONCLUSIVE`, or `NOT_RUN`. Use `--mode gate` for a release check;
it succeeds only when every selected product has real `PASS` evidence for V0,
V1, V2, V3, and V4. Historical baseline entries never waive a failed or missing
requirement.

## License

MIT — see [LICENSE](LICENSE).
