# eRadar360 — Sensor Coverage Matrix and System Architecture
**Document:** EOS-RADAR-SYS-001 | **Revision:** 1.0 | **Date:** 2026-06-03

---

## 1. Sensor Coverage Matrix

### 1.1 Threat Detection Capabilities

| Threat Type | Front Radar | Rear Radar | Laser Detection | V2X | GPS/GNSS | OBD-II | AI NPU |
|-------------|------------|-----------|----------------|-----|---------|--------|--------|
| Speed camera (stationary) | ✅ Detect | — | ✅ Laser detect | — | ✅ Location | — | ✅ Classify |
| Speed camera (mobile) | ✅ Detect | ✅ Detect | ✅ Laser detect | — | ✅ Location | — | ✅ Classify |
| Red light camera | — | — | ✅ Laser detect | ✅ SPaT msg | ✅ Intersection | — | ✅ Classify |
| Police radar (Ka/K/X band) | — | — | ✅ Laser detect | — | — | — | ✅ Signature |
| Adaptive cruise radar | ✅ Detect | ✅ Detect | — | — | — | ✅ Speed | ✅ Filter |
| Emergency vehicle | — | — | — | ✅ BSM/TIM | ✅ Proximity | — | ✅ Alert |
| Road hazard ahead | — | — | — | ✅ TIM msg | ✅ Location | — | ✅ Alert |
| Traffic signal phase | — | — | — | ✅ SPaT msg | ✅ Intersection | — | ✅ Countdown |
| Collision warning (front) | ✅ TTC calc | — | — | ✅ BSM | ✅ Speed | ✅ Speed | ✅ FCW |
| Collision warning (rear) | — | ✅ TTC calc | — | ✅ BSM | ✅ Speed | ✅ Speed | ✅ RCW |
| Lane change assist | ✅ Detect | ✅ Detect | — | ✅ BSM | — | — | ✅ BLIS |
| Door opener / false alert | ✅ Detect | ✅ Detect | — | — | — | — | ✅ Suppress |

### 1.2 Sensor Performance Specifications

| Sensor | Parameter | Specification |
|--------|-----------|--------------|
| **Front Radar (AWR2944)** | Frequency | 76–81 GHz (77 GHz center) |
| | Waveform | FMCW, 4TX/4RX MIMO |
| | Range | 0.5–250 m |
| | Range resolution | 0.75 m |
| | Velocity resolution | 0.12 m/s |
| | Angular resolution | 15° azimuth, 10° elevation |
| | Max targets | 128 simultaneous |
| | Update rate | 20 Hz |
| **Rear Radar (AWR2944)** | Frequency | 76–81 GHz |
| | Range | 0.5–150 m |
| | Angular coverage | ±60° azimuth |
| | Update rate | 20 Hz |
| **Laser Detection (×5 APD)** | Wavelength | 900–1700 nm (904 nm + 1550 nm guns) |
| | Field of view | 360° (5 sensors at 72° spacing) |
| | Response time | <100 µs (pulse detection) |
| | Alert latency | <50 ms (end-to-end) |
| | Dark current | <10 nA per sensor @ 25°C |
| | TIA bandwidth | 4.5 GHz (OPA857) |
| **V2X (TEKTON3)** | C-V2X standard (US mode) | 3GPP PC5 Sidelink, Band 47, 5.895–5.925 GHz |
| | IEEE 802.11p | Supported by the chipset; not a US operating mode |
| | Range | Up to 1 km (LOS) |
| | Latency | <10 ms (BSM broadcast) |
| | Messages | BSM, TIM, SPaT, MAP, EVA |
| **GNSS (NEO-M9N)** | Constellations | GPS, GLONASS, Galileo, BeiDou |
| | Position accuracy | 2.5 m CEP (open sky) |
| | Update rate | 18 Hz |
| | Cold start | <24 s |
| **AI NPU (RK3588S)** | Performance | 6 TOPS (INT8) |
| | Inference latency | <10 ms per frame |
| | False alert suppression | 97% (vs. door openers, BSM, ACC) |
| | Signature database | >50,000 radar signatures |

---

## 2. System Architecture

### 2.1 Processing Pipeline

