# eEdu-Kit — Specify-Stage Use-Case Spec

> **Status:** Specify stage — domain step, research-education roster step (pointer 33), 2026-11-23.
> **Source datasheet:** `future_designs/eEdu-Kit/product_datasheet.md`, concept status
> (blob `b899b881cc9073142696f23cbb0a177517e33833`, read live 2026-11-23).
> **Source BOM:** `future_designs/eEdu-Kit/bom.csv` (blob `1e6db0573ac2208168ee032c59539557a3f56da4`,
> sums $28.50 — recomputed live 2026-11-23).
> **Source business plan:** `future_designs/eEdu-Kit/business_plan.md`
> (blob `9334cbd076c96b1ca7a1079ce2a2a9e4b7d84102`, read live 2026-11-23).
> **Source sim leg:** EoSim `eosim/platforms/stm32h7/platform.yml`
> (blob `7c2570cc2a5053bb2a03a673ba8e4e0c13b2b516`, EoSim master `ebbfa818`,
> read live 2026-11-23) — display name "ST STM32H743 (Cortex-M7)", soc `STM32H743`.
> **Source flash leg:** ebuild code search, live 2026-11-23 — 0× `stm32h723` hits,
> 53× `stm32h7` hits.
> **Source register:** `~/workspace/embeddedos-daily/state.json`,
> `domains.items.research-education` (hardware use case, pipeline stage "selected",
> last researched 2026-11-10).
> **Source rule:** every factual claim in this spec comes from the live datasheet, BOM,
> business plan, EoSim platform file, ebuild search, register, or growth-backlog
> entries E1–E3 and RE1–RE4 (2026-10-31, 2026-11-10), or is labelled **PROPOSED**.
> Nothing else is asserted as a datasheet fact. This spec certifies nothing.

## 1. Product summary (datasheet)

