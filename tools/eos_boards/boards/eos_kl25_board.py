"""EoS KL25 Board: an NXP Kinetis KL25 development board that fits Uno R3 shields, designed by Kartikeydheer Srivastava.

Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved: this design file is not under
the repository's MIT licence; see boards/eos/eos-kl25-board/LICENSE.txt.

A 68.58 x 53.34 mm two-layer board for the NXP MKL25Z128VLK4 (Kinetis KL25, Cortex-M0+,
48 MHz, LQFP-80) at 3.3 V. It does the job of NXP's FRDM-KL25Z: Arduino R3 shield headers, the
KL25's own full-speed USB on USB-C, an 8 MHz crystal, an RGB LED, an accelerometer, a reset
button, and a Cortex 10-pin SWD header and a USB-UART bridge in place of OpenSDA.
No design file of NXP's (schematic, layout, Gerbers, BOM) was opened. The circuit comes from
the chip makers' datasheets; the header positions come from published Uno R3 mechanical facts.

Mechanical facts (origin top-left, y down; the sources use mils from the lower-left corner, y up):

* Outline 2700 x 2100 mil = 68.58 x 53.34 mm, and the shield header positions: Matthew
  Beckler's "Arduino Uno R3" dimension drawing v1.05 (Wayne and Layne): digital 1x10 from
  1640 mil (D8) to 740 mil (SCL) and 1x8 from 2500 mil (D0) to 1800 mil (D7) on the 2000-mil
  row; power 1x8 from 1100 mil and analog 1x6 from 2000 mil on the 100-mil row. Checked
  against KiCad 10's Module:Arduino_UNO_R3_WithMountingHoles footprint, pad by pad.
* Mounting holes, 3.2 mm, at (600, 2000), (550, 100), (2600, 1400) and (2600, 300) mil:
  Arduino UNO R3 product reference manual (A000066), section 5.4 (15.24 / 2.54 / 50.80 /
  66.04 / 17.78 / 45.72 mm, 4 x 3.20 mm), and the Beckler drawing. Unplated, as on EoS
  ATmega328P Board. The 10-pin socket's SCL end lies within the top-left hole's screw-head
  courtyard, so H1 is placed from the back, where its standoff goes.
* The Uno R3 pin order (A000066 section 5): power header NC, IOREF, RESET, 3V3, 5V, GND, GND,
  VIN; digital D0-D13, GND, AREF, SDA, SCL; SDA/SCL duplicate A4/A5.

Every value follows a datasheet or a chip maker's guide. Sources, by short name:
  DS   = NXP KL25 sub-family data sheet KL25P80M48SF0, Rev 5, 08/2014
  RM   = NXP KL25 sub-family reference manual KL25P80M48SF0RM, Rev 3, 09/2012
  KLQ  = NXP (Freescale) Kinetis L Peripheral Module Quick Reference KLQRUG, Rev 0, 09/2012:
         chapter 2 is NXP's Kinetis L hardware design guidance
  AN3208 = NXP (Freescale) AN3208 "Crystal Oscillator Troubleshooting Guide", Rev 0
  AN1706 = NXP (Freescale) AN1706 "Microcontroller Oscillator Circuit Design Considerations"
  AN2867 = ST AN2867 Rev 24 "Guidelines for oscillator design", section 3.4 (critical transconductance)

* Supply. DS Table 5: VDD 1.71-3.6 V, VDDA within 0.1 V of VDD. The board runs at 3.3 V from
  an AP7361C-33 LDO (Diodes DS37274 Rev. 5-2: 2.2-6.0 V in, 1 A out; "Bypass to ground through
  at least 1 uF" on IN and "at least 2.2 uF" on OUT; 4.7 uF on each, the values its electrical
  characteristics are specified with). The DS and RM give no VDD decoupling value; KLQ 2.1.3.2
  asks for a bypass capacitor at the supply pins, so each VDD/VSS pair (7/8, 38/39, 60/59) gets
  100 nF next to it, the value RM 28.6.2.3 gives for VDDA, and the LDO's 4.7 uF is the bulk.
* VDDA and VREFH (RM 28.6.1.1, 28.6.1.2, 28.6.2.3): VDDA from 3.3 V through a ferrite bead
  (inductive isolation), so it gets 100 nF plus the "additional 1 uF" the RM asks for in that
  case. VREFH has its 0.1 uF low-ESR capacitor to VREFL at the pins. The bead is a Murata
  BLM18PG221SN1D (JENF243A: 220 ohm at 100 MHz, 1.4 A, 0.10 ohm max), so the ADC's few mA drop
  well under a millivolt and VDDA stays within DS Table 5's 0.1 V of VDD. JP1 picks VREFH:
  VDDA as delivered, or the AREF header pin (cut and re-bridge), which RM 28.2.3 allows for an
  external reference between the minimum and VDDA. VREFL and VSSA go to ground.
* USB (KL25, J1). RM 3.9.1.2.1 (Figure 3-29): the MCU runs from VDD and the USB regulator
  (VREGIN in, VOUT33 out) powers the transceiver from USB VBUS, so VREGIN is wired to J1's VBUS
  after the fuse and VOUT33 to its capacitor only. DS Table 30: VREGIN 2.7-5.5 V, COUT
  1.76-8.16 uF with 1-100 mohm ESR: VOUT33 gets 4.7 uF X7R (Murata GRM21BR71A475KE51L): inside
  that window at +10 % and for any DC-bias loss up to 58 % at 3.3 V (the exact figure is not confirmed). 100 nF at VREGIN as its local bypass (KLQ
  2.1.3.2). The transceiver therefore has no supply, and its internal D+ pull-up cannot be on,
  without VBUS. RM 3.9.1: "To detect a valid VBUS in device mode, use a GPIO signal that can
  wake the chip in all power modes": VBUS reaches PTD6, a PORTD interrupt pin and LLWU_P15,
  through 15 k / 22 k (5.5 V -> 3.27 V, under VDD; 4.4 V -> 2.62 V, over VIH = 0.7 VDD = 2.31 V,
  DS Table 5). When J1 is the only source, VDD follows the TPS2116's 1.7 ms soft start (SLVSFG1A
  6.6) and the LDO, while a bare divider would follow VBUS at once; DS Table 4 allows at most
  VDD + 0.3 V on the pin, which has no diode to VDD (Table 5 note 1). So C24, 1 uF on PTD6, makes
  the divider rise with 15 k || 22 k x 1 uF = 8.9 ms: about 0.33 V/ms against VDD's 2.9 V/ms,
  and PTD6 is still at 0.6 V 2 ms after the plug-in, by when VDD is at 3.3 V. PTD6 has 0.06 VDD of input
  hysteresis (Table 5), so the slow edge reads cleanly. KLQ 9.6.2 (Figure 9-11): 33 ohm series
  resistors close to the MCU on D+/D-.
* Clock. DS Table 20: 3-32 MHz in high-frequency mode; the PLL needs 2-4 MHz (8 MHz / 4).
  DS Table 19 note 3: in high-frequency mode the load capacitors must be external; note 4: in
  low-power mode (HGO = 0) RF is integrated "and must not be attached externally", and RS is
  zero. Crystal: ECS-80-10-30B-CWN-TR (ECS ECX-53B: 8 MHz, CL 10 pF, ESR 100 ohm max, C0 5 pF
  max, drive level 100 uW max). The DS gives no oscillator transconductance, so the gain margin
  cannot be computed; the load is chosen to need as little gain as the family offers. AN2867 3.4's
  critical transconductance, gmcrit = 4 ESR (2 pi f)^2 (C0 + CL)^2, is 0.227 mA/V with CL 10 pF
  against 0.535 mA/V with the 18 pF part of the same family: 2.35 times less gain needed. Load
  capacitors from AN3208 section 5 (C1 = C2, series value = CL including strays): C = 2 x CL -
  Cstray = 20 - 9 = 11 pF, with Cstray = 7 pF pin capacitance (DS Table 12, CIN max) + 2 pF of
  board (AN1706 3.1.1, about 1 pF per cm of trace). Drive level, AN3208 Eqn. 1, P = 2 R1
  [pi f V (CL + C0)]^2: in low-power mode, where the swing is 0.6 V (DS Table 19, Vpp, taken as a
  peak, which overstates P), P = 10 uW, a tenth of the crystal's 100 uW; in high-gain mode, with
  a full 3.3 V swing, it would be 310 uW. So firmware must run the oscillator in low-power mode
  (MCG_C2[HGO] = 0, RANGE = 01), and no external RF is fitted.
* Reset (KLQ 2.1.3.4.1): "The RESET_b pin ... should have a 100 nF capacitor close to the MCU
  ... an external 4.7 kohm to 10 kohm pullup is recommended": 10 kohm and 100 nF, and a button
  to ground. RM 6.2.2.1: the pin is open drain with an internal pull-up. NMI_b (PTA4), which
  is NMI by default out of reset, gets the same 10 kohm and, as KLQ says, no capacitance; PTA4
  is not on a header, so a shield cannot fire the NMI.
* Debug: an Arm Cortex 10-pin (1.27 mm) SWD header, J7: SWD_CLK (PTA0), SWD_DIO (PTA3),
  RESET_b, VTref = 3.3 V. The KL25 has no SWO. It replaces OpenSDA, whose firmware is NXP's.
  RM 6.2: SWD_CLK has a pull-down and SWD_DIO a pull-up out of reset, so none is fitted.
* Power path. USB-C as a 5 V sink on each port: 5.1 kohm Rd on CC1 and CC2 (USB Type-C
  specification, sink termination). ESD protection on D+, D- and VBUS of both ports: Littelfuse
  SP0503BAHTG (SP05xxBA data sheet: 5.5 V standoff, 100 nA maximum leakage at 5 V, 30 pF), three
  diodes from each line to the common pin 1 and none between them, the part the CP2102N data
  sheet shows (Figure 2.5). Pins 2, 3 and 4 are the same diode, so D+ is on pin 3 and D- on pin 2,
  the order that keeps each pair from crossing (see Layout). A USBLC6-2SC6 is not used: its data-line diodes run to its VBUS
  pin, so after a host unplugs J2 the CP2102N's D+ pull-up, live on the board's 3.3 V, could
  hold J2's VBUS near 2 V, between the VBUS pin's VIL and VIH (Table 3.7), and the bridge
  might never see the unplug. J1 gets the same part, so nothing but the host's VBUS reaches
  the KL25's VBUS detect divider either. Each VBUS through a Bourns MF-NSMF050/8X-2 PTC (MF-NSMF series Rev. AF: 0.50 A hold,
  1.00 A trip, 8 V, R1max 0.75 ohm; the plain MF-NSMF050 is marked not for new designs). A TI
  TPS2116 power mux (SLVSFG1A) joins them: priority mode, MODE tied to VIN1 (section 7.6.1),
  VIN1 = the KL25 port, VIN2 = the bridge port. PR1 = VIN1 x 10 k / 37 k, against VREF
  0.92-1.08 V (section 6.5), so VIN1 is used whenever it is above 3.40-4.00 V, below USB's
  4.40 V minimum (USB 2.0 Table 7-7, low-power port). Reverse current blocking (section 7.3.4;
  reverse leakage out of VINx 0.001 uA typical, 6.5) means neither port, nor 5 V fed into the
  shield 5V pin, feeds the other port or the bridge. 1 uF on each input (section 9) and 100 uF
  on VOUT (section 7.3.4: "a high output capacitance (about 100 uF)" where reverse blocking can
  occur); soft start limits the inrush (section 8.2: 100 uF gives 294 mA). The shield VIN pin
  is not connected: there is no 7-12 V input, and a voltage there must not reach the 5 V rail.
  IOREF is 3.3 V: the KL25's pins are not 5 V tolerant (DS Table 4: VIO max VDD + 0.3 V), so a
  shield driving 5 V onto a pin can damage the chip. Nothing may feed the 3V3 or IOREF pins:
  they are the LDO's output, whose absolute maximum is VIN + 0.3 V (DS37274), so a shield
  sourcing 3.3 V with no USB attached would drive the LDO backwards.
* USB-UART: Silicon Labs CP2102N-A02-GQFN20 (data sheet Rev. 1.5) on UART0 (PTA1 RX, PTA2 TX,
  the D0/D1 header pins), on its own USB-C, J2. It runs from the board's 3.3 V with its own
  regulator unused (Figure 2.3: VREGIN tied to VDD, 3.0-3.6 V in; QFN20: VIO = VDD), so it is
  powered whenever the KL25 is and the KL25's TX never drives an unpowered bridge. "4.7 uF and
  0.1 uF bypass capacitors required for each power pin": one pair at VREGIN and one at VDD.
  1 kohm RSTb pull-up to VDD (section 2.1). Its VBUS pin ("A 5 V signal on this pin indicates a
  USB network connection", Table 5.3) senses J2's VBUS through the 22.1 k / 47.5 k divider
  section 2.3 requires (Figure 2.6, self-powered): 5 V reads 3.41 V, over VIH = VIO - 0.6 V =
  2.7 V (Table 3.7); section 2.3 notes the divider's current limit covers the VIO + 2.5 V rating
  while VDD is still rising. So the bridge connects to USB, and its D+ pull-up comes on, only
  when a host supplies VBUS (USB 2.0 section 7.1.5). Bleed: with J1 powering the board and no
  host on J2, VBUS2 is still a TPS2116 input, whose leakage could lift it. The CP2102N reads its
  VBUS pin as low only at or below VIL = 0.6 V (Table 3.7), so VBUS2 must stay under
  0.6 V x 69.6 / 47.5 = 0.88 V. R27 = 10 kohm in parallel with the divider is 8.74 kohm, which
  holds VBUS2 under 0.88 V for up to 100 uA of leakage. The TPS2116's largest leakage or
  shutdown-current maximum is 2.9 uA (ISD, 105 C; reverse leakage out of VINx is 0.15 uA typical
  at 105 C, SLVSFG1A 6.5), 34 times under that. A host on J2 pays 0.5 mA for it. J2 still powers the board
  through the TPS2116 (VIN2) when it is the only source. Unused pins left open: GPIOs default
  to open drain with a weak pull-up (section 4.3.1). It was chosen for its 3.3 V UART levels,
  the KL25's, and its single-chip USB (no crystal). TXD and RXD meet D0/D1 through 1 kohm, so a
  shield driving D0 against the bridge's TXD fights at most 3.3 mA, within its 6.5 mA
  low-drive rating (Table 3.7); 1 kohm x about 20 pF = 20 ns is nothing at 3 Mbaud.
* RGB LED: Wurth 150141M173100 (common anode; pin 1 anode, 2 blue, 3 red, 4 green). VF at
  20 mA: red 2.0 V typ (2.4 max), green and blue 3.2 V typ (3.6 max), 30 mA continuous max.
  From 3.3 V a GPIO cannot light green or blue reliably (3.6 V max), so the anode is on 5 V and
  each colour is switched by an AO3400A N-MOSFET (Alpha & Omega: VGS(th) 0.65-1.45 V, RDS(on)
  < 48 mohm at VGS = 2.5 V), driven by a KL25 PWM pin. About 5 mA each, computed with the 20 mA
  VF (lower at 5 mA, so slightly more): red (5.0 - 2.0) / 620 ohm = 4.8 mA, green and blue
  (5.0 - 3.2) / 360 ohm = 5.0 mA; worst case 4.4 V and the maximum VF still gives 2.2 mA. The
  KL25's pins are disabled out of reset (RM 6.2), so 100 kohm holds each gate low and the LED
  off until firmware drives it (33 uA when on). Red on PTA12 (TPM1_CH0), green on PTA13
  (TPM1_CH1), blue on PTE25 (TPM0_CH1).
* Power LED: Kingbright APTD1608LCGCK (DSAO7432: VF 1.9 V typ at 2 mA) on 3.3 V through
  680 ohm: 2.1 mA.
* Accelerometer: ST LIS2HH12 (DocID025344 Rev 5), in production; NXP's MMA8451Q is end of
  life (NXP product page). On its own I2C bus, I2C1 on PTE0 (SDA) / PTE1 (SCL) (ALT6, RM
  10.3.1), so a shield cannot clash with its address. CS tied to Vdd_IO selects I2C; SA0 to GND
  gives 0011110b = 0x1E (through JP2, re-bridged to 3.3 V for 0x1D); RES to GND (Table 2,
  section 6). 100 nF on Vdd_IO, and at Vdd 100 nF and 10 uF (section 4, Figure 5: "100 nF
  ceramic, 10 uF aluminum ... (common design practice)"). The 10 uF is a ceramic X5R 0805: the
  aluminium part first chosen (Panasonic EEE-1CA100SR) is not for new designs, and Vdd is a
  load, not a regulator output that needs the electrolytic's ESR. INT1 to PTD7, INT2 to PTD4 (PORTD interrupt
  pins); push-pull by default (CTRL5 PP_OD = 0). SCL and SDA "must be connected to Vdd_IO through
  an external pull-up" (section 6.1): 4.7 kohm, inside NXP UM10204 section 7.1's limits for
  400 kHz (Rp min = (3.3 - 0.4) V / 3 mA = 0.97 kohm; Rp max = 300 ns / (0.8473 x 50 pF) =
  7.1 kohm).
* The capacitive slider is left out (see the README).
* Layout (two layers; the autorouter, Freerouting, gives a different result on every run, so
  everything below is laid by placement and `priority_routes`, before it runs):
  - USB, KLQ 9.6.3: "Route the USB D+ and D- signals as parallel 90 ohm differential pairs ...
    Minimize vias and corners ... Avoid signal stubs." Each pair runs on the top layer from the
    receptacle's A6/A7 contacts through its ESD part's pads (pins 3 and 2, inline, no stub) on to
    R5/R6 and the MCU, or to the CP2102N. The receptacle's second contacts join behind: B7 (D-)
    to A7 under the shell on the top layer, and B6 (D+) to A6 through two vias, the one crossing
    a USB-C pair needs, kept in the 3.5 mm duplicate-contact stub.
  - Crystal, KLQ 2.1.3.3.1: "The crystal or resonator must be located close to the MCU. No
    signals of any kind should be routed on the layer directly below the crystal. The load
    capacitors and ground of the crystal package must be connected to a single ground trace
    coming from the closest VSS pin". Y1 sits below EXTAL0 (pin 40), turned so its EXTAL pad is
    straight below that pin and its XTAL pad on the side facing XTAL0 (pin 41), which runs straight
    down to it; each load capacitor sits beside its own pad. Pin -> pad -> capacitor is laid on the
    top layer with no via. One ground trace runs from VSS pin 39 through C10's and C14's ground
    ends to Y1's ground pads (joined across under its body) and C15. Y1 is kept out of the
    analog lines' way from the MCU's right side to the A0-A5 header, the reset line leaves C16 and
    R12 between XTAL0's line and those analog lines, and the RGB LED's switches are below. The
    generator has no bottom-layer keep-out, and on the routed board the reset line drops to the
    bottom layer there and crosses under Y1 and C14 (see the README).
  - Decoupling, KLQ 2.1.3.2 ("placed close to the MCU supply pins"; the CP2102N's "as close to
    the pins as possible", CP Figure 2.3): VDD pins 7 and 38, VOUT33, VREGIN, VDDA (C11, C12, the
    bead and JP1), VREFH (C13 and JP1), RESET_b's 100 nF, the CP2102N's four capacitors and the
    LDO's are each joined to their pin by a short top-layer route laid first.

Arduino pin map (KL25 pin, function; PWM on D3, D5, D6, D9, D10, D11 as on the Uno; D2 and D3
are interrupt pins, as on the Uno):
  D0 PTA1 UART0_RX (bridge TXD via 1 k)   D1 PTA2 UART0_TX (bridge RXD via 1 k)
  D2 PTA5 PORTA interrupt                 D3 PTD5 TPM0_CH5, PORTD interrupt
  D4 PTC5                                 D5 PTB18 TPM2_CH0
  D6 PTC4 TPM0_CH3                        D7 PTC6
  D8 PTC7                                 D9 PTC8 TPM0_CH4
  D10 PTD0 SPI0_PCS0, TPM0_CH0            D11 PTD2 SPI0_MOSI, TPM0_CH2
  D12 PTD3 SPI0_MISO                      D13 PTD1 SPI0_SCK
  A0 PTB0 ADC0_SE8    A1 PTB1 ADC0_SE9    A2 PTC1 ADC0_SE15   A3 PTC2 ADC0_SE11
  A4/SDA PTB3 ADC0_SE13, I2C0_SDA         A5/SCL PTB2 ADC0_SE12, I2C0_SCL
J8 (2x6, 2.54 mm) brings out PTB8, PTB9, PTB10-PTB11 and PTB16-PTB17 (SPI1), PTB19
(TPM2_CH1), PTC0 (ADC0_SE14), PTC3 (UART1_RX, CLKOUT) and PTE30 (DAC0_OUT), with 3.3 V and GND.
Pins not used are left unconnected: RM 6.2, non-analog pins are disabled after reset.

Two layers, ground poured on both sides.
"""

