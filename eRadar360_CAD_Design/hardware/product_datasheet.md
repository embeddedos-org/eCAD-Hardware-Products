# eRadar360 / Aegis One — Product Datasheet

## Product Overview

| Parameter | Value |
|-----------|-------|
| **Product Name** | eRadar360 (Aegis One) |
| **Category** | Advanced Driver Awareness System |
| **Version** | v1.0 Rev A |
| **Part Number** | ERAD360-001-A |
| **Target Price** | $699 USD (retail) |
| **BOM Cost** | ~$330 USD |

---

## Electrical Specifications

### Power

| Parameter | Min | Typ | Max | Unit |
|-----------|-----|-----|-----|------|
| Input Voltage (USB-C) | 4.5 | 5.0 | 5.5 | V |
| Input Voltage (OBD-II) | 9.0 | 12.0 | 16.0 | V |
| Input Current (USB-C) | — | 1.8 | 3.0 | A |
| Power Consumption (active) | — | 8.5 | 10.0 | W |
| Power Consumption (sleep) | — | 0.5 | 0.8 | W |
| Power Consumption (off) | — | — | 0.01 | W |

### Internal Rails

| Rail | Voltage | Tolerance | Max Current | Source |
|------|---------|-----------|-------------|--------|
| VCC_5V | 5.00 V | ±5% | 3.0 A | USB-C / OBD-II regulator |
| VCC_3V3 | 3.30 V | ±3% | 1.5 A | TPS65219 BUCK1 |
| VCC_1V8 | 1.80 V | ±3% | 1.0 A | TPS65219 BUCK2 |
| VCC_0V85 | 0.85 V | ±3% | 4.0 A | TPS65219 BUCK3 |
| VCC_1V1 | 1.10 V | ±3% | 0.8 A | TPS65219 BUCK4 |
| VCC_OLED | 12.0 V | ±5% | 0.2 A | TPS61046 Boost |

---

## Radar Performance

| Parameter | X-Band | K-Band | Ku-Band | Ka-Band |
|-----------|--------|--------|---------|---------|
| Frequency Range | 10.500–10.550 GHz | 24.050–24.250 GHz | 13.450–13.500 GHz | 33.400–36.000 GHz |
| Antenna Type | Patch + LNA | 2×2 Patch | Patch + LNA | SIW Phased Array |
| Front Gain | 7 dBi | 12 dBi | 8 dBi | 24 dBi |
| Rear Gain | — | — | — | 18 dBi |
| Beam Steering (Front) | Fixed | Fixed | Fixed | ±45° Az, ±30° El |
| Beam Steering (Rear) | — | — | — | ±30° Az |
| Detection Range (typical) | 1.5 mi | 2.0 mi | 1.5 mi | 3.0+ mi |
| False Alert Suppression | — | — | — | 97% (AI) |

### Radar SoC

| Parameter | Value |
|-----------|-------|
| Chipset | TI AWR2944 × 2 (front + rear) |
| Technology | 77 GHz FMCW |
| TX Channels | 4 per SoC (8 total) |
| RX Channels | 4 per SoC (8 total) |
| IF Bandwidth | 20 MHz |
| Range Resolution | 0.75 m |
| Interface | SPI @ 50 MHz |

---

## Laser Detection

| Parameter | Value |
|-----------|-------|
| Sensors | 5× Hamamatsu G12183-010K InGaAs APD |
| Wavelength Coverage | 900–1700 nm (904 nm + 1550 nm guns) |
| Field of View | 360° (5 sensors at 72° spacing) |
| Response Time | < 100 µs (pulse detection) |
| Alert Latency | < 50 ms (end-to-end) |
| Dark Current | < 10 nA per sensor @ 25°C |
| TIA | OPA857 × 5 (4.5 GHz bandwidth) |

---

## V2X Communication

| Parameter | Value |
|-----------|-------|
| Chipset | Autotalks TEKTON3 |
| US mode | C-V2X, 3GPP PC5 Sidelink. US band is 5.895–5.925 GHz; the design range (5.855–5.925 GHz) is to be restricted to it |
| IEEE 802.11p | Supported by the chipset; not a US operating mode. US DSRC operations end on 2026-12-14 (FCC DA 25-125 (ET Docket No. 19-138, released 2025-02-11)). Intended only for regions that use ITS-G5 |
| Modes | C-V2X in the United States; the chipset is dual-mode |
| Range | Up to 1 km (line of sight) |
| Messages | BSM, TIM, SPaT, MAP |
| Antenna | External SMA (J5), 5.9 GHz |
| Interface | UART @ 115200 baud |

---

## AI / Processing

| Parameter | Value |
|-----------|-------|
| Main Processor | Rockchip RK3588S |
| CPU | 4× Cortex-A76 @ 2.4 GHz + 4× Cortex-A55 @ 1.8 GHz |
| NPU | 6 TOPS (INT8), RKNPU |
| GPU | Mali-G610 MP4 |
| Memory | 1 GB DDR4-3200 (Samsung K4A8G165WC) |
| Storage | 256 MB QSPI NOR Flash (Macronix MX25U25645G) |
| AI Model | Radar signature fingerprinting neural network |
| Inference Latency | < 10 ms per frame |
| False Alert Suppression | 97% (vs. door openers, BSM, adaptive cruise) |