```
Sensor Layer                Processing Layer              Output Layer
─────────────               ────────────────              ────────────
Front AWR2944 ──SPI──►┐
Rear  AWR2944 ──SPI──►│     ┌─────────────────┐          ┌──────────────┐
                       ├────►│   RK3588S NPU   │─────────►│ AMOLED Alert │
5× InGaAs APD ─Analog►│     │  AI Threat Engine│          │   Display    │
                       │     │  Signature DB    │          └──────────────┘
TEKTON3 V2X  ──UART──►│     │  V2X Correlator  │
                       │     │  OBD Fuser       │          ┌──────────────┐
NEO-M9N GPS  ──UART──►│     └────────┬─────────┘    ┌────►│ Audio Alert  │
                       │              │               │     │ (2W Speaker) │
OBD-II Port  ──CAN───►│     ┌────────▼─────────┐    │     └──────────────┘
                       └────►│  STM32H7B3       │────┘
                              │  Co-processor    │          ┌──────────────┐
                              │  Laser ADC       │─────────►│ Mobile App   │
                              │  GPS fusion      │          │ (BT 5.3)     │
                              │  OBD parsing     │          └──────────────┘
                              └──────────────────┘
```

### 2.2 Alert Priority System

| Priority | Alert Type | Latency Target | Output |
|----------|-----------|---------------|--------|
| P1 — Critical | Collision imminent (TTC <1.5s) | <100 ms | Audio + Display + Haptic |
| P1 — Critical | Laser gun detected | <50 ms | Audio + Display |
| P2 — High | Emergency vehicle approaching | <200 ms | Audio + Display |
| P2 — High | Red light camera ahead | <500 ms | Display |
| P3 — Medium | Speed camera zone | <1,000 ms | Display |
| P3 — Medium | V2X road hazard | <500 ms | Display |
| P4 — Info | Traffic signal phase (SPaT) | <1,000 ms | Display |
| P4 — Info | Speed limit update | <2,000 ms | Display |

### 2.3 Power Architecture

| Rail | Voltage | Current | Supplied By | Consumers |
|------|---------|---------|-------------|-----------|
| VCC_12V | 12V | 2A max | OBD-II / USB-C | PMIC input |
| VCC_5V | 5V | 1.5A | TPS65219 Buck1 | RK3588S, peripherals |
| VCC_3V3 | 3.3V | 1.0A | TPS65219 Buck2 | STM32, GPS, BT/Wi-Fi |
| VCC_1V8 | 1.8V | 0.5A | TPS65219 Buck3 | Flash, DDR4 I/O |
| VCC_1V1 | 1.1V | 0.8A | TPS65219 Buck4 | RK3588S CPU core |
| VCC_0V85 | 0.85V | 1.2A | TPS65219 LDO | RK3588S NPU/GPU |
| VCC_OLED | 4.6–12V | 200mA | TPS61046 Boost | AMOLED ELVDD |

**Total system power:** ~8.5W typical, 12W peak  
**OBD-II fuse rating:** 15A (standard OBD-II port)  
**USB-C input:** 5V/3A (15W PD)

---

## 3. Competitive Differentiation

| Feature | eRadar360 | Escort MAX 360c | Uniden R9 | Cobra RAD 480i |
|---------|-----------|----------------|-----------|----------------|
| 77 GHz FMCW radar | ✅ Dual (front+rear) | ❌ | ❌ | ❌ |
| 360° laser detection | ✅ 5× InGaAs APD | ✅ 4 sensors | ✅ 4 sensors | ✅ 4 sensors |
| V2X (C-V2X) | ✅ C-V2X (PC5) | ❌ | ❌ | ❌ |
| AI NPU (6 TOPS) | ✅ | ❌ | ❌ | ❌ |
| OBD-II integration | ✅ | ❌ | ❌ | ❌ |
| GPS/GNSS | ✅ Multi-constellation | ✅ | ✅ | ✅ |
| Display | ✅ 4" AMOLED | ✅ OLED | ❌ | ❌ |
| Wi-Fi 6 | ✅ | ✅ | ❌ | ❌ |
| False alert suppression | 97% (AI) | ~85% (GPS DB) | ~80% | ~75% |
| MSRP | $699–$899 | $649 | $499 | $199 |

---

*EmbeddedOS eCAD-Hardware-Products | eRadar360_CAD_Design | Document EOS-RADAR-SYS-001*