from __future__ import annotations

from ..design import NC, Board, Part, USB_C_EDGE
from .owner import CONTACT, LICENCE, LICENCE_TERMS, OWNER

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
HOLE = "MountingHole:MountingHole_3.2mm_M3_ISO14580"

DS = "NXP KL25P80M48SF0 Rev 5"
RM = "NXP KL25P80M48SF0RM Rev 3"
KLQ = "NXP KLQRUG Rev 0"
CP = "Silicon Labs CP2102N Rev. 1.5"
TPS = "TI SLVSFG1A"
LIS = "ST LIS2HH12 DocID025344 Rev 5"


# Capacitor part numbers by value, all Murata and all "In Production" on Murata's product pages (checked
# 2026-10-13). The 4.7 uF 10 V X7R part stays inside DS Table 30's 1.76-8.16 uF for the VOUT33 capacitor
# for any DC-bias loss up to 58 % at 3.3 V (its exact figure is not confirmed).
MURATA = {"100n": "GRM155R71C104KA88D", "1u": "GCM188R71C105KA64D", "4.7u": "GRM21BR71A475KE51L",
          "4.7u 25V": "GRM219R61E475KA73D", "10u": "GRM21BR61C106KE15L", "11p": "GJM1555C1H110JB01D"}


def yageo(value):
    """Yageo RC0402FR-07 (1 %, 0402) part number: 5.1k -> RC0402FR-075K1L, 33 -> RC0402FR-0733RL."""
    code = (value[:-1].replace(".", "K") if "." in value else value[:-1] + "K") if value.endswith("k") else value + "R"
    return f"RC0402FR-07{code}L"


