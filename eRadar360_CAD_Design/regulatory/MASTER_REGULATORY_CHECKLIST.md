# eRadar360 — Master Regulatory Clearance Checklist
**Document:** EOS-RADAR-REG-MASTER | **Revision:** 1.0 | **Date:** 2026-06-03
**Product:** eRadar360 / Aegis One | **Target Markets:** USA, Canada, EU

---

## Executive Summary

The eRadar360 requires clearance across **7 regulatory frameworks** before commercial launch. This document consolidates all requirements, timelines, and costs into a single actionable checklist.

| Framework | Mandatory? | Lead Time | Estimated Cost | Status |
|-----------|-----------|----------|----------------|--------|
| FCC (Part 15B, 15.253, Part 90) | ✅ USA required | 7 months | $60K–$115K | Docs complete |
| ISED/IC (Canada) | ✅ Canada required | 7 months | $5K–$12K | Docs complete |
| NHTSA / SAE J3016 | Advisory | 7 months | $33K–$61K | Docs complete |
| ISO 26262 (functional safety) | Recommended | 12 months | $85K–$160K | Docs complete |
| IEC 62443 (cybersecurity) | Recommended | 8 months | $28K–$55K | Docs complete |
| UNECE WP.29 R155/R156 | ✅ EU required | 12 months | $25K–$50K | Docs complete |
| FTC (marketing claims) | ✅ USA required | 2 months | $10K–$20K | Docs complete |
| **Total** | | **12 months** | **$246K–$473K** | |

---

## Phase 1: Immediate Actions (Month 1–2)

### Legal and Marketing
- [ ] **FTC Disclaimer:** Add to all marketing materials: "Check local laws before use. Radar detectors are illegal in Virginia, Washington DC, and Canada."
- [ ] **FTC Claim Substantiation:** Document evidence for all performance claims (97% false alert suppression, <50ms laser alert, 1km V2X range)
- [ ] **State Law Database:** Implement GPS-based legal zone alerts in mobile app
- [ ] **Privacy Policy:** Publish privacy policy covering GPS location data, OBD-II vehicle data, V2X messages
- [ ] **Terms of Service:** Publish ToS with driver responsibility disclaimer
- [ ] **EULA:** Publish EULA with limitation of liability for missed alerts

### Engineering
- [ ] **OBD-II Read-Only Lock:** Verify ELM327 is configured read-only in firmware
- [ ] **Firmware Signing:** Implement ECDSA-P256 firmware signature verification
- [ ] **Watchdog Timer:** Verify STM32H7B3 watchdog is active and tested
- [ ] **E-Label:** Implement regulatory information screen in firmware

---

## Phase 2: Testing and Certification (Month 2–7)

### FCC Testing
- [ ] Pre-compliance emissions scan (30 MHz–1 GHz) — $3K–$8K
- [ ] 77 GHz radar verification (§15.253/§15.255) — $18K–$35K
- [ ] Wi-Fi 6 / BT integration testing (§15.247) — $12K–$22K
- [ ] V2X C-V2X certification (Part 90) — $15K–$28K. DSRC is not a US mode: US DSRC operations end 2026-12-14 (see `fcc/FCC_AUTHORIZATION_CHECKLIST.md`, Part 3)
- [ ] Part 15B full compliance test — $8K–$15K
- [ ] FCC filing and fees — $4K–$7K
- [ ] ISED/IC simultaneous testing — $5K–$12K

### NHTSA / Safety
- [ ] FMVSS 302 flammability testing — $3K–$6K
- [ ] Windshield mount mechanical testing (drop, vibration, temperature) — $5K–$10K
- [ ] SAE J2364 driver distraction assessment — $8K–$15K
- [ ] V2X SCMS enrollment — $5K–$10K
- [ ] SAE J2945/1 BSM conformance testing — $12K–$20K

---

## Phase 3: Safety and Cybersecurity (Month 3–12)

### ISO 26262 Functional Safety
- [ ] Complete HARA sign-off by independent safety assessor
- [ ] Develop Technical Safety Concept (TSC)
- [ ] Complete hardware FMEA/FMEDA for ASIL-B items
- [ ] Complete software safety analysis (MC/DC coverage for ASIL-B modules)
- [ ] Conduct DFA (Dependent Failure Analysis)
- [ ] Conduct FTA for SG-001 (false collision warning) and SG-002 (missed warning)
- [ ] Calculate PMHF ≤ 10 FIT for ASIL-B hardware
- [ ] Independent safety assessment — $30K–$60K
- [ ] ISO 26262 certification (optional, TÜV or SGS) — $20K–$40K

### IEC 62443 Cybersecurity
- [ ] IEC 62443 gap assessment — $8K–$15K
- [ ] Implement all CR requirements (see ISO26262_FUNCTIONAL_SAFETY.md §2.3)
- [ ] Penetration testing (SL-2 target) — $20K–$40K
- [ ] Vulnerability disclosure policy (VDP) — published
- [ ] SBOM (CycloneDX format) — generated

### UNECE WP.29 (EU Market)
- [ ] Establish CSMS per R155 Annex 5
- [ ] Establish SUMS per R156 Annex 4
- [ ] Obtain CSMS certificate from Type Approval Authority
- [ ] Obtain SUMS certificate from Type Approval Authority
- [ ] EU Authorised Representative appointment — $3K–$8K/yr

---

## Phase 4: EU Market Entry (Month 8–14)

### CE Marking
- [ ] Conduct EMC testing per EN 55032 (Class B) and EN 55035
- [ ] Conduct Radio Equipment Directive (RED) testing per EN 300 328 (Wi-Fi/BT) and EN 302 571 (77 GHz radar)
- [ ] Conduct V2X testing per ETSI EN 302 663 (ITS-G5 / DSRC)
- [ ] Conduct LVD (Low Voltage Directive) testing per EN 62368-1
- [ ] Conduct RoHS compliance verification
- [ ] Prepare EU Declaration of Conformity (DoC)
- [ ] Affix CE mark to device and packaging
- [ ] Register in EPREL (European Product Registry for Energy Labelling) if applicable

### GDPR Compliance
- [ ] Appoint EU Data Protection Representative
- [ ] Conduct DPIA (Data Protection Impact Assessment) for GPS location data
- [ ] Implement data minimization (collect only necessary location/OBD data)
- [ ] Implement right to erasure (delete user data on request)
- [ ] Publish GDPR-compliant privacy notice

---

## Regulatory Contact Directory

| Organization | Contact | Purpose |
|-------------|---------|---------|
| FCC Office of Engineering and Technology | oet@fcc.gov | Part 15 / Part 90 questions |
| NHTSA Office of Vehicle Safety Compliance | nhtsa.dot.gov | FMVSS questions |
| Autotalks (TEKTON3 FCC grant) | support@autotalks.com | V2X FCC grant verification |
| Texas Instruments (AWR2944 FCC grant) | ti.com/support | Radar FCC grant verification |
| NTS Laboratories | ntslabs.com | FCC testing |
| SGS Automotive | sgs.com/automotive | ISO 26262 / IEC 62443 |
| TÜV Rheinland | tuv.com | ISO 26262 certification |
| SCMS (V2X credentials) | v2x-security.com | SCMS enrollment |

---

*EmbeddedOS eCAD-Hardware-Products | eRadar360_CAD_Design | Document EOS-RADAR-REG-MASTER*