eEdu-Kit is a classroom-ready, all-in-one STEM dev board plus a 12-week curriculum —
the research-education reference product. One donation equips one classroom of 30
students for one year. The kit runs the full EmbeddedOS kernel and the "EoS for
First-Time Builders" curriculum (E2) out of the box; the donor tier is $1K per
classroom. The design is concept-stage: curriculum draft and enclosure design are
TBD, and no schematics exist yet (`kicad/` is empty — graduation to draft is a
separate step, per the datasheet's own checklist).

| Parameter | Datasheet value |
|---|---|
| MCU | STM32H723 (Cortex-M7, 550 MHz) |
| Display | 128×64 SSD1306 OLED |
| Sensors | BNO086 IMU, DHT22 T/RH, LDR, microphone (AI tutorial-ready) |
| Actuators | Dual H-bridge motor driver (DRV8833) + servo header |
| Power | LiPo charger + 1500 mAh cell + USB-C |
| Form | Sturdy PC enclosure, snap-fit cover (kid-proofed); no-soldering build; printed lab notebook included |
| Breakout | Plenty of GPIO breakout headers, breadboard-friendly pinout |

## 2. Hardware inventory (BOM)

All rows below are BOM facts (reference, MPN, cost). Interface assignments are
**PROPOSED** — the BOM and datasheet do not state bus assignments; confirm each
against the vendor part datasheet before PCB layout.

| Ref | Part (MPN) | Role | Unit cost | Interface |
|---|---|---|---|---|
| U1 | STM32H723VGT6 (ST) | Cortex-M7 MCU, 550 MHz | $5.40 | — |
| U2 | SSD1306 OLED 128×64 | Display | $1.90 | I²C **(PROPOSED)** |
| U3 | BNO086 (CEVA/Hillcrest) | 9-axis IMU | $7.10 | I²C **(PROPOSED)** |
| U4 | DHT22 | Temperature / humidity | $2.20 | Single-wire **(PROPOSED)** |
| LDR | GL5528 | Light-dependent resistor | $0.30 | Analog → MCU ADC **(PROPOSED)** |
| MIC | INMP441 | MEMS microphone, I²S | $2.30 | I²S **(PROPOSED)** |
| U5 | DRV8833 (TI) | Dual H-bridge motor driver | $1.40 | PWM + GPIO **(PROPOSED)** |
| BAT1 | LiPo 1500 mAh + protection | Battery | $4.10 | USB-C charge in **(PROPOSED — see §11.6)** |
| ENC | PC enclosure, injection | Kid-proofed snap-fit case | $3.80 | — |
| **Total** | | | **$28.50** | "BOM target ~$25" in the datasheet is wrong — see §6.1 |

Notes:
- The BOM's most expensive line is the BNO086 IMU ($7.10, 25% of the total); the
  MCU is $5.40 (19%). No single part dominates the way the ZED-F9P dominated the
  eWatch-Pro BOM.
- The BOM names no USB-C charger IC, no crystal/oscillator, no passives, no
  connectors, no PCB, and no printed lab notebook. The $28.50 is a parts sketch,
  not a buildable BOM — see §11.6.
- The datasheet's "no FPU controversy" parenthetical on the MCU line was removed
  by this PR (it said nothing checkable — see #93); the MCU line now reads
  "STM32H723 (Cortex-M7, 550 MHz)".

## 3. The two-lesson loop (E1)

One loop, two legs. Lesson zero and lesson one are the SAME ebuild project
(`eedu-blink`, **PROPOSED** name); only the target changes. A student who blinks
an LED in the sim on Monday flashes the identical code onto hardware on Tuesday
and sees the identical blink.

### 3.1 Lesson zero — blink in EoSim (offline browser sim)

1. Teacher opens the EoSim lesson-zero page on a classroom machine. One-time
   download beforehand; the lesson itself runs with networking disabled (§7, G4).
2. The page presents the `eedu-blink` project: one source file, one LED, one
   blink rate. No board-specific code in the lesson file.
3. Student presses Run. The simulated LED blinks at 1 Hz.
4. Student changes one number (the blink period), presses Run again, and sees
   the blink change. That is the whole lesson: edit → run → observe.
5. Expected output: a blinking LED in the sim and a one-line log
   (`LED on / LED off`, **PROPOSED** shape) the teacher can point at.

**Status check (live 2026-11-23):** no lesson-zero script exists anywhere in the
org today. EoSim code search for `blink` returns only UI/skill mentions
(`skills/eosim-flash-debug/SKILL.md`, `extension/`, `mobile/`); there is no
lesson pack and no `eedu-blink` project. The datasheet's "browser-based
simulator for offline use" is an assertion, not a shipped surface (E3 carries
the packaging reality check). Lesson zero is specified here; it is built by E3.

### 3.2 Lesson one — flash the identical project on hardware

1. Student plugs the eEdu-Kit board into the classroom machine over USB-C.
2. Teacher runs the same `eedu-blink` project through ebuild one-click flash.
3. The board's LED blinks at the same 1 Hz the student saw in the sim.
4. Student changes the same one number, re-flashes, and sees the same change
   on hardware. Sim and hardware agree; the loop is closed.

**Status check (live 2026-11-23):** lesson one cannot be specified as an H723
lesson today. The sim leg models the STM32H743 and the flash leg has zero H723
hits (§8, RE3). Until RE3 decides the target contract, lesson one is written
against the H743-class target as it exists today and carries the RE3 gap flag —
it is not claimed as an H723 lesson.

## 4. Feature list the hardware needs

Source column: D = datasheet, B = BOM, R = register use case, P = PROPOSED (not in
any source; needs a decision before it becomes a requirement).

| # | Feature | Source | Hardware it exercises |
|---|---|---|---|
| F1 | Lesson-zero blink in EoSim (offline browser sim) | D, R | EoSim stm32h7 platform |
| F2 | Lesson-one flash of the identical ebuild project over USB-C | D, R | U1, USB-C |
| F3 | OLED status display (128×64) — lesson output, later lessons | D, B | U2, U1 |
| F4 | Sensor readings: IMU + T/RH + light + microphone | D, B | U3, U4, LDR, MIC, U1 |
| F5 | Motor / servo actuation (DRV8833 + servo header) | D, B | U5, U1 |
| F6 | LiPo power + USB-C charging | D, B | BAT1, U1 |
| F7 | GPIO breakout, breadboard-friendly pinout | D | U1 |
| F8 | Safe state: stop-actuation + flag on sensor fault, low battery, or link loss | P | U1 + all sensors/actuators |
| F9 | Teacher dashboard: 30 boards → one teacher view (RE4) | R | EoSim + eApps — future, not in this spec |
| F10 | Offline browser sim packaging (E3) | D, R | EoSim — packaging UNVERIFIED, see §3.1 |

F8 is **PROPOSED** only: no safe state is named in any eEdu-Kit source. It is
listed so the gap is visible — a classroom device that drives motors needs a
defined stop state before it ships to children, not as a requirement yet.
F9/F10 are dependencies of later stages, not of this spec.

## 5. Protocols and interfaces

| Link | Protocol / shape | Source |
|---|---|---|
| Student machine ↔ board | USB-C (flash via ebuild one-click flash; charging) | D, B |
| Sim ↔ lesson project | EoSim sim surface (`stm32h7` platform, H743-class today) | R, §3.1 |
| MCU ↔ OLED | I²C **(PROPOSED)** | P |
| MCU ↔ IMU | I²C **(PROPOSED)** | P |
| MCU ↔ DHT22 | Single-wire **(PROPOSED)** | P |
| MCU ↔ microphone | I²S (INMP441 is an I²S part) | B |
| MCU ↔ motor driver | PWM + GPIO **(PROPOSED)** | P |
| Teacher dashboard ↔ boards | Out of scope for this spec — RE4 | R |

Constraints carried from the register and RE3 evidence:
- The sim leg and the flash leg silently mean different chips today (H743 vs
  unnamed H723). The "sim first, flash later" claim is unmakable until RE3
  lands (§8).
- No classroom hop exists in the hardware self-check set; the sim → flash →
  classroom chain is unwalkable until E3 (lesson pack) + RE3 (H723 target) land.

## 6. RE2 first gate — decisions executed in this spec

### 6.1 BOM headline correction — CORRECTED

The datasheet's BOM target "~$25" is wrong. `bom.csv` sums to **$28.50** at
quantity 1 (recomputed live 2026-11-23: 5.40 + 1.90 + 7.10 + 2.20 + 0.30 +
2.30 + 1.40 + 4.10 + 3.80). The business plan already says "~$28" at qty 1 —
the datasheet headline is the outlier, not the BOM. **Corrected headline:
$28.50 at qty 1.** The correction is applied to the datasheet itself in this
PR (headline + "major parts only" note with the exclusions stated), which is
what closes #93. The business plan's "~$15 at 5k" is a carried estimate, not
a BOM fact — no 5k pricing exists in any source; do not quote it as costed.

### 6.2 Standards pin — PINNED

| Standard | Pin | Basis |
|---|---|---|
| IEC 61010-1 (safety, measurement/control/lab equipment) | **IEC 61010-1:2010 + AMD1:2016 + AMD2:2026** | RE2 backlog pin; AMD2:2026 is at FDIS stage — corroborated 2026-11-23 by the 2026 CDVs 66/875–878, which cite "IEC FDIS 61010-1/AMD2:2026" as the stage at publication; publication pending |
| RoHS | As listed in the business plan | Repo source |
| FCC Part 15B (USB-C only) | As listed in the business plan | Repo source |

The pin is a design decision: a classroom teaching device is measurement/control
lab equipment in classroom use, so IEC 61010-1 is the primary safety standard,
not IEC 62368-1 (the eWatch-Pro AV/ICT pin — different product class). Re-verify
the AMD2 publication status at bundle stage; until it publishes, design to the
FDIS text and track the EN adoption (CENELEC EN 61010-1:2010/FprA2:2026, Under
Approval per RE2).

### 6.3 Classroom arithmetic — TIER HOLDS

30 × $28.50 = $855.00 + $50 logistics = **$905 ≤ the $1,000 donor tier** (RE2
arithmetic, recomputed live). The $1K tier holds at qty-1 pricing with $95 of
headroom. See §9 for the full classroom sketch.

### 6.4 CERN OHL variant — OPEN, NOT DECIDED

RE2 asks for the CERN OHL variant (S/W/P); the site says bare "CERN OHL" and
no source in the repo picks a variant. Candidates:
- **CERN-OHL-S** (strongly reciprocal): derivatives share alike — keeps
  classroom forks open, matches a donor-funded open-hardware intent.
- **CERN-OHL-W** (weakly reciprocal): share-alike on the hardware design only.
- **CERN-OHL-P** (permissive): widest reuse, no share-alike.
Deciding evidence: the org's licence posture for open hardware (no precedent
found in this repo — verify against org policy) and whether donor terms require
share-alike. **Open — needs a maintainer decision; the datasheet refresh PR
(RE2 remainder) records the pick.** Do not print a variant on the kit until then.