def res(ref, value, a, b, sch, desc, rot=0, dnp=False):
    return Part(ref, "Device:R_Small", value, R0402, sch, {"1": a, "2": b},
                fields={"Manufacturer": "Yageo", "MPN": yageo(value), "Description": desc}, sch_rotation=rot, dnp=dnp)


def cap(ref, value, a, b, sch, desc, fp=C0402, rot=0, mfr="Murata", mpn=None):
    fields = {"Manufacturer": mfr, "MPN": mpn or MURATA[value], "Description": desc}
    return Part(ref, "Device:C_Small", value, fp, sch, {"1": a, "2": b}, fields=fields, sch_rotation=rot)


def socket(ref, n, value, pins, sch, desc):
    """A female header for shields: pin 1 is the first signal named in ``pins``."""
    return Part(ref, f"Connector:Conn_01x{n:02d}_Socket", value,
                f"Connector_PinSocket_2.54mm:PinSocket_1x{n:02d}_P2.54mm_Vertical", sch,
                {str(i + 1): net for i, net in enumerate(pins)},
                fields={"Manufacturer": "Samtec", "MPN": f"SSW-1{n:02d}-01-T-S", "Description": desc})


def usb_c(ref, vbus, cc1, cc2, dp, dm, sch, what):
    return Part(ref, "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
                sch, {"VBUS": vbus, "GND": "GND", "CC1": cc1, "CC2": cc2, "D+": dp, "D-": dm,
                      "SBU1": NC, "SBU2": NC, "SHIELD": "GND"},
                fields={"Manufacturer": "Korean Hroparts", "MPN": "TYPE-C-31-M-12",
                        "Description": f"USB-C 2.0 receptacle, 16 pins: {what}"})


def esd(ref, dp, dm, vbus, sch, swap=False):
    """Three TVS diodes to GND (pin 1 the common anode), none between the lines, so a live D+
    pull-up cannot raise VBUS through the protection part. Pins 2, 3 and 4 are the same diode to
    pin 1 (Littelfuse SP05xxBA pinout), so ``swap`` puts D+ on pin 3 and D- on pin 2 where that
    keeps the pair from crossing."""
    p_dp, p_dm = ("3", "2") if swap else ("2", "3")
    return Part(ref, "Power_Protection:SP0503BAHT", "SP0503BAHTG", "Package_TO_SOT_SMD:SOT-143", sch,
                {"1": "GND", p_dp: dp, p_dm: dm, "4": vbus},
                fields={"Manufacturer": "Littelfuse", "MPN": "SP0503BAHTG",
                        "Description": "USB ESD protection, three diodes to GND on D+, D- and VBUS, no path between them "
                                       f"({CP} Figure 2.5)"})


def fuse(ref, a, b, sch):
    return Part(ref, "Device:Polyfuse_Small", "500mA", "Fuse:Fuse_1206_3216Metric", sch, {"1": a, "2": b},
                fields={"Manufacturer": "Bourns", "MPN": "MF-NSMF050/8X-2",
                        "Description": "PTC fuse 0.50 A hold, 1.00 A trip, 8 V, R1max 0.75 ohm, 1206 (Bourns MF-NSMF Rev. AF)"})


def nfet(ref, gate, drain, sch, colour):
    return Part(ref, "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23", sch,
                {"G": gate, "S": "GND", "D": drain},
                fields={"Manufacturer": "Alpha & Omega", "MPN": "AO3400A",
                        "Description": f"N-MOSFET, {colour} LED switch: VGS(th) 0.65-1.45 V, RDS(on) < 48 mohm at 2.5 V (AOS AO3400A)"})


W, H = 68.58, 53.34          # 2700 x 2100 mil
MIL = 0.0254


def uno(x_mil, y_mil):
    """A position from the Uno R3 drawings (mils from the lower-left corner, y up) in board mm."""
    return round(x_mil * MIL, 4), round(H - y_mil * MIL, 4)