### Co-Processor

| Parameter | Value |
|-----------|-------|
| Chipset | STMicroelectronics STM32H7B3 |
| Core | ARM Cortex-M7 @ 280 MHz |
| Flash | 2 MB |
| SRAM | 1 MB |
| Function | Laser ADC processing, OBD-II parsing, GPS data, sensor fusion |
| Interface | I2C0 to RK3588S |

---

## GPS / Navigation

| Parameter | Value |
|-----------|-------|
| Chipset | u-blox NEO-M9N |
| Constellations | GPS, GLONASS, Galileo, BeiDou |
| Accuracy | 1.5 m CEP |
| Cold Start | < 24 s |
| Hot Start | < 2 s |
| Update Rate | 25 Hz |
| Interface | I2C @ 400 kHz |
| Antenna | 25 mm ceramic patch (Taoglas AP.25F) |

---

## OBD-II Vehicle Interface

| Parameter | Value |
|-----------|-------|
| Protocol IC | ELM327 (Microchip) |
| CAN Transceiver | MCP2551 (1 Mbps) |
| Supported Protocols | CAN (ISO 15765), ISO 9141, KWP2000, J1850 |
| Data Read | Speed, RPM, throttle, cruise state, DTC codes |
| Connector | SAE J1962 male (J3) |
| Power Input | 12V from vehicle (via J3) |

---

## Display

| Parameter | Value |
|-----------|-------|
| Panel | Samsung AMS395GE04 AMOLED |
| Size | 4.0 inches diagonal |
| Resolution | 480 × 800 pixels |
| Brightness | 600 nits (max) |
| Interface | MIPI-DSI 2-lane |
| Features | Color-coded threat map, directional arrows, AI score overlay |
| Connector | 40-pin FPC (J4) |

---

## Connectivity

| Parameter | Value |
|-----------|-------|
| Wi-Fi | 802.11ax (Wi-Fi 6), 2.4 GHz — Qualcomm QCA6174A |
| Bluetooth | BLE 5.3 — Qualcomm QCA6174A |
| USB | USB 2.0 Type-C (data + power, J1) |
| Audio | 3.5 mm TRRS jack (J2) + 2W speaker (8Ω) |

---

## Mechanical

| Parameter | Value |
|-----------|-------|
| Dimensions | 120 mm × 85 mm × 18 mm |
| Weight | 185 g |
| Enclosure | ABS/PC blend, matte black |
| Mount | Magnetic windshield + suction cup |
| PCB | 10-layer, Rogers 4003C / FR4 hybrid |
| Surface Finish | ENIG |

---

## Environmental

| Parameter | Min | Max | Unit |
|-----------|-----|-----|------|
| Operating Temperature | -20 | +85 | °C |
| Storage Temperature | -40 | +100 | °C |
| Humidity (operating) | 10 | 90 | %RH (non-condensing) |
| Vibration | — | 2G, 5–500 Hz | — |
| ESD (contact) | — | ±8 kV | IEC 61000-4-2 |
| ESD (air) | — | ±15 kV | IEC 61000-4-2 |

---

## Regulatory

| Standard | Status |
|----------|--------|
| FCC Part 15 | Planned |
| FCC Part 90 (V2X) | Planned |
| IC (Canada) | Planned |
| CE (EU) | Planned |
| RoHS | Compliant |
| REACH | Compliant |
| UL/IEC 62368-1 | Planned |

---

## Pinout / Connectors

### J1 — USB Type-C
| Pin | Signal | Description |
|-----|--------|-------------|
| A1/B1 | GND | Ground |
| A4/B4 | VBUS | 5V power input |
| A6 | D+ | USB 2.0 data |
| A7 | D- | USB 2.0 data |
| B5 | CC2 | Configuration channel |

### J3 — OBD-II (SAE J1962)
| Pin | Signal | Description |
|-----|--------|-------------|
| 4 | Chassis GND | Vehicle ground |
| 5 | Signal GND | Signal ground |
| 6 | CAN High | CAN bus H |
| 14 | CAN Low | CAN bus L |
| 16 | Battery+ | 12V vehicle power |

### J6 — JTAG Debug (10-pin 1.27mm)
| Pin | Signal |
|-----|--------|
| 1 | VCC_3V3 |
| 2 | TMS/SWDIO |
| 3 | GND |
| 4 | TCK/SWCLK |
| 5 | GND |
| 6 | TDO/SWO |
| 7 | — |
| 8 | TDI |
| 9 | GND |
| 10 | nRESET |

---

## Ordering Information

| Part Number | Description |
|-------------|-------------|
| ERAD360-001-A | eRadar360 complete unit, US market |
| ERAD360-001-A-EU | eRadar360 complete unit, EU market |
| ERAD360-MOUNT-01 | Replacement magnetic mount |
| ERAD360-OBD-01 | OBD-II power cable (10 ft) |
| ERAD360-V2X-ANT-01 | External V2X antenna (SMA) |

---

*Document: ERAD360-DS-001 Rev A | Date: 2026-04-15 | EmbeddedOS*
