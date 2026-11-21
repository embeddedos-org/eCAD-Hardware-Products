# eRadar360 — Board Bring-Up & Test Guide

## Prerequisites

- Lab bench power supply (5V / 3A, current-limited)
- USB-C cable (data + power)
- Multimeter (4½ digit minimum)
- Oscilloscope (≥500 MHz, 4 channel)
- Spectrum analyzer (to 40 GHz) — for RF validation
- JTAG debugger (Segger J-Link or ST-Link V3)
- OBD-II simulator (or vehicle with OBD port)
- Serial terminal (115200 baud)

---

## Phase 1: Visual Inspection

1. **Inspect solder joints** under 10× microscope, especially:
   - U1, U2 (AWR2944) BGA — look for bridging
   - U3 (RK3588S) BGA — look for bridging
   - U4 (TEKTON3) BGA — look for bridging
   - U11 (DDR4) BGA — look for bridging
2. **Check orientation** of all polarized components (D1–D3, C61–C68 electrolytics if any)
3. **Verify RF shield** is properly seated and grounded

---

## Phase 2: Power Rail Validation (NO firmware loaded)

**⚠ Do NOT connect USB or OBD-II yet. Use lab supply only.**

### 2.1 Cold Resistance Check (Power OFF)

| Net | Expected | Measure Between | Fail If |
|-----|----------|----------------|---------|
| VCC_5V | > 10 Ω | J1 VBUS to GND | < 1 Ω (short) |
| VCC_3V3 | > 50 Ω | U10 pin 7 to GND | < 5 Ω (short) |
| VCC_1V8 | > 50 Ω | U10 pin 10 to GND | < 5 Ω (short) |
| VCC_0V85 | > 100 Ω | U10 pin 13 to GND | < 10 Ω (short) |
| VCC_1V1 | > 100 Ω | U10 pin 16 to GND | < 10 Ω (short) |

### 2.2 Power-On Sequence (Apply 5V, current limit 500mA)

Connect lab supply to J1 USB-C VBUS pin (or use USB-C breakout board).

| Step | Rail | Expected Voltage | Tolerance | Max Current | Time After Power |
|------|------|-----------------|-----------|-------------|-----------------|
| 1 | VCC_5V | 5.00 V | ±5% | 50 mA | 0 ms |
| 2 | VCC_3V3 | 3.30 V | ±3% | 80 mA | 1 ms |
| 3 | VCC_1V1 | 1.10 V | ±3% | 40 mA | 3 ms |
| 4 | VCC_0V85 | 0.85 V | ±3% | 200 mA | 5 ms |
| 5 | VCC_1V8 | 1.80 V | ±3% | 100 mA | 8 ms |
| 6 | VCC_OLED | 12.0 V | ±5% | 20 mA (idle) | 15 ms |

**Total quiescent current at idle (no firmware): ~150 mA @ 5V**

If any rail is missing or shows wrong voltage, STOP. Check PMIC (U10) enable pins and feedback resistors.

### 2.3 Power-Good Signals

| Signal | Pin | Expected | Notes |
|--------|-----|----------|-------|
| PG_3V3 | U10 PG1 | HIGH | Goes HIGH when VCC_3V3 is within 95% |
| PG_1V8 | U10 PG2 | HIGH | Goes HIGH when VCC_1V8 is within 95% |
| PG_CPU | U10 PG3 | HIGH | Goes HIGH when VCC_0V85 is within 95% |
| nRESET | U3 pin A1 | HIGH | De-asserted after all PG good |

---

## Phase 3: Processor Bring-Up

### 3.1 RK3588S (U3) — Main CPU

1. Connect JTAG debugger to J6 (10-pin Cortex header)
2. Connect serial console to UART2 debug port (115200 8N1)
3. Raise current limit to 2A
4. Power on — expect:
   - Boot ROM output on UART2 within 100ms
   - JTAG halts CPU at reset vector
5. Load minimal test firmware via JTAG:
   - Toggle GPIO (verify with scope)
   - Read CHIP_ID register — expect `0x35880000`
   - DDR4 initialization — memtest 1MB
   - SPI bus scan — should find U1 and U2 (AWR2944)

### 3.2 STM32H7B3 (U8) — Co-processor

1. Connect ST-Link to J6 secondary JTAG lines (shared header, different TDI/TDO)
2. Flash minimal LED blink firmware
3. Verify I2C bus scan finds:
   - U7 (NEO-M9N) at address 0x42
   - U5A-E (TIA) readable via ADC

### 3.3 DDR4 Memory Test

1. Run full memtest from RK3588S:
   - Walking-1s pattern
   - Walking-0s pattern
   - Random data
   - Address bus test
2. Expected: 8 Gbit (1 GB) at DDR4-3200
3. If errors: check VDDQ (1.8V), verify DDR4 training in firmware

---

## Phase 4: Subsystem Validation

### 4.1 Radar SoC — AWR2944 (U1 Front, U2 Rear)