D0_PIN = uno(2500, 2000)      # D0 .. D7 run right to left, 100 mil apart
D8_PIN = uno(1640, 2000)      # D8 .. D13, GND, AREF, SDA, SCL run right to left
POWER_PIN = uno(1100, 100)    # NC, IOREF, RESET, 3V3, 5V, GND, GND, VIN run left to right
A0_PIN = uno(2000, 100)       # A0 .. A5 run left to right
HOLES = [uno(600, 2000), uno(550, 100), uno(2600, 1400), uno(2600, 300)]

# MKL25Z128VLK4 (LQFP-80) pins by number, DS section 5.1. NC: not used, disabled after reset (RM 6.2).
MCU = {
    1: "ACC_SDA", 2: "ACC_SCL", 3: NC, 4: NC, 5: NC, 6: NC,             # PTE0 I2C1_SDA, PTE1 I2C1_SCL (ALT6)
    7: "+3V3", 8: "GND", 9: "KL_DP", 10: "KL_DM", 11: "VOUT33", 12: "VBUS1_F",
    13: NC, 14: NC, 15: NC, 16: NC,                                      # PTE20-PTE23
    17: "VDDA", 18: "VREFH", 19: "GND", 20: "GND",                       # VDDA, VREFH, VREFL, VSSA
    21: NC, 22: "EXT_PTE30", 23: NC, 24: NC, 25: "LED_B",                # PTE29, PTE30 DAC0_OUT, PTE31, PTE24, PTE25 TPM0_CH1
    26: "SWCLK", 27: "D0", 28: "D1", 29: "SWDIO", 30: "NMI", 31: "D2",   # PTA0, PTA1, PTA2, PTA3, PTA4, PTA5
    32: "LED_R", 33: "LED_G", 34: NC, 35: NC, 36: NC, 37: NC,            # PTA12 TPM1_CH0, PTA13 TPM1_CH1, PTA14-17
    38: "+3V3", 39: "GND", 40: "XTAL_IN", 41: "XTAL_OUT", 42: "RESET",   # VDD, VSS, EXTAL0, XTAL0, RESET_b
    43: "A0", 44: "A1", 45: "A5_SCL", 46: "A4_SDA",                      # PTB0-PTB3
    47: "EXT_PTB8", 48: "EXT_PTB9", 49: "EXT_PTB10", 50: "EXT_PTB11",
    51: "EXT_PTB16", 52: "EXT_PTB17", 53: "D5", 54: "EXT_PTB19",         # PTB18 TPM2_CH0, PTB19 TPM2_CH1
    55: "EXT_PTC0", 56: "A2", 57: "A3", 58: "EXT_PTC3", 59: "GND", 60: "+3V3",
    61: "D6", 62: "D4", 63: "D7", 64: "D8", 65: "D9", 66: NC,            # PTC4 TPM0_CH3, PTC5, PTC6, PTC7, PTC8 TPM0_CH4, PTC9
    67: NC, 68: NC, 69: NC, 70: NC, 71: NC, 72: NC,                      # PTC10-PTC13, PTC16, PTC17
    73: "D10", 74: "D13", 75: "D11", 76: "D12",                          # PTD0-PTD3 SPI0
    77: "ACC_INT2", 78: "D3", 79: "VBUS1_DET", 80: "ACC_INT1",           # PTD4, PTD5 TPM0_CH5, PTD6 LLWU_P15, PTD7
}

