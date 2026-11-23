# eWatch-Pro — Specify-Stage Use-Case Spec

> **Status:** Specify stage — domain step, consumer-electronics roster step (pointer 30), 2026-11-22.
> **Source datasheet:** `eConsumer_CAD_Design/personal_devices/product_datasheet.md`,
> v1.0, 2026-06-03, status Design Phase (blob `aeb060763329fa20e9814cc294754ce4bc34b9b9`,
> read live 2026-11-22).
> **Source BOM:** `eConsumer_CAD_Design/personal_devices/bom.csv` (total $110.75, read live 2026-11-22).
> **Source sim:** `eConsumer_CAD_Design/personal_devices/simulation/power_budget_sim.py`
> (run live 2026-11-22 — see §6).
> **Source register:** `~/workspace/embeddedos-daily/state.json`,
> `domains.items.consumer-electronics` (hardware use case, pipeline stage "selected",
> last researched 2026-11-09).
> **Source rule:** every factual claim in this spec comes from the live datasheet, BOM, sim,
> register, or growth-backlog entries CE1–CE3 (2026-11-09), or is labelled **PROPOSED**.
> Nothing else is asserted as a datasheet fact. This spec certifies nothing.

## 1. Product summary (datasheet)

eWatch-Pro is a wrist-worn wellness companion smart watch — the consumer-electronics
reference product. Datasheet family table: ECG, SpO2, GPS as key sensors; 5-day battery
life (typical). The other family members in the same datasheet (eTracker-Fit, eGlasses-AR,
eSensor-Portable, eComm-Device) are out of scope for this spec.

| Parameter | Datasheet value |
|---|---|
| MCU | Nordic nRF5340 (dual-core BLE SoC) |
| Display | 1.4" AMOLED 454×454 |
| Sensors | ECG (AD8232), SpO2 (MAX86141), GPS (ZED-F9P) |
| Battery | 3.7 V LiPo, 420 mAh |
| Battery life | 5 days (typical), 2 days (GPS always-on) |
| Water resistance | 5 ATM (50 m) |

## 2. Hardware inventory — sensors, actuators, supporting parts (BOM)

All rows below are BOM facts (reference, MPN, cost). Interface assignments are **PROPOSED**
— the BOM and datasheet do not state bus assignments; confirm each against the vendor
part datasheet before PCB layout.

| Ref | Part (MPN) | Role | Unit cost | Interface |
|---|---|---|---|---|
| U1 | nRF5340-QKAA-R7 (Nordic) | Dual-core BLE 5.3 SoC, application + network core | $6.50 | — |
| U2 | AD8232ACPZ-R7 (Analog Devices) | Single-lead ECG analogue front end | $4.50 | Analog out → MCU ADC **(PROPOSED)** |
| U3 | MAX86141EFF+T (Maxim) | Optical PPG + SpO2 AFE | $4.20 | I²C/SPI **(PROPOSED)** |
| U4 | ZED-F9P (u-blox) | RTK GPS — marked "(optional)" in the BOM | $75.00 | UART **(PROPOSED)** — see §5.1 decision |
| U5 | BMI270 (Bosch Sensortec) | 6-axis IMU (accel + gyro) | $1.85 | I²C/SPI **(PROPOSED)** |
| U6 | MAX17205G+T (Maxim) | Fuel-gauge IC | $2.20 | I²C **(PROPOSED)** |
| U7 | BQ25895RTWR (TI) | USB-C battery charger | $2.40 | USB-C in, I²C control **(PROPOSED)** |
| U8 | ATECC608B-MAHDA-T (Microchip) | Crypto co-processor / secure element | $0.95 | I²C **(PROPOSED)** |
| U9 | W25Q32JVSSIQ (Winbond) | 32 Mb SPI flash | $0.65 | SPI **(PROPOSED)** |
| U10 | AMS129 (BOE) | 1.4-inch AMOLED display, 454×454 | $12.00 | MIPI/DSI or SPI **(PROPOSED — bus not stated anywhere)** |
| C1 | GRM155R71C104KA88D ×20 | 100 nF decoupling | $0.40 | — |
| R1 | RC0402FR-0710KL ×10 | 10 kΩ resistor | $0.10 | — |
| **Total** | | | **$110.75** | "Approximate BOM cost" (BOM) |