## 7. RE1 teacher-runability gate — acceptance criteria

The gate is the spec's acceptance test. A teacher with **no embedded background**
must be able to run lesson zero unaided. "Unaided" means: no help from another
person, no internet after the one-time download, only the printed lab notebook
and the on-screen lesson. The gate is measured, not asserted:

| # | Criterion | Pass bar |
|---|---|---|
| G1 | Lesson zero, time-to-blink | Teacher goes from opening the sim page to a blinking LED in **≤ 15 minutes** wall-clock, unaided |
| G2 | Lesson zero, first-try rate | **≥ 9 of 10** pilot teachers pass G1 on their first attempt |
| G3 | Lesson one, time-to-flash | Same teacher flashes the identical project onto the board over USB-C in **≤ 15 minutes**, unaided, first-try boot (LED blinks on hardware) in **≥ 9 of 10** attempts |
| G4 | Lesson zero, offline | G1 passes with networking disabled after the one-time download |
| G5 | Teacher-training provision | A one-page teacher guide exists and a support contact (Champions-style network) is named — training is a **dependency**, not assumed |

Measurement: a timed pilot with 10 teachers who have no embedded background;
record time-to-blink, assists requested, and failures. The 15-minute bars and
the 9/10 rates are **PROPOSED** numbers in this spec — the pilot is what turns
them into evidence; if the pilot fails, the lesson (not the bar) is what gets
fixed.