PARTS = [
    # ---- KL25 USB-C (J1), ESD, fuse, VBUS sense, series resistors -------------------------------
    usb_c("J1", "VBUS1", "CC1A", "CC2A", "USB1_DP", "USB1_DM", (45, 100), "KL25 native USB (USB0)"),
    res("R1", "5.1k", "CC1A", "GND", (80, 78), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC1, USB Type-C specification)"),
    res("R2", "5.1k", "CC2A", "GND", (95, 78), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC2, USB Type-C specification)"),
    esd("U1", "USB1_DP", "USB1_DM", "VBUS1", (110, 105), swap=True),
    fuse("F1", "VBUS1", "VBUS1_F", (140, 82)),
    res("R5", "33", "USB1_DP", "KL_DP", (140, 120), f"Resistor 33 ohm 1% 0402 (USB D+ series termination close to the MCU, {KLQ} 9.6.2)"),
    res("R6", "33", "USB1_DM", "KL_DM", (155, 120), f"Resistor 33 ohm 1% 0402 (USB D- series termination close to the MCU, {KLQ} 9.6.2)"),
    res("R7", "15k", "VBUS1_F", "VBUS1_DET", (175, 92), f"Resistor 15 kohm 1% 0402 (VBUS detect divider: 5.5 V -> 3.27 V, {RM} 3.9.1)", rot=90),
    res("R8", "22k", "VBUS1_DET", "GND", (190, 92), f"Resistor 22 kohm 1% 0402 (VBUS detect divider: 4.4 V -> 2.62 V > VIH, {DS} Table 5)", rot=90),
    cap("C24", "1u", "VBUS1_DET", "GND", (205, 92), f"Capacitor 1 uF 16 V X7R 0603 (PTD6 rises with 15 k || 22 k x 1 uF = 8.9 ms, slower than "
        f"VDD, so it stays under VDD + 0.3 V, {DS} Table 4, while the TPS2116 soft start ({TPS} 6.6 and 8.2: 1.7 ms) brings VDD up)",
        C0603),

    # ---- Power mux (J1 first, J2 otherwise), 100 uF, 3.3 V LDO, power LED -------------------------
    Part("U3", "Power_Management:TPS2116DRL", "TPS2116", "Package_TO_SOT_SMD:SOT-583-8", (95, 165),
         {"VIN1": "VBUS1_F", "VIN2": "VBUS2_F", "VOUT": "+5V", "GND": "GND", "PR1": "MUX_PR1", "MODE": "VBUS1_F", "ST": NC},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPS2116DRLR",
                 "Description": f"Power mux 2.5 A, priority mode: VIN1 (KL25 USB) first, VIN2 (UART USB) otherwise ({TPS} 7.6.1)"}),
    res("R9", "27k", "VBUS1_F", "MUX_PR1", (55, 150), f"Resistor 27 kohm 1% 0402 (PR1 divider: VIN1 used above 3.40-4.00 V, {TPS} 6.5 VREF)", rot=90),
    res("R10", "10k", "MUX_PR1", "GND", (55, 168), f"Resistor 10 kohm 1% 0402 (PR1 divider, {TPS} 7.6.1.1)", rot=90),
    cap("C1", "1u", "VBUS1_F", "GND", (125, 150), f"Capacitor 1 uF 16 V X7R 0603 (TPS2116 VIN1, {TPS} section 9)", C0603),
    cap("C2", "1u", "VBUS2_F", "GND", (140, 150), f"Capacitor 1 uF 16 V X7R 0603 (TPS2116 VIN2, {TPS} section 9)", C0603),
    Part("C3", "Device:C_Polarized_Small", "100u", "Capacitor_SMD:CP_Elec_6.3x5.8", (155, 150), {"1": "+5V", "2": "GND"},
         fields={"Manufacturer": "Panasonic", "MPN": "EEE-FK1C101P",
                 "Description": f"Capacitor 100 uF 16 V aluminium electrolytic, 6.3 x 5.8 mm (TPS2116 VOUT, reverse current blocking, {TPS} 7.3.4)"}),
    Part("U4", "Regulator_Linear:AP7361C-33E", "AP7361C-33", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", (95, 215),
         {"VI": "+5V", "VO": "+3V3", "GND": "GND"},
         fields={"Manufacturer": "Diodes Incorporated", "MPN": "AP7361C-33E-13",
                 "Description": "LDO 3.3 V 1 A, SOT-223, input 2.2-6.0 V (Diodes DS37274 Rev. 5-2)"}),
    cap("C4", "4.7u", "+5V", "GND", (70, 210), "Capacitor 4.7 uF 25 V X5R 0805 (LDO input: at least 1 uF, 4.7 uF as specified, Diodes DS37274)", C0805,
        mpn=MURATA["4.7u 25V"]),
    cap("C5", "4.7u", "+3V3", "GND", (120, 210), "Capacitor 4.7 uF 10 V X7R 0805 (LDO output: at least 2.2 uF, 4.7 uF as specified, Diodes DS37274)", C0805),
    res("R11", "680", "+3V3", "LED_PWR_A", (140, 210), "Resistor 680 ohm 1% 0402 (power LED: (3.3 V - 1.9 V) / 680 ohm = 2.1 mA, Kingbright DSAO7432)"),
    Part("D1", "Device:LED_Small", "PWR", "LED_SMD:LED_0603_1608Metric", (158, 210), {"A": "LED_PWR_A", "K": "GND"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LCGCK",
                 "Description": "LED green 0603, VF 1.9 V typ at 2 mA (Kingbright DSAO7432): power (3.3 V)"}),

    # ---- UART USB-C (J2), ESD, fuse, VBUS sense and bleed, CP2102N on 3.3 V -----------------------
    usb_c("J2", "VBUS2", "CC1B", "CC2B", "USB2_DP", "USB2_DM", (45, 280), "USB-UART (CP2102N) and board power"),
    res("R3", "5.1k", "CC1B", "GND", (80, 258), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC1, USB Type-C specification)"),
    res("R4", "5.1k", "CC2B", "GND", (95, 258), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC2, USB Type-C specification)"),
    esd("U2", "USB2_DP", "USB2_DM", "VBUS2", (110, 285), swap=True),
    fuse("F2", "VBUS2", "VBUS2_F", (140, 262)),
    Part("U6", "Interface_USB:CP2102N-Axx-xQFN20", "CP2102N-A02-GQFN20",
         "Package_DFN_QFN:SiliconLabs_QFN-20-1EP_3x3mm_P0.5mm_EP1.8x1.8mm", (205, 290),
         {"VREGIN": "+3V3", "VDD": "+3V3", "GND": "GND", "D+": "USB2_DP", "D-": "USB2_DM", "VBUS": "BR_VBUS",
          "~{RST}": "BR_RST", "TXD": "BR_TXD", "RXD": "BR_RXD",
          **{p: NC for p in ("1", "2", "10", "11", "13", "14", "15", "16", "19", "20")}},
         fields={"Manufacturer": "Silicon Labs", "MPN": "CP2102N-A02-GQFN20",
                 "Description": f"USB-UART bridge on the board's 3.3 V, own regulator unused: VREGIN tied to VDD ({CP} Figure 2.3)"}),
    cap("C17", "4.7u", "+3V3", "GND", (160, 300), f"Capacitor 4.7 uF 10 V X7R 0805 (CP2102N VREGIN, tied to VDD, {CP} Figure 2.3)", C0805),
    cap("C18", "100n", "+3V3", "GND", (160, 318), f"Capacitor 100 nF 16 V X7R 0402 (CP2102N VREGIN, tied to VDD, {CP} Figure 2.3)"),
    cap("C19", "4.7u", "+3V3", "GND", (245, 258), f"Capacitor 4.7 uF 10 V X7R 0805 (CP2102N VDD, {CP} Figure 2.3)", C0805),
    cap("C20", "100n", "+3V3", "GND", (260, 258), f"Capacitor 100 nF 16 V X7R 0402 (CP2102N VDD, {CP} Figure 2.3)"),
    res("R14", "1k", "BR_RST", "+3V3", (245, 280), f"Resistor 1 kohm 1% 0402 (CP2102N RSTb pull-up to VDD, {CP} section 2.1)", rot=90),
    res("R15", "22.1k", "VBUS2_F", "BR_VBUS", (150, 340), f"Resistor 22.1 kohm 1% 0402 (CP2102N VBUS divider, {CP} Figure 2.6)", rot=90),
    res("R16", "47.5k", "BR_VBUS", "GND", (165, 340), f"Resistor 47.5 kohm 1% 0402 (CP2102N VBUS divider: 5 V -> 3.41 V, {CP} Figure 2.6)", rot=90),
    res("R27", "10k", "VBUS2_F", "GND", (180, 340), f"Resistor 10 kohm 1% 0402 (VBUS2 bleed: with the divider, 8.74 kohm holds VBUS2 under 0.88 V, "
        f"so the CP2102N VBUS pin under VIL 0.6 V ({CP} Table 3.7), for up to 100 uA of leakage; TPS2116 at most 2.9 uA, {TPS} 6.5)", rot=90),
    res("R17", "1k", "BR_TXD", "D0", (250, 305), f"Resistor 1 kohm 1% 0402 (bridge TXD to D0/PTA1: a shield driving D0 fights at most 3.3 mA, {CP} Table 3.7)"),
    res("R18", "1k", "D1", "BR_RXD", (250, 322), f"Resistor 1 kohm 1% 0402 (D1/PTA2 to bridge RXD: contention and ESD current limit on a shield pin)"),

    # ---- MKL25Z128VLK4 and its supply, analog, clock, reset ---------------------------------------
    Part("U5", "MCU_NXP_Kinetis:MKL25Z128VLK4", "MKL25Z128VLK4", "Package_QFP:LQFP-80_12x12mm_P0.5mm", (335, 200),
         {str(n): net for n, net in MCU.items()},
         fields={"Manufacturer": "NXP", "MPN": "MKL25Z128VLK4",
                 "Description": f"Kinetis KL25, Cortex-M0+ 48 MHz, 128 KB flash, 16 KB SRAM, USB FS OTG, LQFP-80 ({DS})"}),
    cap("C6", "100n", "VBUS1_F", "GND", (290, 300), f"Capacitor 100 nF 16 V X7R 0402 (VREGIN local bypass, {KLQ} 2.1.3.2)"),
    cap("C7", "4.7u", "VOUT33", "GND", (305, 300), f"Capacitor 4.7 uF 10 V X7R 0805 (USB regulator VOUT33: 1.76-8.16 uF, ESR 1-100 mohm, {DS} Table 30)", C0805),
    cap("C8", "100n", "+3V3", "GND", (320, 300), f"Capacitor 100 nF 16 V X7R 0402 (VDD pin 7 / VSS pin 8, {KLQ} 2.1.3.2)"),
    cap("C9", "100n", "+3V3", "GND", (335, 300), f"Capacitor 100 nF 16 V X7R 0402 (VDD pin 60 / VSS pin 59, {KLQ} 2.1.3.2)"),
    cap("C10", "100n", "+3V3", "GND", (350, 300), f"Capacitor 100 nF 16 V X7R 0402 (VDD pin 38 / VSS pin 39, {KLQ} 2.1.3.2)"),
    Part("FB1", "Device:FerriteBead_Small", "220R", "Inductor_SMD:L_0603_1608Metric", (290, 325), {"1": "+3V3", "2": "VDDA"},
         fields={"Manufacturer": "Murata", "MPN": "BLM18PG221SN1D",
                 "Description": f"Ferrite bead 220 ohm at 100 MHz, 1.4 A, 0.10 ohm max (Murata JENF243A): VDDA isolation, {RM} 28.6.2.3"}),
    cap("C11", "100n", "VDDA", "GND", (305, 325), f"Capacitor 100 nF 16 V X7R 0402 (VDDA to VSSA, {RM} 28.6.2.3)"),
    cap("C12", "1u", "VDDA", "GND", (320, 325), f"Capacitor 1 uF 16 V X7R 0603 (VDDA, additional 1 uF with inductive isolation, {RM} 28.6.2.3)", C0603),
    cap("C13", "100n", "VREFH", "GND", (335, 325), f"Capacitor 100 nF 16 V X7R 0402 (VREFH to VREFL, low ESR, at the pins, {RM} 28.6.1.2)"),
    Part("JP1", "Jumper:SolderJumper_3_Bridged12", "VREFH", "Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm",
         (365, 325), {"A": "VDDA", "C": "VREFH", "B": "AREF"},
         fields={"Description": f"VREFH source: 1-2 (as delivered) VDDA; cut and bridge 2-3 for the AREF pin (must not exceed VDDA, {RM} 28.2.3)"}),
    Part("Y1", "Device:Crystal_GND24", "8MHz", "Crystal:Crystal_SMD_5032-4Pin_5.0x3.2mm", (430, 92),
         {"3": "XTAL_IN", "1": "XTAL_OUT", "2": "GND", "4": "GND"},
         fields={"Manufacturer": "ECS Inc.", "MPN": "ECS-80-10-30B-CWN-TR",
                 "Description": "Crystal 8 MHz, CL 10 pF, +-10 ppm, +-15 ppm -40..85 C, ESR 100 ohm max, C0 5 pF max, 100 uW max, "
                                "5.0 x 3.2 mm (ECS ECX-53B)"}),
    cap("C14", "11p", "XTAL_IN", "GND", (412, 108), "Capacitor 11 pF 50 V C0G 0402 (EXTAL load: 2 x 10 pF - 9 pF strays, AN3208 section 5)"),
    cap("C15", "11p", "XTAL_OUT", "GND", (448, 108), "Capacitor 11 pF 50 V C0G 0402 (XTAL load: 2 x 10 pF - 9 pF strays, AN3208 section 5)"),
    res("R12", "10k", "RESET", "+3V3", (420, 140), f"Resistor 10 kohm 1% 0402 (RESET_b pull-up, 4.7-10 kohm, {KLQ} 2.1.3.4.1)", rot=90),
    cap("C16", "100n", "RESET", "GND", (435, 140), f"Capacitor 100 nF 16 V X7R 0402 (RESET_b, close to the MCU, {KLQ} 2.1.3.4.1)"),
    Part("SW1", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", (455, 150),
         {"1": "RESET", "2": "GND"}, fields={"Manufacturer": "C&K", "MPN": "KMR221G LFS", "Description": "Tactile switch, reset (RESET_b)"}),
    res("R13", "10k", "NMI", "+3V3", (475, 140), f"Resistor 10 kohm 1% 0402 (NMI_b pull-up, no capacitance, {KLQ} 2.1.3.4.1)", rot=90),

    # ---- SWD -----------------------------------------------------------------------------------------
    Part("J7", "Connector:Conn_ARM_JTAG_SWD_10", "SWD", "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD",
         (520, 100), {"VTref": "+3V3", "SWDIO/TMS": "SWDIO", "GND": "GND", "SWCLK/TCK": "SWCLK",
                      "SWO/TDO": NC, "KEY": NC, "NC/TDI": NC, "GNDDetect": "GND", "~{RESET}": "RESET"},
         fields={"Manufacturer": "Samtec", "MPN": "FTSH-105-01-L-DV-K",
                 "Description": "Arm Cortex Debug 10-pin, 1.27 mm: SWD_CLK PTA0, SWD_DIO PTA3, RESET_b (replaces OpenSDA)"}),

    # ---- Accelerometer on I2C1 ---------------------------------------------------------------------
    Part("U7", "Sensor_Motion:LIS2HH12", "LIS2HH12", "Package_LGA:LGA-12_2x2mm_P0.5mm", (430, 190),
         {"1": "ACC_SCL", "2": "+3V3", "3": "ACC_SA0", "4": "ACC_SDA", "5": "GND", "6": "GND", "7": "GND", "8": "GND",
          "9": "+3V3", "10": "+3V3", "11": "ACC_INT2", "12": "ACC_INT1"},
         fields={"Manufacturer": "STMicroelectronics", "MPN": "LIS2HH12TR",
                 "Description": f"3-axis accelerometer, I2C 0x1E: CS high, SA0 to GND through JP2, RES to GND ({LIS} Table 2, section 6)"}),
    Part("JP2", "Jumper:SolderJumper_3_Bridged12", "0x1E", "Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm",
         (430, 222), {"A": "GND", "C": "ACC_SA0", "B": "+3V3"},
         fields={"Description": f"LIS2HH12 address: 1-2 (as delivered) SA0 low, 0x1E; cut and bridge 2-3 for 0x1D ({LIS} section 6.1.1)"}),
    res("R19", "4.7k", "ACC_SCL", "+3V3", (470, 172), f"Resistor 4.7 kohm 1% 0402 (I2C1 SCL pull-up, {LIS} 6.1; NXP UM10204 7.1)", rot=90),
    res("R20", "4.7k", "ACC_SDA", "+3V3", (485, 172), f"Resistor 4.7 kohm 1% 0402 (I2C1 SDA pull-up, {LIS} 6.1; NXP UM10204 7.1)", rot=90),
    cap("C21", "100n", "+3V3", "GND", (470, 200), f"Capacitor 100 nF 16 V X7R 0402 (LIS2HH12 Vdd_IO, {LIS} Figure 5)"),
    cap("C22", "100n", "+3V3", "GND", (485, 200), f"Capacitor 100 nF 16 V X7R 0402 (LIS2HH12 Vdd pin 9, {LIS} section 4)"),
    cap("C23", "10u", "+3V3", "GND", (500, 200), f"Capacitor 10 uF 16 V X5R 0805 (LIS2HH12 Vdd pin 9 bulk, {LIS} section 4; "
        "ceramic in place of the aluminium part ST names, whose Panasonic EEE-1CA100SR is not for new designs)", C0805),

    # ---- RGB LED, switched from 5 V --------------------------------------------------------------------
    Part("D2", "Device:LED_ABRG", "RGB", "LED_SMD:LED_RGB_Wuerth-PLCC4_3.2x2.8mm_150141M173100", (450, 250),
         {"A": "+5V", "BK": "RGB_BK", "RK": "RGB_RK", "GK": "RGB_GK"},
         fields={"Manufacturer": "Wurth Elektronik", "MPN": "150141M173100",
                 "Description": "RGB LED common anode, PLCC4 3.2 x 2.8 mm: VF 2.0 / 3.2 / 3.2 V typ at 20 mA (Wurth 150141M173100)"}),
    res("R21", "620", "RGB_RK", "RGB_RD", (420, 272), "Resistor 620 ohm 1% 0402 (red: (5.0 V - 2.0 V) / 620 ohm = 4.8 mA, Wurth 150141M173100 VF)", rot=90),
    res("R22", "360", "RGB_GK", "RGB_GD", (450, 272), "Resistor 360 ohm 1% 0402 (green: (5.0 V - 3.2 V) / 360 ohm = 5.0 mA, Wurth 150141M173100 VF)", rot=90),
    res("R23", "360", "RGB_BK", "RGB_BD", (480, 272), "Resistor 360 ohm 1% 0402 (blue: (5.0 V - 3.2 V) / 360 ohm = 5.0 mA, Wurth 150141M173100 VF)", rot=90),
    nfet("Q1", "LED_R", "RGB_RD", (425, 295), "red"),
    nfet("Q2", "LED_G", "RGB_GD", (455, 295), "green"),
    nfet("Q3", "LED_B", "RGB_BD", (485, 295), "blue"),
    res("R24", "100k", "LED_R", "GND", (408, 305), f"Resistor 100 kohm 1% 0402 (Q1 gate held low while PTA12 is disabled, {RM} 6.2)", rot=90),
    res("R25", "100k", "LED_G", "GND", (438, 305), f"Resistor 100 kohm 1% 0402 (Q2 gate held low while PTA13 is disabled, {RM} 6.2)", rot=90),
    res("R26", "100k", "LED_B", "GND", (468, 305), f"Resistor 100 kohm 1% 0402 (Q3 gate held low while PTE25 is disabled, {RM} 6.2)", rot=90),

    # ---- Shield headers and the extra I/O header ---------------------------------------------------------
    socket("J3", 10, "D8-SCL", ["D8", "D9", "D10", "D11", "D12", "D13", "GND", "AREF", "A4_SDA", "A5_SCL"], (545, 90),
           "Socket 1x10 2.54 mm, Uno R3 digital D8-D13, GND, AREF, SDA, SCL (pin 1 = D8)"),
    socket("J4", 8, "D0-D7", ["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7"], (545, 135),
           "Socket 1x8 2.54 mm, Uno R3 digital D0-D7 (pin 1 = D0)"),
    socket("J5", 8, "POWER", [NC, "+3V3", "RESET", "+3V3", "+5V", "GND", "GND", NC], (580, 90),
           "Socket 1x8 2.54 mm, Uno R3 power: NC, IOREF (3.3 V), RESET, 3V3, 5V, GND, GND, VIN (not connected)"),
    socket("J6", 6, "A0-A5", ["A0", "A1", "A2", "A3", "A4_SDA", "A5_SCL"], (580, 135),
           "Socket 1x6 2.54 mm, Uno R3 analog A0-A5 (pin 1 = A0)"),
    Part("J8", "Connector_Generic:Conn_02x06_Odd_Even", "EXT", "Connector_PinHeader_2.54mm:PinHeader_2x06_P2.54mm_Vertical",
         (550, 200), {"1": "+3V3", "2": "GND", "3": "EXT_PTB8", "4": "EXT_PTB9", "5": "EXT_PTB10", "6": "EXT_PTB11",
                      "7": "EXT_PTB16", "8": "EXT_PTB17", "9": "EXT_PTB19", "10": "EXT_PTC0", "11": "EXT_PTC3",
                      "12": "EXT_PTE30"},
         fields={"Manufacturer": "Samtec", "MPN": "TSW-106-07-G-D",
                 "Description": "Header 2x6 2.54 mm, extra I/O: 3V3, GND, PTB8, PTB9, PTB10, PTB11, PTB16, PTB17, PTB19, PTC0, PTC3, PTE30 (DAC0_OUT)"}),
]
for i, label in enumerate(["top left", "bottom left", "right, upper", "right, lower"]):
    PARTS.append(Part(f"H{i + 1}", "Mechanical:MountingHole", "M3", HOLE, (60 + 20 * i, 395), {},
                      side="B" if i == 0 else "F",
                      fields={"Description": f"Mounting hole 3.2 mm, unplated, Uno R3 position ({label})"}))