1. SPI communication test — read DEVICE_ID register
   - U1: expect `0x2944` on SPI0
   - U2: expect `0x2944` on SPI1
2. Load chirp configuration (77 GHz FMCW, 4 GHz sweep, 100 µs chirp)
3. Verify IF output on oscilloscope (expect beat frequency)
4. **RF test (requires spectrum analyzer):**
   - Transmit CW at 77 GHz
   - Verify output power: +12 dBm ±2 dB per TX channel
   - Verify all 4 TX channels active
   - Check spurious emissions (must be < -30 dBc)

### 4.2 V2X — TEKTON3 (U4)

1. UART communication test at 115200 baud
2. Send AT command — expect `OK` response
3. Scan for C-V2X PC5 (5.9 GHz) sidelink signals
4. Verify C-V2X PC5 sidelink mode enters search state
5. **Antenna test:** connect V2X antenna to J5, verify RSSI reading

### 4.3 GPS — NEO-M9N (U7)

1. I2C read — device responds at 0x42
2. Configure UBX protocol, request NAV-PVT
3. With antenna connected to J7, verify:
   - Satellite acquisition (>4 SVs) within 60s (cold start)
   - Position fix accuracy < 5m CEP
   - 1PPS output toggling

### 4.4 Laser Array — InGaAs APD (U5A-E)

1. Apply bias voltage (check TIA output offset — should be ~1.5V at idle)
2. Point a 905nm laser pointer at each sensor window
3. Verify TIA output spike on oscilloscope (>500 mV peak)
4. Verify all 5 channels respond independently
5. Measure dark current: < 10 nA per APD at room temperature

### 4.5 Display — AMOLED (U6)

1. Initialize MIPI-DSI interface from RK3588S
2. Send solid color test patterns: Red, Green, Blue, White, Black
3. Verify all pixels illuminate (no dead lines)
4. Measure brightness at max: ≥ 600 nits (with lux meter)

### 4.6 OBD-II — ELM327 + MCP2551 (U9A/U9B)

1. Connect to OBD-II simulator (or vehicle)
2. Send `ATZ` — expect `ELM327 v2.x`
3. Send `0100` — expect supported PIDs response
4. Read vehicle speed (PID `010D`) — verify matches simulator value
5. Verify CAN bus termination (120Ω between CANH and CANL)

### 4.7 Audio — Speaker + 3.5mm

1. Play 1 kHz sine wave through TPA2012D2
2. Verify speaker output (SPK1) — should be audible, no distortion
3. Plug in 3.5mm headphones — verify audio switches to headphone output
4. Test volume levels: min, mid, max

### 4.8 Connectivity — Wi-Fi + Bluetooth

1. Initialize QCA6174A via PCIe/SDIO
2. Wi-Fi scan — verify SSIDs detected
3. Bluetooth scan — verify discoverable
4. OTA firmware update test via Wi-Fi

---

## Phase 5: System Integration Test

1. **Full power test:** All subsystems active, measure total current
   - Expected: 1.5–2.0A @ 5V (7.5–10W)
   - **Thermal check:** Verify no component exceeds 85°C after 30 min
2. **AI inference test:** Feed recorded radar samples through NPU
   - Verify classification output (Ka, K, X, false-alert)
   - Measure inference latency: < 10 ms per frame
3. **End-to-end alert test:**
   - Simulate Ka-band signal → display shows alert + direction arrow
   - Simulate laser pulse → audio alert within 100ms
   - Simulate V2X BSM → pre-alert before radar detection
4. **OBD-II context test:**
   - With speed = 0 and parked → suppress BSM door-opener alerts
   - With adaptive cruise active → reduce alert priority

---

## Phase 6: Environmental Qualification

| Test | Condition | Duration | Pass Criteria |
|------|-----------|----------|--------------|
| High temp operation | +85°C | 8 hours | All functions pass |
| Low temp operation | -20°C | 8 hours | All functions pass |
| Thermal shock | -20°C ↔ +85°C | 100 cycles | No solder cracks |
| Vibration | 5–500 Hz, 2G | 4 hours | No failures |
| ESD | ±8 kV contact, ±15 kV air | Per IEC 61000-4-2 | No damage |
| UV exposure | Windshield UV equivalent | 500 hours | Display readable |

---

## Sign-Off Checklist

- [ ] All power rails within spec
- [ ] JTAG access to RK3588S and STM32H7B3
- [ ] DDR4 memtest passes (full 1 GB)
- [ ] Both AWR2944 respond on SPI
- [ ] RF output verified at 77 GHz
- [ ] V2X TEKTON3 responds on UART
- [ ] GPS acquires fix within 60s
- [ ] All 5 laser sensors respond
- [ ] OLED displays all test patterns
- [ ] OBD-II reads vehicle speed
- [ ] Audio output functional (speaker + 3.5mm)
- [ ] Wi-Fi and Bluetooth operational
- [ ] Total system power < 10W
- [ ] No thermal exceedance at 85°C ambient
- [ ] AI inference < 10ms per frame