Notes:
- The datasheet's sensor list omits the BMI270 IMU, the fuel gauge, charger, secure
  element and flash — all are BOM facts, not datasheet facts.
- The datasheet names no haptic actuator, microphone, speaker, barometer, ambient-light
  or temperature sensor. Any of those is **PROPOSED** and not in this spec's hardware list.
- The register's hardware use case adds: BLE link to a phone gateway peer as the
  visibility path; ATECC608B for identity/keys.

## 3. Feature list the hardware needs

Source column: D = datasheet, B = BOM, R = register use case, P = PROPOSED (not in any
source; needs a decision before it becomes a requirement).

| # | Feature | Source | Hardware it exercises |
|---|---|---|---|
| F1 | Watch face / time display on 454×454 AMOLED | D | U10, U1 |
| F2 | Single-lead ECG measurement, 30 s spot checks (hourly cadence per CE3) | D, R | U2, U1 |
| F3 | SpO2 / PPG measurement, 15 s spot checks (per CE3) | D, R | U3, U1 |
| F4 | Step / activity tracking from 6-axis IMU | B, R | U5, U1 |
| F5 | GPS workout tracking, duty-cycled (not always-on — see §5.1, §6) | D, R | U4, U1 |
| F6 | BLE link to phone gateway peer; sync of ECG/SpO2/activity/GPS records | R | U1 |
| F7 | Battery state reporting + USB-C charging | B | U6, U7, U1 |
| F8 | Secure identity / keys for the BLE link and stored records | B, R | U8, U1 |
| F9 | On-watch record storage + OTA update staging | B | U9, U1 |
| F10 | Safe state: stop-streaming-and-flag on sensor fault, stale data, or link loss | R (PROPOSED state) | U1 + all sensors |
| F11 | Notifications from the phone gateway | P | U1, U10 |
| F12 | Sleep tracking (IMU + PPG cadence) | P | U5, U3, U1 |
| F13 | Haptic feedback | P — no actuator in BOM | (no part selected) |

F11–F13 are **PROPOSED** only: they appear in the EoSim wearable scenario set (CE1
evidence, read 2026-11-09) but in no eWatch-Pro source. They are listed so the gap is
visible, not as requirements.

## 4. Protocols and interfaces

| Link | Protocol / shape | Source |
|---|---|---|
| Watch ↔ phone gateway | BLE 5.3 (nRF5340 is a "Dual-core BLE 5.3 SoC" per BOM) | B |
| Watch ↔ charger / host | USB-C (BQ25895 charger) | B |
| MCU ↔ flash | SPI (W25Q32JVSSIQ is an SPI flash) | B |
| MCU ↔ sensors / secure element / fuel gauge | Per-part buses — **PROPOSED**, see §2 table | P |
| GPS output | NMEA sentence stream **(PROPOSED — CE1 sim shape; not in any hardware source)** | P |
| Phone gateway ↔ cloud | Out of scope for this spec — phone-side, not watch hardware | — |