# Board placement: (x, y, rotation) in mm, origin top-left. Shield headers and holes where the Uno R3
# drawings put them. Both USB-C ports on the left edge (KLQ 2.1.2.1: connectors on one edge): the
# KL25's port above, the bridge's below, each with its ESD part, CC resistors and fuse; the power mux
# and its 100 uF between them. The MCU sits under the digital headers with its USB pins facing J1;
# its decoupling, VOUT33 and VDDA/VREFH parts on its left, the crystal below EXTAL0/XTAL0 (its
# bottom-right corner), the reset parts right of RESET_b, the SWD header below. The column right of
# the MCU is left to the six analog lines on their way down to A0-A5, so nothing there sits in
# their path; the RGB LED and its switches are below the SWD header and the crystal.
MCU_AT = (42.0, 24.0)
PLACEMENT = {
    "J3": (D8_PIN[0], D8_PIN[1], 270), "J4": (D0_PIN[0], D0_PIN[1], 270),
    "J5": (POWER_PIN[0], POWER_PIN[1], 90), "J6": (A0_PIN[0], A0_PIN[1], 90),
    **{f"H{i + 1}": (x, y, 0) for i, (x, y) in enumerate(HOLES)},
    "U5": (MCU_AT[0], MCU_AT[1], 0),
    # J1: KL25 USB. The ESD part's D+/D- column (pins 3, 2) faces away from the receptacle, so the pair
    # passes between its VBUS and GND pins and into pins 3 and 2 in the receptacle's order
    "J1": (USB_C_EDGE, 12.5, 270), "U1": (12.0, 12.5, 90), "R1": (9.6, 6.5, 0), "R2": (9.6, 18.5, 0),
    "F1": (16.0, 8.5, 0),
    "R7": (31.5, 15.0, 0), "R8": (31.5, 16.2, 0), "C24": (31.5, 17.6, 0),
    # power mux: turned so its two VOUT pads (2, 7) share one column: they join under the body, and 5 V
    # leaves pad 7 straight down to C3's + pad (see PRIORITY); VIN1 and PR1 leave upwards, VIN2 leftwards
    "U3": (17.0, 22.0, 270), "C1": (18.2, 18.9, 0), "C2": (13.8, 23.6, 180),
    "R9": (14.6, 19.3, 90), "R10": (15.9, 19.3, 90), "C3": (17.25, 29.5, 270),
    # USB series resistors in the pins' order (D+ above), D- level with pin 10, so neither line has to
    # jog across the other's escape; C8 above pins 7/8, VOUT33's 4.7 uF and VREGIN's 100 nF below the
    # pair, then VDDA (C11, the 1 uF and the bead) and VREFH (C13) with JP1 between their two lines
    "R5": (28.6, 22.55, 0), "R6": (28.6, 23.75, 0),
    "C8": (33.6, 22.15, 270), "C6": (33.8, 25.6, 270), "C7": (31.15, 25.5, 270),
    "C11": (32.75, 26.8, 90), "C13": (33.8, 28.33, 270), "JP1": (30.95, 29.65, 270),
    "C12": (28.9, 27.6, 270), "FB1": (27.2, 27.6, 90),
    # MCU bottom: VDD pin 38 / VSS pin 39's capacitor, NMI pull-up, and the crystal: EXTAL pad (3)
    # straight below pin 40, XTAL pad (1) in the column XTAL0 (pin 41) runs straight down, 1 mm or more
    # from the MCU's courtyard; C14 beside the EXTAL pad, C15 below the XTAL pad
    "C10": (44.9, 32.65, 270), "R13": (41.0, 33.0, 270),
    "Y1": (46.7, 36.6, 90), "C14": (44.0, 36.6, 270), "C15": (47.7, 40.55, 270),
    # RESET_b's 100 nF and pull-up right beside pin 42, in the column between XTAL0's line and the
    # analog lines; the button by the SWD header
    "C16": (50.5, 29.6, 0), "R12": (50.6, 31.0, 0), "SW1": (29.5, 37.0, 90),
    "C9": (51.4, 19.5, 90),
    # SWD below the MCU
    "J7": (36.0, 37.5, 0),
    # accelerometer, top left
    "U7": (27.0, 13.0, 0), "C21": (27.0, 9.9, 0), "C22": (24.6, 13.0, 90), "C23": (23.0, 13.0, 90),
    "R19": (30.0, 11.8, 90), "R20": (31.4, 11.8, 90), "JP2": (26.6, 16.6, 0),
    # J2: bridge USB and the CP2102N, whose D+/D- pins (4, 5) are level with the receptacle's A6/A7;
    # its 100 nF capacitors right at VDD pin 6 and VREGIN pin 7, the 4.7 uF ones behind them; the VBUS
    # divider and bleed below VBUS pin 8, the UART resistors above TXD/RXD
    "J2": (USB_C_EDGE, 37.5, 270), "U2": (12.0, 37.5, 90), "R3": (9.6, 31.5, 0), "R4": (9.6, 43.5, 0),
    "F2": (13.2, 46.0, 0),
    "U6": (19.0, 37.0, 0), "C18": (18.25, 40.3, 270), "C20": (16.6, 39.8, 180), "C19": (15.9, 41.5, 180),
    "C17": (15.9, 43.6, 180), "R14": (19.55, 40.4, 270), "R16": (18.9, 42.5, 270), "R15": (20.0, 42.5, 90),
    "R27": (21.1, 42.5, 90), "R17": (22.3, 33.4, 0), "R18": (22.3, 34.6, 180),
    # LDO with its input capacitor at IN (pin 1) and output capacitor at OUT (pin 3); power LED
    "U4": (30.0, 45.0, 0), "C4": (23.6, 42.7, 180), "C5": (23.6, 47.3, 180),
    "R11": (23.6, 45.0, 180), "D1": (21.0, 45.0, 0),
    # RGB LED and its switches below the SWD header and the crystal: blue, red, green left to right
    "Q3": (37.6, 43.2, 0), "Q1": (42.6, 43.2, 0), "Q2": (47.6, 43.2, 0),
    "R26": (35.15, 43.2, 270), "R24": (40.15, 43.2, 270), "R25": (45.15, 43.2, 270),
    "R23": (39.6, 46.3, 180), "R21": (47.2, 47.6, 90), "R22": (48.4, 47.6, 90), "D2": (43.6, 46.95, 180),
    # extra I/O header, right
    "J8": (54.2, 8.2, 0),
}
# Laid before the autorouter, in this order, and locked (pcb_build.py): Freerouting gives a different
# result on every run, so what the layout guidance asks for is not left to it.
# The mux output first, at its class width, before anything else can box it in: the TPS2116's pads
# are 0.3 mm wide at 0.5 mm pitch, so 5 V has one way out of each VOUT pad. Pad 2 to pad 7 under the
# body, then pad 7 down to the 100 uF.
PRIORITY = [(("U3", "2"), ("U3", "7")), (("U3", "7"), ("C3", "1"))]
# The accelerometer's two interrupt lines (U7 pins 11 and 12, side by side at 0.5 mm) go first,
# INT2 then INT1: they leave the package in the same order they reach the MCU (pins 77 and 80), and
# laid before the plane fan-out, neither one's via can land in front of the other's pad. SA0 (pin 3
# to JP2) is next, while the south side of that pad is still open. Pins 2 and 9 are both +3V3, but
# a 0.3 mm track cannot leave either (the neighbours are 0.5 mm away and the maze's margin closes
# the gap). Pin 10, the corner +3V3 pad, then joins C22, and JP2's +3V3 pad joins that capacitor,
# so the jumper meets the accelerometer supply without crossing SA0.
PRIORITY += [(("U7", "11"), ("U5", "77")), (("U7", "12"), ("U5", "80")),
             (("U7", "3"), ("JP2", "2")),
             (("U7", "10"), ("C22", "1")),
             (("JP2", "3"), ("C22", "1"))]
