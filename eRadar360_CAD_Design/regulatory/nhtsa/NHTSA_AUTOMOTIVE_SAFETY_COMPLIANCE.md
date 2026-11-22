# eRadar360 — NHTSA, SAE J3016, and Automotive Safety Compliance
**Document:** EOS-RADAR-NHTSA-001 | **Revision:** 1.0 | **Date:** 2026-06-03

---

## 1. Product Classification and Regulatory Scope

The eRadar360 is an **aftermarket automotive safety device** — a consumer product that attaches to a vehicle windshield via suction mount and connects to the OBD-II port. It does not integrate with the vehicle's safety-critical systems (brakes, steering, airbags) and does not provide any automated vehicle control. This classification has significant regulatory implications:

| Classification | Applies? | Rationale |
|---------------|---------|-----------|
| FMVSS (Federal Motor Vehicle Safety Standards) | Partial | FMVSS 111 (rearview) may apply if marketed as backup camera aid |
| NHTSA ADAS guidelines | Advisory | Non-binding guidelines for aftermarket ADAS |
| SAE J3016 (automation levels) | Informational | Device is Level 0 (driver information only) |
| ISO 26262 (functional safety) | Recommended | Not legally required for aftermarket, but best practice |
| UNECE WP.29 R155/R156 | EU market only | Cybersecurity and OTA update regulations |
| FTC (marketing claims) | ✅ Required | All performance claims must be substantiated |

---

## 2. SAE J3016 Automation Level Classification

Per SAE J3016 Rev. 2021, the eRadar360 operates at **Level 0 — No Driving Automation**:

> "The driving automation system performs no part of the dynamic driving task. The driver performs the entire DDT, even when enhanced by active safety systems."

The eRadar360 provides **driver information and alerts only**. It does not:
- Control the vehicle's brakes, throttle, or steering
- Override any vehicle control system
- Provide automated emergency braking
- Qualify as a Level 1 or higher ADAS system

**Required labeling statement:**
> "The eRadar360 is a driver information and alert system only. It does not control your vehicle and does not replace attentive driving. Always obey traffic laws and maintain full control of your vehicle."

### SAE J3016 Compliance Checklist

- [ ] Confirm device does not actuate any vehicle control (brake, throttle, steering)
- [ ] Confirm OBD-II connection is read-only (speed, RPM data only — no write commands)
- [ ] Include SAE J3016 Level 0 classification in product documentation
- [ ] Include driver responsibility disclaimer in user manual, app, and packaging
- [ ] Ensure all alert outputs are advisory only (audio/visual, no haptic brake intervention)

---

## 3. NHTSA Aftermarket ADAS Guidelines

NHTSA's 2020 guidance on aftermarket ADAS devices (Docket NHTSA-2020-0072) establishes voluntary best practices:

### 3.1 Driver Distraction

NHTSA recommends that aftermarket ADAS devices minimize driver distraction. The eRadar360 addresses this through:

| Requirement | eRadar360 Implementation | Status |
|-------------|--------------------------|--------|
| Minimize visual distraction | AMOLED display positioned in driver's peripheral vision (windshield mount) | ✅ |
| Audio alerts only for critical warnings | P1/P2 alerts use audio; P3/P4 are display-only | ✅ |
| No manual interaction while driving | All settings configured via mobile app before driving | ✅ |
| Alert duration ≤3 seconds for non-critical | P3/P4 alerts auto-dismiss after 3 seconds | ✅ |
| Glance-readable display | 4" AMOLED with high-contrast icons, readable in <1 second glance | ✅ |

### 3.2 Mounting and Installation

- [ ] Windshield mount must not obstruct driver's critical vision area (per FMVSS 205)
- [ ] Mount must comply with state laws on windshield obstruction (varies by state)
- [ ] OBD-II connector must not interfere with driver's leg movement
- [ ] Cable routing must not create entanglement hazard
- [ ] Include installation guide with safe mounting zone diagram

### 3.3 Cybersecurity (NHTSA 2022 Cybersecurity Best Practices)

NHTSA's 2022 Cybersecurity Best Practices for the Safety of Modern Vehicles recommends:

- [ ] Implement layered cybersecurity (defense in depth)
- [ ] Protect OBD-II interface from unauthorized access (read-only enforcement)
- [ ] Secure OTA update mechanism (signed firmware, rollback protection)
- [ ] Implement anomaly detection for unusual OBD-II data patterns
- [ ] Maintain vulnerability disclosure policy (VDP)
- [ ] Conduct annual penetration testing

---

## 4. FMVSS Applicability Analysis

### FMVSS 111 — Rearview Visibility

FMVSS 111 (49 CFR §571.111) requires new vehicles to have rearview video systems. For aftermarket devices:

- eRadar360 does **not** include a rearview camera
- The rear radar (AWR2944) provides object detection but not video
- If marketed as a "rearview assistance system," FMVSS 111 performance requirements may apply
- **Recommendation:** Do not market eRadar360 as a rearview camera replacement

### FMVSS 205 — Glazing Materials (Windshield)

FMVSS 205 governs windshield glazing and prohibits obstructions in the critical vision area (AS-1 zone). The eRadar360 windshield mount must be positioned:

- Below the AS-1 line (typically 4 inches from top of windshield)
- Outside the driver's primary forward vision zone
- Per SAE J1757-2 (automotive glazing)

- [ ] Define and document safe mounting zone in user manual
- [ ] Include mounting zone diagram on packaging
- [ ] Validate mount position does not obstruct AS-1 zone

### FMVSS 302 — Flammability of Interior Materials

The eRadar360 enclosure and mounting hardware must meet FMVSS 302 burn rate requirements (≤101.6 mm/min).

- [ ] Test enclosure material per FMVSS 302 (horizontal burn test)
- [ ] Test mounting suction cup and bracket material
- [ ] Document material compliance in technical file

---

## 5. State-Level Radar Detector Laws

Radar detector legality varies by US state. The eRadar360 must include clear legal disclosures:

| State | Radar Detector Status | Notes |
|-------|----------------------|-------|
| Virginia | ❌ Illegal | Prohibited by Va. Code §46.2-1079 |
| Washington DC | ❌ Illegal | DC Code §50-2201.03 |
| All other US states | ✅ Legal (private vehicles) | Federal preemption for commercial vehicles |
| Canada (all provinces) | ❌ Illegal | Provincial Highway Traffic Acts |
| Most EU countries | ❌ Illegal | Local road traffic laws |

### Required Disclosures

- [ ] Include state/country legality disclaimer in user manual
- [ ] Display legality warning on first app launch
- [ ] Include in-app GPS-based legal zone alerts (where data available)
- [ ] Include on product packaging: "Check local laws before use"

---

## 6. V2X Regulatory Compliance

### FCC V2X Authorization (47 CFR Part 90 Subpart M)

The TEKTON3 V2X module requires FCC authorization under Part 90 Subpart M for operation in the 5.895–5.925 GHz band as C-V2X (PC5 sidelink). DSRC (IEEE 802.11p) is not a US operating mode: US DSRC operations end 2026-12-14. See `regulatory/fcc/FCC_AUTHORIZATION_CHECKLIST.md` Part 3 for full details.

### USDOT V2X Deployment Program

The US Department of Transportation's V2X deployment program (FHWA-HRT-22-048) provides guidance on V2X interoperability:

- [ ] Implement SAE J2735 (DSRC Message Set Dictionary) for BSM, TIM, SPaT, MAP
- [ ] Implement SAE J2945/1 (On-Board System Requirements for V2V Safety) for BSM
- [ ] Implement IEEE 1609.2 (Security Services for WAVE) for message signing
- [ ] Implement IEEE 1609.3 (WAVE Networking Services) for WSMP
- [ ] Obtain SCMS (Security Credential Management System) enrollment certificate

### SAE J2945/1 BSM Requirements

The Basic Safety Message (BSM) broadcast must include:

| Field | Requirement | TEKTON3 Implementation |
|-------|-------------|----------------------|
| Message ID | 0x14 (BSM) | ✅ |
| Temporary ID | 4-byte rotating ID | ✅ |
| D_Second | 0–65535 ms | ✅ |
| Latitude | WGS84, 1/10 µdeg | ✅ |
| Longitude | WGS84, 1/10 µdeg | ✅ |
| Elevation | 0.1 m resolution | ✅ |
| Speed | 0.02 m/s resolution | ✅ |
| Heading | 0.0125° resolution | ✅ |
| Acceleration | Longitudinal + lateral | ✅ |
| Brake status | 4-bit field | ✅ (via OBD-II) |
| Vehicle size | Length + width | ✅ (configured) |

---

## 7. Compliance Timeline and Costs

| Activity | Timeline | Estimated Cost |
|----------|----------|----------------|
| SAE J3016 documentation | Month 1 | Internal |
| FMVSS 302 flammability testing | Month 2–3 | $3,000–$6,000 |
| NHTSA distraction assessment (SAE J2364) | Month 3–4 | $8,000–$15,000 |
| V2X SCMS enrollment | Month 4–6 | $5,000–$10,000 |
| SAE J2945/1 conformance testing | Month 5–7 | $12,000–$20,000 |
| Legal review (state laws, disclaimers) | Month 1–2 | $5,000–$10,000 |
| **Total** | **7 months** | **$33,000–$61,000** |

---

*EmbeddedOS eCAD-Hardware-Products | eRadar360_CAD_Design | Document EOS-RADAR-NHTSA-001*