Constraints carried from the register and CE1 evidence:
- eos BLE GATT is declarations-only today (tracked under eNet #9 prerequisite 1); the
  real-hardware BLE commissioning/sync path is blocked on eos GATT + nRF52 BSP. The
  sim path (CE1/CE3) proceeds first.
- No watch → phone → cloud chain is walkable in the hardware self-check set until
  CE1/CE3 land (register self-check note).

## 5. CE2 first gate — decisions executed in this spec

### 5.1 GPS module decision — DECIDED

**ZED-F9P stays as an OPTIONAL RTK variant; the base configuration uses an M10-class
receiver (PROPOSED, MPN to be selected).**

Rationale (all figures from live sources):
- ZED-F9P is $75.00 of a $110.75 BOM — **67.7%** of the total — and the BOM itself
  marks it "(optional)".
- The sim's GPS-active draw is 135 mA (§6); RTK-grade positioning is not needed for
  wellness workout tracks (F5).
- Removing the ZED-F9P from the base BOM leaves $35.75 before the M10-class part;
  the M10-class part price is **unknown — not stated in any source, do not assume**.
- Open: select the M10-class MPN, confirm its UART/NMEA shape and duty-cycled draw,
  and re-price the base BOM. RTK variant keeps the ZED-F9P line unchanged.

### 5.2 BOM-vs-sim reconciliation — DISCREPANCIES RECORDED, NOT RESOLVED

Sim run live 2026-11-22 (`power_budget_sim.py`, 420 mAh @ 3.7 V):

| Sim mode | Draw |
|---|---|
| Deep sleep (RTC + accel) | 0.01 mA |
| Watch face update | 5.00 mA |
| BLE connected (no data) | 3.00 mA |
| BLE data transfer | 10.00 mA |
| ECG measurement (30 s) | 8.00 mA |
| SpO2 measurement (15 s) | 12.00 mA |
| GPS active | 135.00 mA |
| AMOLED display (50% brightness) | 30.00 mA |
| **Sim "typical use" average** | **1.696 mA → 10.3 days** |

- **D1 — runtime gap:** the sim computes **10.3 days** typical; the datasheet claims
  **5 days**. The sim's "typical use" model weights only deep sleep (90%), display
  (5%), BLE-connected (4%) and hourly 30 s ECG — it omits SpO2, GPS duty cycle, BLE
  data transfer, watch-face updates and IMU streaming. The sim is optimistic; the
  datasheet's 5-day figure is the conservative claim until the sim model is completed.
  Resolution: extend the sim duty-cycle model (CE1 follow-up), then re-derive.
- **D2 — GPS always-on gap:** at the sim's 135 mA GPS-active draw, always-on GPS gives
  420 mAh / 135 mA ≈ **3.1 hours**, not the datasheet's **2 days**. The datasheet's
  "2 days (GPS always-on)" is inconsistent with the sim figure and cannot stand as
  written. Resolution: either the GPS figure is a duty-cycled average (define the duty
  cycle) or the datasheet claim needs correction. Open — blocks any GPS battery claim.

### 5.3 Standards edition pins — PINNED (PROPOSED pins, externally grounded)

The datasheet pins no standards edition. The repo's `eConsumer_CAD_Design/docs/
regulatory_path.md` lists only "FCC Part 15, BT SIG" for the smart watch. Pins below
are design decisions, grounded in first-party/current sources read 2026-11-22:

| Standard | Pin | Basis |
|---|---|---|
| IEC 62368-1 (product safety, AV/ICT) | **IEC 62368-1:2023, Ed. 4** (EN IEC 62368-1:2024/A11:2024 in Europe) | 4th edition published 2023-05-26 (CSA/UL guides); EN edition published Apr 2024, DOW Feb 15, 2027 |
| EN 55032 (EMC emissions, multimedia) | **EN 55032:2015+A1:2020+A11:2020** | Harmonised under EMC Directive 2014/30/EU per Implementing Decision (EU) 2020/1630; prEN IEC 55032:2025 in progress — watch item |
| FCC Part 15 (radio) | As listed in regulatory_path.md | Repo source |
| Bluetooth SIG | As listed in regulatory_path.md | Repo source |

Caveat (honest): only EN 62368-1:2014 (2nd edition) is currently cited in the EU
Official Journal under the Low-Voltage Directive, so the 4th edition does not yet give
presumption of conformity for CE marking — design to Ed. 4, track OJEU citation.

### 5.4 CRA + Battery Regulation positions — RECORDED (per CE2 backlog research, 2026-11-09)

- **Cyber Resilience Act, Reg. (EU) 2024/2847:** smart watches are named in scope.
  Vulnerability reporting live since Sep 11, 2026; main obligations apply Dec 11, 2027.
  Position: eWatch-Pro must carry a vulnerability-handling and update path (OTA staging
  on U9, secure identity on U8) before the Dec 11, 2027 date. Re-verify dates against
  the Regulation text at bundle stage — these dates are carried from the 2026-11-09
  backlog entry, not re-read today.
- **Battery Regulation, Art. 11 (removability / replaceability):** applies Feb 18, 2027.
  Position: the sealed 420 mAh LiPo in a 5 ATM watch faces the Art. 11
  removability-vs-sealing question. **OPEN: the 5 ATM water-exposure derogation
  question is undecided** — whether a sealed 5 ATM design qualifies for derogation
  needs a legal read; do not claim compliance either way.

### 5.5 Claim firewall (DH1 pattern, carried from the register) — STATED

eWatch-Pro outputs are **wellness outputs only**:
- ECG spot checks and SpO2 readings are wellness indicators, not diagnostic results.
- **No disease claim. No atrial-fibrillation (AFib) claim. No diagnostic claim.**
- No wording in any datasheet, spec, UI string, or marketing copy may imply detection,
  diagnosis, monitoring, or treatment of any condition.
- This firewall applies to the sibling wearable HEALTH-KEY ULTRA as well (register
  cross-link) and to the EoSim wearable scenarios (CE1/CE3).

## 6. Power budget (sim outputs, not datasheet claims)

From the live sim run (§5.2 table). The datasheet's 5-day / 2-day-GPS claims are the
product claims; the sim's 10.3-day typical figure is a model output that overstates
runtime (D1). GPS always-on at 135 mA is ≈ 3.1 h (D2). No power figure in this spec
overrides the datasheet claims.

## 7. Open decisions and gaps

1. M10-class GPS MPN selection + re-priced base BOM (§5.1).
2. D1: complete the sim duty-cycle model (SpO2, GPS duty cycle, BLE transfer,
   watch-face updates) and re-derive typical runtime.
3. D2: define the GPS duty cycle or correct the datasheet's "2 days (GPS always-on)".
4. Battery Regulation Art. 11: 5 ATM sealed-LiPo derogation — legal read needed (§5.4).
5. U10 display bus (MIPI/DSI vs SPI) — not stated anywhere; confirm against BOE AMS129.
6. Sensor bus assignments (§2) — confirm each against vendor part datasheets.
7. F11–F13 (notifications, sleep, haptic) — decide in/out; haptic needs a part if in.
8. CRA/Battery dates — re-verify against Regulation texts at bundle stage (§5.4).
9. The datasheet itself is still v1.0 Design Phase (2026-06-03) and lists no standards
   editions; this spec does not amend the datasheet — a datasheet refresh PR (CE2
   remainder) should fold §5.1–§5.4 back into `product_datasheet.md` + `bom.csv`.

## 8. Traceability

- Growth backlog CE1 (EoSim wearable ECG + GPS peripherals + 454×454 display, size S,
  home EoSim) — this spec's F2/F5 and §4 GPS shape are the hardware side CE1 simulates
  against; CE1 is the next dependency, not part of this spec.
- Growth backlog CE3 (EoSim "watch-day" scenario, size S, depends on CE1) — exercises
  F2/F3/F5/F6 and the F10 safe state in sim.
- CE2 first gate is executed by this spec (§5); the CE2 remainder is gap 9 (datasheet
  + BOM refresh).
- Pipeline stage after this step: consumer-electronics moves selected → **specified**
  (register update is the loop's bookkeeping, not this PR).

---

*Signature: av_mando*