# The USB pairs (KLQ 9.6.3), D+ then D- for each line segment: from the receptacle's A6/A7 through
# the ESD part's pads to R5/R6 and the MCU, or to the CP2102N, on the top layer. The receptacle's
# order (A6 D+ above A7 D-) is the order at the far end, so the main lines do not cross. Then the
# second contacts: B7 (D-) joins A7 behind the pads, under the shell; B6 (D+) can then only reach
# A6's line through two vias, the single crossing a USB-C pair needs, kept in the short stub.
PRIORITY += [(("J1", "A6"), ("U1", "3")), (("U1", "3"), ("R5", "1")), (("R5", "2"), ("U5", "9")),
             (("J1", "A7"), ("U1", "2")), (("U1", "2"), ("R6", "1")), (("R6", "2"), ("U5", "10")),
             (("J1", "B7"), ("J1", "A7"), "join"), (("J1", "B6"), ("J1", "A6"), "join"),
             (("J2", "A6"), ("U2", "3")), (("U2", "3"), ("U6", "4")),
             (("J2", "A7"), ("U2", "2")), (("U2", "2"), ("U6", "5")),
             (("J2", "B7"), ("J2", "A7"), "join"), (("J2", "B6"), ("J2", "A6"), "join")]
# The crystal (KLQ 2.1.3.3.1): first Y1's two ground pads joined under its body, which also closes
# the gap between its pads to anything else; then pin -> crystal pad -> load capacitor for EXTAL0 and
# XTAL0 on the top layer; then the single ground trace from the nearest VSS pin (39) through C10's and
# C14's ground ends to Y1 and C15; last VDD pin 38 to C10.
PRIORITY += [(("Y1", "2"), ("Y1", "4")),
             (("U5", "40"), ("Y1", "3")), (("Y1", "3"), ("C14", "1")),
             (("U5", "41"), ("Y1", "1")), (("Y1", "1"), ("C15", "1")),
             (("U5", "39"), ("C10", "2")), (("C10", "2"), ("C14", "2")), (("C14", "2"), ("Y1", "4")),
             (("Y1", "4"), ("C15", "2")), (("U5", "38"), ("C10", "1"))]