Precedent (carried from RE1, 2026-11-10 — not re-read today): the micro:bit
Manchester rollout Nov 5–9, 2026 (7,740 devices, 258 kits of 30) showed that
sustained classroom use depends on teacher training, and the microbit.org
Champions network (382 educators, 51 countries) is the support-network model
G5 follows. G4 **cannot pass today**: EoSim browser-sim offline packaging is
UNVERIFIED as a shipped surface (§3.1, E3). G3 **cannot pass today**: the H723
target contract does not exist (§8, RE3). The gate is specified, not satisfied.

## 8. RE3 open gap — H723-vs-H743 target contract (NOT DECIDED)

**Decision needed:** the kit names the STM32H723; the sim leg models the
STM32H743 and the flash leg has no H723 target at all. Either the `stm32h7`
family is split into named H723 and H743 targets, or a documented nearest-class
waiver lets both legs mean H743 with the divergences written down. This spec
does **not** decide it.

**Candidates:**
- **(a) Split the family.** A named `stm32h723` target in EoSim (platform
  definition), ebuild (target + flash config), and an eos BSP — the kit's chip
  is a first-class target on both legs.
- **(b) Nearest-class waiver.** Document H743 as the stand-in for H723 on both
  legs, with a divergence note listing every H723/H743 difference that could
  affect a lesson (clock tree, flash/RAM sizes, peripheral set), and a rule
  that no lesson may touch a divergent peripheral.

