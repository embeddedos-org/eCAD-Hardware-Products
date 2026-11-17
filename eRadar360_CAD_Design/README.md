# eRadar360 / Aegis One — CAD Design Package
**Product:** eRadar360 (consumer) / Aegis One (OEM)
**Category:** Automotive Safety — 360° Radar + Laser + V2X + AI Threat Detection
**Repository:** `eCAD-Hardware-Products/eRadar360_CAD_Design`
**Status:** Pre-production | Simulation Complete | Regulatory Documentation Complete

---

## Product Overview

The **eRadar360** (marketed as **Aegis One** for OEM channels) is a windshield-mounted automotive safety device providing 360° situational awareness through the fusion of four independent sensor modalities:

| Sensor | Technology | Coverage | Key Metric |
|--------|-----------|----------|-----------|
| Front Radar | TI AWR2944 77 GHz FMCW | 120° FOV, 0–250 m | 0.75 m range resolution |
| Rear Radar | TI AWR2944 77 GHz FMCW | 120° FOV, 0–150 m | 0.75 m range resolution |
| Laser Detection | 5× Hamamatsu G12183-010K InGaAs APD | 360° (72° spacing) | <50 ms alert latency |
| V2X | Autotalks TEKTON3, C-V2X (PC5) in the US; chipset also supports 802.11p | 1 km LOS | BSM, TIM, SPaT, MAP |

**AI Processing:** Rockchip RK3588S (6 TOPS NPU) — radar signature fingerprinting, 97% false-alert suppression  
**Co-processor:** STM32H7B3 — laser ADC, OBD-II parsing, GPS fusion  
**GNSS:** u-blox NEO-M9N (GPS/GLONASS/Galileo/BeiDou)  
**Connectivity:** Wi-Fi 6 + BT 5.3 + USB-C  
**Power:** 12V OBD-II or USB-C 5V/3A  
**Display:** 4" Samsung AMOLED (480×800, MIPI-DSI)

---

## Directory Structure

```
eRadar360_CAD_Design/
├── hardware/                   ← KiCad schematics, BOM, PCB stackup, manufacturing
│   ├── eradar360.kicad_sch     ← Main KiCad schematic
│   ├── eradar360.net           ← Netlist
│   ├── eradar360_schematic.html← HTML schematic viewer
│   ├── bom.csv                 ← Full 35-component BOM with pricing
│   ├── pick_and_place.csv      ← SMT pick-and-place coordinates
│   ├── pcb_stackup.txt         ← 8-layer PCB stackup specification
│   ├── decoupling_cap_map.csv  ← Decoupling capacitor placement map
│   ├── antenna_design.md       ← Radar and V2X antenna specifications
│   ├── power_sequencing.html   ← Power rail sequencing diagram
│   ├── product_datasheet.md    ← Full product datasheet
│   ├── manufacturing_notes.md  ← Assembly and test notes
│   └── bring_up_guide.md       ← Hardware bring-up procedure
├── firmware/                   ← Firmware source and GPS integration
│   └── gps_integration.ts      ← GPS/GNSS integration module
├── mobile/                     ← Companion mobile apps
│   ├── flutter_app/            ← Flutter (iOS + Android + macOS + Windows)
│   └── react_native_app/       ← React Native (iOS + Android)
├── regulatory/                 ← All compliance documentation
│   ├── fcc/                    ← FCC Part 15B, Part 90, Part 95 (V2X)
│   ├── nhtsa/                  ← NHTSA FMVSS, SAE J3016, ADAS guidelines
│   ├── iso26262/               ← ISO 26262 functional safety (ASIL-B)
│   ├── v2x/                    ← C-V2X certification (US); IEEE 802.11p / ITS-G5 for other regions
│   ├── cybersecurity/          ← IEC 62443, NIST CSF, UNECE WP.29
│   └── legal/                  ← Terms of Service, Privacy Policy, EULA
├── simulation/                 ← All simulation and test code
│   ├── ebuild/                 ← eBuild full-stack simulation scenarios
│   ├── unit/                   ← Algorithm unit tests
│   ├── corner_case/            ← Boundary and edge case tests
│   └── factory_test/           ← Factory test suite (--demo mode)
├── tests/                      ← Existing TypeScript test suite
└── docs/                       ← Sensor coverage matrix, architecture docs
```

---

## COGS and Pricing

| Configuration | COGS | MSRP | Margin |
|--------------|------|------|--------|
| eRadar360 Standard (radar + laser + GPS) | $285 | $699 | 59% |
| eRadar360 Pro (+ V2X, C-V2X) | $310 | $899 | 65% |
| Aegis One OEM (no display, V2X optional) | $240 | OEM pricing | — |

---

## Regulatory Clearance Requirements

| Framework | Applicability | Status |
|-----------|--------------|--------|
| FCC Part 15B (unintentional radiator) | All configurations | Documentation complete |
| FCC Part 15.253 (77 GHz radar) | Radar subsystem | Documentation complete |
| FCC Part 90 / Part 95 (V2X 5.9 GHz) | V2X configuration | Under revision — C-V2X only; limits not yet re-derived (see `regulatory/fcc/FCC_AUTHORIZATION_CHECKLIST.md`, Part 3) |
| NHTSA FMVSS 111 (rearview systems) | All configurations | Documentation complete |
| SAE J3016 (ADAS taxonomy) | All configurations | Documentation complete |
| ISO 26262 (functional safety, ASIL-B) | All configurations | Documentation complete |
| IEC 62443 (cybersecurity) | All configurations | Documentation complete |
| UNECE WP.29 R155/R156 (cybersecurity/OTA) | EU market | Documentation complete |
| FTC (marketing claims) | All configurations | Documentation complete |

---

## eBuild Simulation

```bash
# Run all 5 simulation scenarios
python3 simulation/ebuild/eradar360_ebuild_sim.py --scenarios all

# Specific scenarios
python3 simulation/ebuild/eradar360_ebuild_sim.py --scenario radar_detection
python3 simulation/ebuild/eradar360_ebuild_sim.py --scenario laser_alert
python3 simulation/ebuild/eradar360_ebuild_sim.py --scenario v2x_pipeline
python3 simulation/ebuild/eradar360_ebuild_sim.py --scenario power_budget
python3 simulation/ebuild/eradar360_ebuild_sim.py --scenario ai_regression

# Factory test (no hardware required)
python3 simulation/factory_test/eradar360_factory_test.py --demo
```

---

*Part of the EmbeddedOS eCAD-Hardware-Products ecosystem | github.com/embeddedos-org/eCAD-Hardware-Products*