# Decoupling (KLQ 2.1.3.2, CP2102N Figure 2.3), each capacitor joined to its own pin: VDD pin 7 and
# VSS pin 8 to C8; VOUT33 to C7; VREGIN to C6; VDDA to C11, then JP1, the 1 uF and the bead; VREFH to
# C13, then JP1, and VSSA pin 20 to C13's ground end, with the ground ends of C7, C11 and C6 joined;
# the CP2102N's VBUS pin to the divider (R16) before its supply routes, then its VDD and VREGIN
# pads to each other and to their 100 nF and 4.7 uF capacitors; the LDO's IN and OUT to C4 and C5;
# RESET_b to C16 and R12.
PRIORITY += [(("U5", "7"), ("C8", "1")), (("U5", "8"), ("C8", "2")),
             (("U5", "11"), ("C7", "1")), (("U5", "12"), ("C6", "1")),
             (("U5", "17"), ("C11", "1")), (("C11", "1"), ("JP1", "1")), (("C11", "1"), ("C12", "1")),
             (("C12", "1"), ("FB1", "2")),
             (("U5", "18"), ("C13", "1")), (("C13", "1"), ("JP1", "2")), (("U5", "20"), ("C13", "2")),
             (("C7", "2"), ("C11", "2")), (("C11", "2"), ("C6", "2")),
             (("U6", "8"), ("R16", "1")),
             (("U6", "6"), ("U6", "7")), (("U6", "7"), ("C18", "1")), (("U6", "6"), ("C20", "1")),
             (("C20", "1"), ("C19", "1")), (("C19", "1"), ("C17", "1")),
             (("U4", "3"), ("C5", "1")), (("U4", "1"), ("C4", "1")),
             (("U5", "42"), ("C16", "1")), (("C16", "1"), ("R12", "1"))]

_unplaced = sorted({p.ref for p in PARTS} - set(PLACEMENT))
assert not _unplaced, f"parts without a board position: {_unplaced}"
for _p in PARTS:
    _p.pcb = PLACEMENT[_p.ref]

TEXTS = [
    # back: under the LDO and its capacitors, whose courtyards keep the ground-stitching vias out
    # (pcb_build.stitch avoids front courtyards); line 2 sits between two rows of the 2.54 mm stitching grid
    {"text": "EoS KL25 Board  rev A", "x": 27.5, "y": 44.0, "size": 1.0, "layer": "B_SilkS", "bold": True, "mirror": True},
    {"text": "(c) 2026 Kartikeydheer Srivastava", "x": 27.5, "y": 46.0, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    {"text": "All rights reserved", "x": 27.5, "y": 47.4, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    # front: which USB-C is which, the reset button, the SWD header and its pin 1, and the two jumpers
    {"text": "KL25 USB", "x": 4.2, "y": 5.8, "size": 1.0},
    {"text": "UART/PWR", "x": 4.3, "y": 30.8, "size": 1.0},
    {"text": "RESET", "x": 26.9, "y": 37.0, "size": 1.0, "angle": 90},
    {"text": "SWD", "x": 38.9, "y": 33.2, "size": 1.0},
    {"text": "1", "x": 32.4, "y": 34.96, "size": 0.8},
    {"text": "1 VDDA 3 AREF", "x": 30.95, "y": 32.7, "size": 0.8},
    {"text": "0x1E 0x1D", "x": 26.6, "y": 19.0, "size": 0.8},
]

BOARD = Board(
    name="eos-kl25-board",
    title="EoS KL25 Board",
    revision="A",
    date="2026-10-12",
    company=OWNER,
    licence=LICENCE,
    contact=CONTACT,
    licence_terms=LICENCE_TERMS,
    credits=["Uno R3 outline (2700 x 2100 mil) and shield header positions: Matthew Beckler, \"Arduino Uno R3\" "
             "dimension drawing v1.05, Wayne and Layne (wayneandlayne.com/files/common/arduino_uno_drawing.svg); "
             "facts only, no file copied",
             "Uno R3 mounting holes (4 x 3.20 mm at 15.24 / 2.54 / 50.80 / 66.04 / 17.78 / 45.72 mm) and pin order: "
             "Arduino UNO R3 product reference manual (SKU A000066), sections 5 and 5.4 "
             "(docs.arduino.cc/resources/datasheets/A000066-datasheet.pdf); facts only",
             "Uno R3 header positions cross-checked against KiCad 10's Module:Arduino_UNO_R3_WithMountingHoles footprint "
             "(KiCad libraries, CC BY-SA 4.0); positions only, the footprint is not used"],
    width=W,
    height=H,
    corner_radius=1.0,
    thickness=1.6,
    layers=2,
    parts=PARTS,
    power_nets={"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V"},
    flagged_nets=["GND", "VBUS1", "VBUS1_F", "VBUS2", "VBUS2_F", "VDDA", "VREFH"],
    priority_routes=PRIORITY,
    # the router necks a track to 0.1124 mm to enter a fine-pitch pad; finish() widens such necks to this
    # floor (0.0073 mm a side, inside the router's 0.01 mm extra clearance) and DRC enforces it, so no track
    # is under the 0.127 mm (5 mil) that low-cost two-layer fabs make
    rules={"min_track": 0.127},
    headings=[((35, 62), "KL25 USB-C, ESD, fuse, VBUS detect"), ((35, 135), "Power mux (KL25 USB first), 100 uF"),
              ((35, 195), "3.3 V LDO, power LED"), ((35, 240), "UART USB-C and CP2102N (on 3.3 V, VBUS sensed)"),
              ((280, 62), "MKL25Z128VLK4"), ((280, 285), "Decoupling, VOUT33, VDDA/VREFH (RM 28.6)"),
              ((400, 72), "8 MHz crystal (low-power mode)"), ((400, 125), "Reset and NMI (KLQRUG 2.1.3.4.1)"),
              ((495, 72), "SWD"), ((400, 160), "Accelerometer, I2C1"), ((400, 232), "RGB LED, switched from 5 V"),
              ((530, 62), "Uno R3 shield headers"), ((525, 180), "Extra I/O"),
              ((40, 382), "Mounting holes"), ((35, 352), "Power nets")],
    power_block=(40.64, 360.0),
    notes=[((260, 360), "EoS KL25 Board, rev A. Designed by Kartikeydheer Srivastava. Fits Uno R3 shields; 3.3 V I/O.\n"
                       "Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved; see LICENSE.txt.\n"
                       "Values from NXP KL25P80M48SF0 (data sheet), KL25P80M48SF0RM, KLQRUG, AN3208, AN1706;\n"
                       "Silicon Labs CP2102N Rev. 1.5, TI SLVSFG1A (TPS2116), Diodes DS37274 (AP7361C), ST LIS2HH12.\n"
                       "Firmware: run the 8 MHz oscillator in low-power mode (MCG_C2[HGO] = 0): high-gain mode\n"
                       "would overdrive the crystal (AN3208 Eqn. 1), and RF must not be fitted (DS Table 19)."),
           ((400, 330), "Power: J1 (KL25 USB) or J2 (UART USB), each through its PTC fuse to the TPS2116,\n"
                        "which takes J1 whenever it is present and blocks reverse current. The CP2102N runs\n"
                        "from 3.3 V and senses J2's VBUS (R15, R16); R27 bleeds mux leakage off VBUS2, so it\n"
                        "connects only when a host is on J2.")],
    # The mux rails (VBUS after the fuses, 5 V) are 0.3 mm, not 0.4: a 0.4 mm track cannot leave a
    # 0.3 mm TPS2116 pad between neighbours 0.5 mm apart with 0.15 mm clearance (the maze needs
    # 0.39 mm from the pad's centre line to the neighbour; there is 0.35). The fuses hold 0.5 A.
    netclasses={"Power": {"track": 0.4, "clearance": 0.15}, "Supply": {"track": 0.3, "clearance": 0.15},
                "USB": {"track": 0.2, "clearance": 0.15}},
    net_to_class={"VBUS1": "Power", "VBUS2": "Power", "VBUS1_F": "Supply", "VBUS2_F": "Supply", "+5V": "Supply",
                  "+3V3": "Supply", "VOUT33": "Supply", "VDDA": "Supply",
                  "USB1_DP": "USB", "USB1_DM": "USB", "KL_DP": "USB", "KL_DM": "USB",
                  "USB2_DP": "USB", "USB2_DM": "USB"},
)