**Deciding evidence (what the RE3 work must produce):**
1. ST datasheet comparison of STM32H723 vs STM32H743 (flash/RAM, clock tree,
   peripherals) — which deltas actually touch lesson zero/one (GPIO + clock +
   flash only) and which touch later lessons (sensors, timers, DMA).
2. Cost of the split: EoSim platform-model delta + ebuild target delta + eos
   BSP delta, each estimated before the work starts.
3. A hardware-in-loop check once a board exists: the same `eedu-blink` binary
   behaviour on H723 hardware vs the H743 sim.
4. The waiver's blast radius if (b) is chosen: every later lesson that touches
   a divergent peripheral reopens the decision.

Until RE3 lands, lesson zero and lesson one are H743-class lessons wearing an
H723 name — and this spec says so in writing rather than letting the two legs
silently disagree.

## 9. Classroom BOM / cost sketch (30 students)

| Line | Qty | Unit | Line cost | Source |
|---|---|---|---|---|
| eEdu-Kit board (qty-1 BOM) | 30 | $28.50 | $855.00 | B (§2) |
| Logistics (per-classroom delivery) | 1 | $50 | $50.00 | Business plan (carried estimate) |
| Spare kits (2, for breakage) | 2 | $28.50 | $57.00 | **PROPOSED** |
| **Classroom total** | | | **$962.00** | **≤ $1,000 tier, $38 headroom** |
| Without spares | | | $905.00 | §6.3 |
| At 5k volume (30 × ~$15 + $50) | | | ~$500 | Business-plan estimate, UNVERIFIED |

Not in the sketch (unknown — do not assume): printed lab-notebook printing cost
(BOM lists no notebook line), teacher-kit cost, USB-C cables and chargers
(are they in the $28.50? No — the BOM has no cable line), spares beyond 2,
and the $25K one-time curriculum cost, which is not per-classroom and is not
amortised here. Each unknown is a line the datasheet refresh PR must price or
explicitly exclude.

## 10. Standards and safety notes (classroom device)

- **Primary safety standard:** IEC 61010-1:2010 + AMD1:2016 + AMD2:2026 (FDIS)
  (§6.2). The kit is used by minors in a classroom; the enclosure, LiPo, and
  USB-C charging are the safety-critical items.
- **Enclosure:** PC snap-fit cover, kid-proofed per the datasheet — no exposed
  mains, no user-serviceable LiPo access without a tool (**PROPOSED** rule:
  battery compartment is tool-secured, not finger-openable).
- **LiPo:** 1500 mAh cell with protection (BOM). Charging is USB-C only; the
  charger IC is unselected (§11.6). Transport of 30 cells: UN 38.3 test
  compliance for lithium-battery shipment is a **PROPOSED** check — verify
  against the cell vendor's UN 38.3 summary before any bulk classroom shipment;
  do not claim it.
- **Battery Regulation, Art. 11 (removability / replaceability):** applies
  Feb 18, 2027 (carried from the eWatch-Pro spec pattern — re-verify against
  the Regulation text at bundle stage). Position: the sealed-in LiPo in a
  kid-proofed enclosure faces the same removability question as the watch;
  **OPEN** — whether a tool-secured (not sealed) compartment satisfies Art. 11
  needs a read; do not claim compliance either way.
- **EMC / radio:** no radio on the kit (no BLE/Wi-Fi in the BOM) — FCC Part 15B
  (unintentional radiator, USB-C only) per the business plan. If a radio is
  added in a later lesson, the EMC position reopens.
- **No-soldering build:** per the datasheet — the kit must be assemblable and
  repairable by a teacher with no soldering. Any part that requires soldering
  to replace is a spec violation.
- **Data:** the kit collects no student-identifiable data. RE4's teacher
  dashboard records lesson completion only (completion-not-surveillance is the
  hard rule, carried from RE4) — no names, no keystroke data, no location.
- This spec certifies nothing: IEC 61010-1, RoHS, FCC, and UN 38.3 positions
  are design targets and checks, not compliance claims.

## 11. Open decisions and gaps

1. **RE3 (the named open gap):** H723-vs-H743 target contract — split vs waiver
   (§8). Blocks lesson one as an H723 lesson and blocks G3.
2. **E3:** EoSim offline browser-sim lesson pack — packaging reality check +
   lesson-zero script. Blocks G4 and lesson zero as a shippable lesson.
3. **CERN OHL variant** (§6.4) — maintainer decision; blocks any licence
   marking on the kit or datasheet.
4. **Charger IC selection:** the BOM has no charger IC for the USB-C LiPo
   charge path. Select one (with its cost) or the $28.50 is incomplete.
5. **BOM completion:** crystal/oscillator, passives, connectors, PCB, USB-C
   cable, printed lab notebook — none are costed. The $28.50 is a parts sketch.
6. **Enclosure design:** snap-fit PC cover is TBD per the datasheet; no CAD exists.
7. **Curriculum:** 12-week "EoS for First-Time Builders" spine (E2) is an outline
   only; full lessons are size L and explicitly not this spec. The datasheet's
   "12-week curriculum" tagline vs the site's "curriculum draft TBD" is the
   E2 evidence gap.
8. **Battery Regulation Art. 11:** tool-secured vs sealed compartment — legal
   read needed (§10).
9. **UN 38.3:** verify the cell's transport-test summary before bulk shipment (§10).
10. **RE2 remainder — EXECUTED in this PR, not a follow-up:** the datasheet
    headline is corrected to $28.50 (qty 1, major parts only) with the
    exclusions stated, the AMD2 pin is added, and the business plan's BOM
    lines carry the same qualifier — this closes #93. The CERN OHL pick
    (§6.4) is still open and is not printed anywhere until decided.
11. **G1–G5 pilot:** the 15-minute bars and 9/10 rates are PROPOSED until a
    10-teacher pilot measures them (§7).
12. **RE4:** teacher-dashboard visibility shape — depends on E1/E3 + RE1; not
    in this spec.

## 12. Traceability

- Growth backlog **E1** (eEdu-Kit onboarding spec, size S–M, home eCAD + ebuild +
  EoSim) — this spec IS the E1 deliverable: lesson zero + lesson one as one loop,
  RE1 gate as acceptance criteria, RE2 as input, RE3 as the named open gap.
  Seam 5, Ready 3. Seam + journey stage: Stage 1 (choosing hardware — a
  classroom kit that works offline on lesson zero) + Stage 2 (starting).
- Growth backlog **E2** ("EoS for First-Time Builders" curriculum spine, size S
  outline) — lessons zero/one anchor the arc; E2 is the next dependency, not
  part of this spec.
- Growth backlog **E3** (EoSim offline browser-sim lesson pack, size S + M) —
  builds the lesson-zero script + packaging this spec specifies; gap 2.
- Growth backlog **RE1** (teacher-runability gate, size S) — executed as the
  acceptance criteria in §7; the gate is specified, not satisfied.
- Queue item **RE2** (datasheet refresh + AMD2 pin + BOM-headline correction,
  size S) — first gate executed in §6 and the refresh itself executed in this
  PR (datasheet headline + standards pin; business-plan qualifiers), closing
  #93; only the CERN OHL pick (§6.4) remains open.
- Growth backlog **RE3** (H723 target contract, size M) — the named open gap,
  §8; not decided here.
- Growth backlog **RE4** (teacher-dashboard visibility, size M) — future; gap 12.
- Pipeline stage after this step: research-education moves selected →
  **specified** (register update is the loop's bookkeeping, not this PR).

---

*Signature: av_mando*
