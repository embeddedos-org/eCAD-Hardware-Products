"""EoS ATmega328P Board: an ATmega328P development board in the Uno R3 shield format, designed by Kartikeydheer Srivastava.

Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved: this design file is not under
the repository's MIT licence; see boards/eos/eos-atmega328p-board/LICENSE.txt.

A 68.58 x 53.34 mm two-layer board for the Microchip ATmega328P-AU (TQFP-32) at 5 V and
16 MHz, with its shield headers, ICSP header and mounting holes where Uno R3 shields expect
them. The circuit is drawn from the chip makers' datasheets; no vendor board file was used.
Mechanical facts and their sources (origin top-left, y down; the sources use mils from the
lower-left corner, y up):

* Outline 2700 x 2100 mil = 68.58 x 53.34 mm: Matthew Beckler's "Arduino Uno R3" dimension
  drawing v1.05 (Wayne and Layne, public domain). The drawing's chamfered right-hand corners
  are not copied: the generator draws a rounded rectangle on the same bounding box.
* Mounting holes, 3.2 mm, at (600, 2000), (550, 100), (2600, 1400) and (2600, 300) mil:
  the Beckler drawing; Arduino's UNO R3 product reference manual (A000066), section 5.4,
  gives the same 15.24 / 2.54 / 66.04 / 17.78 / 45.72 / 50.80 mm figures and the 3.20 mm
  diameter. Holes are unplated: at 2.54 mm from the edge a plated ring would reach it.
* Shield headers, from the Beckler drawing, checked against KiCad 10's
  Module:Arduino_UNO_R3_WithMountingHoles footprint: digital 10-pin from 740 mil and 8-pin
  from 1800 mil on the 2000-mil row (D7 to D8 is 160 mil, not 100); power 8-pin from 1100
  mil and analog 6-pin from 2000 mil on the 100-mil row. ICSP pin 1 at (2505, 1200) mil.

The R3 pinout puts the 10-pin socket's end 0.69 mm from the top-left hole's edge, so the two
courtyards overlap on top. H1 is placed from the back, which is where its standoff goes; a
screw head on top would hit the socket, on this board as on any with the R3 pinout.

The barrel jack is not at the Uno R3's height. The drawings put the Uno R3's jack at -75 to 450
mil across and 125 to 475 mil up (y 41.3-50.2 mm from the top edge here). Every horizontal
5.5 mm jack in KiCad's library is 14-16 mm long against the Uno R3's 13.3 mm, so at that height
the PJ-102AH's body would cover hole H2, or would have to overhang the edge by 5 mm. It sits
as low as H2's screw head allows instead (body y 36.2-47.7 mm, about 4 mm higher, over the
same x), and overhangs the left edge by about 2 mm, as the Uno R3's does. A shield with parts on
its underside over x < 14 mm, y 36-41 mm should be checked. The USB-C receptacle's shell
stands proud of the left edge, as HRO's recommended layout for the TYPE-C-31-M-12 shows.

Every value follows a datasheet:

* ATmega328P (Microchip DS40002061B, "ATmega48A/PA/88A/PA/168A/PA/328/P"): 100 nF at each
  VCC/GND pair (pins 4/3 and 6/5) as AN2519 section 2.1 asks ("a decoupling capacitor for every
  pair of pins"), plus 10 uF bulk near the chip (AN2519 2.1: "the main power supply should also
  have a tantalum or ceramic capacitor"). AVCC through 10 uH with 100 nF (datasheet section
  24.6.2 b and Figure 24-9; section 1.1.7 asks for a low-pass filter when the ADC is used).
  100 nF on AREF (AN2519 2.2: "AREF must also be decoupled. The typical value ... is 100 nF").
  The speed grade (section 29.3) runs linearly from 10 MHz at 2.7 V to 20 MHz at 4.5 V, so
  16 MHz needs at least 3.78 V; the MCU runs from the 5 V rail.
* Crystal: ECS-160-12-33Q-JES-TR, 16 MHz, CL = 12 pF, ESR 80 ohm max, shunt capacitance C0 7 pF
  max, drive level 100 uW max (ECS ECX-33Q datasheet, Rev. 2023; "JES" = +-20 ppm tolerance,
  +-50 ppm stability, -40 to +125 C). ECS: "Crystal is symmetrical, pads 1 & 3 are
  interchangeable", so pad 1 takes XTAL1 and pad 3 XTAL2: each line then reaches its own pad
  without crossing the other, and each load capacitor sits beside its own pad.
  AN2519 section 5.2, Equation 2: Ce + Ci = 2 CL - Cs, so Ce = 2 x 12 pF - (Ci + Cs). Taking
  Ci + Cs = 6 pF per pin (AN2519 puts the board's stray Cs at 2-5 pF; the XTAL pin adds a few
  pF) gives Ce = 18 pF, inside the 12-22 pF range the ATmega328P datasheet gives for 8-16 MHz
  crystals (Tables 9-3 and 9-5). If Ci + Cs is really 3-9 pF, the load is 10.5-13.5 pF.
  Fuses: the low-power crystal oscillator, CKSEL3..0 = 1111 and SUT1..0 = 11 (Tables 9-1, 9-3,
  9-4), CKDIV8 unprogrammed: low fuse 0xFF (Table 28-9). A new part runs from its 8 MHz RC
  oscillator divided by 8 (section 9.2.1) until ICSP sets them. Not the full-swing oscillator
  (CKSEL 0111-0110, section 9.4): a rail-to-rail XTAL2 would push roughly 2 pi f (C0 + CL) x
  1.77 V rms = 3.4 mA through 80 ohm, about 0.9 mW against the crystal's 100 uW. Critical
  transconductance 4 ESR (2 pi f)^2 (C0 + CL)^2 = 1.2 mA/V; Microchip gives no oscillator gm,
  so the start-up margin is not known.
* RESET: 10 kohm pull-up (AN2519 section 3: 4.7 kohm or more, and 10 kohm or more for
  debugWIRE), a 1N4148W from RESET to 5 V (AN2519 3: "If HVPP is not used, it is recommended to
  add an ESD protection diode externally from Reset to VCC"), the reset button through 330 ohm
  (AN2519 3.1, Figure 3-2). No capacitor to GND: AN2519 3 says it is optional and stops
  debugWIRE. Auto-reset: CH340C DTR#, buffered by an open-drain U10, through 220 ohm, 100 nF
  and solder jumper JP1 to RESET; the pulse stays below 0.2 VCC for about 80 us in the worst
  case below and about 0.16 ms typically (the datasheet asks for 2.5 us, section 29.5, Table
  29-11). debugWIRE needs JP1 cut: "Capacitors connected to the RESET pin must be disconnected"
  and "All external reset sources must be disconnected" (DS40002061B section 25.3).
* USB: USB-C as a 5 V sink (5.1 kohm on CC1 and CC2, the Type-C Rd), USBLC6-2SC6 ESD
  protection on D+/D- and VBUS with 100 nF on VBUS at the device (ST DS4260 Rev 7, Figure 17,
  CBUS = 100 nF), 500 mA polyfuse (Littelfuse 1206L series datasheet: 1206L050 holds 0.50 A,
  trips at 1.00 A, 6 V, R 0.150 ohm min, R1max 0.700 ohm). A USBLC6-style part, with diodes
  from D+/D- to its VBUS pin, is safe here because the CH340C senses no VBUS: it has no VBUS
  pin (CH340 V3D section 4) and is itself powered from VUSB, so its D+ pull-up dies with the
  host's VBUS and cannot hold VBUS up after an unplug. U1 sits turned so that each line runs
  in on one pin and out of the opposite one (D- 4 -> 3, D+ 6 -> 1), ST's flow-through layout
  (DS4260 section 2.3, Figure 6).
* USB-UART: WCH CH340C (CH340 datasheet V3D). Chosen over the CP2102N because it runs from 5 V
  with 5 V logic, so TXD/RXD/DTR# meet the ATmega328P at its own level, and it needs no crystal
  ("CH340C/N/K/E/X/B has a built-in clock"). It is bus-powered, from VUSB after the polyfuse,
  so it runs only while a host supplies VBUS and its D+ pull-up is not powered without VBUS.
  Its 5 V range is 4.0-5.3 V (section 6.2); USB 2.0 VBUS is 4.40-5.25 V (section 7.3.2), and
  after F1 (0.7 ohm at most) that leaves at least 4.33 V at a 4.40 V low-power port (100 mA)
  and 4.40 V at a 4.75 V high-power port (500 mA). 100 nF on VCC (section 4:
  "requires an external 0.1uF power decoupling capacitor") and 100 nF on V3, which is not tied
  to VCC at 5 V (sections 4 and 5.1); UD+/UD- go straight to the connector ("without a series
  resistor"); R232 to GND; unused MODEM inputs left open ("The unused I/O pins of CH340 can be
  dangled").
* CH340C to ATmega328P: the CH340C runs from VBUS and the MCU from the 5 V rail, which the jack
  can power alone. WCH allows no pin above VCC + 0.5 V (section 6.1) and says that, apart from
  CH340C parts of lot 4 and later, a CH340 powered separately from its MCU needs an
  anti-injection circuit (section 7.7). Lots cannot be ordered, so every line between the two
  goes through an Ioff-rated buffer powered from VUSB: SN74LVC1G17 Schmitt buffers (TI
  SCES351Y) U8 for D1 -> RXD and U9 for TXD -> D0, and an SN74LVC1G07 open-drain buffer (TI
  SCES296AG) U10 for DTR# -> RESET. With VUSB at 0 V, an input or output held at up to 5.5 V
  passes at most 10 uA (Ioff, SCES351Y and SCES296AG section 5.5), so nothing on the 5 V side
  reaches the CH340C's pins; the CH340C only ever sees outputs powered from its own VCC. A
  10 kohm bleeder on VUSB (R14) turns those leakages (U8's input, U9's and U10's outputs, at
  most 30 uA) into at most 0.3 V, under the 0.8 V vSafe0V a USB-C source checks before it
  applies VBUS.
  - Levels: the buffers run from 4.33-5.25 V. The LVC1G17s' inputs accept 0-5.5 V at any VCC
    (section 5.3), VT+ is at most 3.33 V (VCC 5.5 V) and VT- at least 0.89 V (VCC 3 V and
    up, section 5.5). Both drivers clear that: the ATmega328P's outputs, which only see a
    CMOS input here, and the CH340C's (VOH >= VCC - 0.6 V = 3.73 V, VOL <= 0.5 V, CH340
    section 6.2). Buffer outputs give VOH >= VCC - 0.1 V and VOL <= 0.1 V at 100 uA, so RXD
    reads low (its built-in pull-up sinks at most 300 uA, IUP; VIL 0.9 V) and D0 reads high
    (VIH = 0.6 VCC = 3.06 V at 5.1 V, DS40002061B Table 30-1).
  - D0: U9 drives D0 through 1 kohm (R6), which limits a shield driving D0 to 5 mA and the
    current into the MCU in the moment VBUS arrives before the 5 V rail does. 10 kohm (R13)
    holds D0 high while U9 is unpowered (WCH section 7.7 suggests 2-22 kohm on the MCU's RXD);
    with U9 low, D0 = 0.1 V + 5.1 V x 1 / 11 = 0.56 V, under VIL = 0.3 VCC.
  - D1: 100 kohm (R7) to 5 V holds U8's input high while the MCU's TXD is tri-stated (reset,
    bootloader start); TI asks that inputs never float (section 5.3, note 1).
  - DTR# -> RESET: U10 (SN74LVC1G07, open drain, on VUSB), then 220 ohm (R12), 100 nF (C11)
    and JP1. U10's output is pulled up to the MCU's own +5V by 10 kohm (R15), and its input
    to VUSB by 100 kohm (R16), so it is never left floating (SCES296AG 5.3 note 1) while the
    CH340C resets. U10's input sees the CH340C's VOH >= VCC - 0.6 V (0.86 VCC at 4.33 V) and
    VOL <= 0.5 V, against VIH 0.7 VCC and VIL 0.3 VCC (SCES296AG 5.3; its 4.5-5.5 V rows,
    applied down to the 4.33 V VUSB minimum: Inferred). When DTR# falls, U10 sinks about
    1.2 mA and RESET drops to VOL + (Vrail - VOL) x R12 / (Rpu + R12), with Rpu = 10 kohm ||
    the MCU's own 30-60 kohm pull-up (Table 30-1). Worst case: rail 5.1 V (the jack's 5.0 V
    +-1 % with margin), Rpu 7.5 kohm, VOL 0.4 V (TI guarantees 0.4 V at 16 mA and VCC 3 V; at
    1.2 mA and 4.33 V or more it is lower): RESET falls to 0.53 V, under the 1.02 V (0.2 VCC)
    a reset needs (Table 29-11), and stays below it for (Rpu + R12) C11 ln(4.57 / 4.08), about
    80 us with C11 10 % low. Because the swing starts from the MCU's rail, not from VUSB, a
    low VBUS no longer eats into this margin. When VUSB collapses (USB unplugged while the
    jack powers the board), U10's input follows VUSB through R16 and the CH340C's DTR#, so the
    output stays off: its input follows its own falling supply, and with VCC at 0 V "the Ioff
    circuitry disables the outputs" (SCES296AG 7.1), so DTR_BUF stays at +5V and no falling edge
    reaches RESET. 220 ohm holds the current
    through U10 to 23 mA when an ISP programmer drives RESET (IOL 32 mA, abs. max 50 mA); a
    reset-button press, or a programmer pulling RESET low, pushes the R12 end below GND into
    U10's output clamp, at most 9 mA for about 55 us (button) or 23 mA for about 22 us
    (programmer), inside the 50 mA output clamp rating (SCES296AG 5.1).
  - USB current: before its USB configuration completes the CH340C reads DTR# as a
    configuration input; WCH's 4.7 kohm pull-down there asks the host for a larger supply
    current (section 5.1). It is not fitted: it would hold U10's input low during every plug-in
    and unplug, and reset the MCU. The CH340C therefore asks for its default current, which
    WCH does not state for the CH340C (the CH340B's configuration table defaults to 31H, 98 mA).
* Barrel jack (Same Sky PJ-102AH, 2.0 mm pin, connector rated 5 A): the board takes 7-12 V,
  centre positive. Below 7 V the buck drops out (a 5 V adapter leaves it at about 4.6 V, inside
  the mux's 3.96-4.64 V switch-over band); above 12 V nothing on the board clamps a hot-plug
  surge, and the AP63205's absolute maximum is 35 V (40 V for 400 ms). A B240A Schottky
  (Diodes DS13004: 40 V, 2 A, VF 0.50 V at 2 A) blocks reverse polarity; after it the supply is
  VIN, which also reaches the VIN header pin. VIN is rated 1 A: D1 carries 2 A, but its 0.4 mm
  tracks carry about 1.2 A for a 10 C rise (IPC-2221, 1 oz outer layer).
* 5 V from the jack: AP63205 buck (Diodes DS41326: 3.8-32 V in, 5.0 V out, 2 A) with its
  Table 3 values: L = 4.7 uH, C1 = 10 uF, C2 = 2 x 22 uF, C3 (BST) = 100 nF; EN tied to VIN
  ("can be directly connected to VIN"). Its high-side current limit is 2.5-3.1 A (Electrical
  Characteristics, IPEAK_LIMIT), so L1 must not saturate below 3.1 A: Bourns SRP5030T-4R7M,
  4.7 uH +-20 %, Isat 6.0 A, Irms 4.6 A, DCR 53 mohm max (Bourns SRP5030T datasheet). The
  0.3 mm 5 V tracks limit this path to about 1 A.
* Power selection: TI TPS2116 power mux (SLVSFG1A) in priority mode: MODE tied to VIN1 (the
  buck's 5 V) and PR1 fed from VIN1 through 33 kohm / 10 kohm, so PR1 = 1.16 V at 5.0 V, above
  VREF (0.92-1.08 V); the jack's 5 V is used whenever it is above 4.3 V (3.96-4.64 V), and USB
  otherwise. Its reverse-current blocking (section 7.3.4) means the two inputs never feed each
  other, and 5 V fed into the 5V header pin reaches neither the USB host nor the buck. 1 uF on
  VIN2 (section 9); on VOUT, 10 uF ceramic at U3's VOUT pins plus 100 uF bulk (section 7.3.4:
  "a high output capacitance (about 100uF)" when reverse blocking can occur). ST is not used.
* 3.3 V: Diodes AP2112K-3.3 LDO (DS39724), 600 mA, 1 uF ceramic in and out as its typical
  application shows, EN tied to VIN. At 184 C/W (SOT25), 250 mA from 5.0 V (0.43 W) keeps the
  junction at 125 C only up to about 47 C ambient (42 C from 5.1 V); derate above that.
* LEDs: Kingbright APTD1608LCGCK (green, power) and APTD1608LSYCK (yellow, "L"), both
  specified at 2 mA (VF 1.9 V and 1.85 V typical): (5 V - 1.9 V) / 1.5 kohm = 2.1 mA. The L
  LED is driven by a TI SN74LVC1G17 Schmitt buffer (SCES351Y: CI 4.5 pF, II 5 uA max) on D13,
  so D13 still works as SPI SCK; 100 kohm holds the buffer input low while D13 is an input
  (TI section 5.3, note 1: inputs must be held at VCC or GND), and 100 nF on its VCC (TI
  section 8.3). With D13's internal pull-up (20-50 kohm) enabled the pin still reads high:
  5 V x 100 / 150 = 3.3 V, above VIH = 0.6 VCC.

Two layers, ground poured on both sides. The autorouter gives a different result on every run,
so the lines that matter are laid first as priority routes, top layer:
* Crystal: each XTAL pin to its crystal pad, then on to its load capacitor (AN2519 section 5.6:
  crystal "as close as possible to the AVR device", "surrounding it with a ground plane").
  Router keep-outs around the crystal and its capacitors keep other top-layer tracks out, so
  the top pour surrounds them.
* MCU decoupling: VCC pins 6 and 4 and GND pins 5 and 3 to their own 100 nF (AN2519 2.1).
* USB: connector B7 -> U1 4 -> 3 -> CH340C UD- and B6 -> U1 6 -> 1 -> UD+, then A6 and A7 joined
  to their B twins (the USB-C receptacle duplicates each data contact, in the order B7 D-, A6
  D+, A7 D-, B6 D+, so the two ties cross: A6 joins B6 behind the pad row, A7 joins B7 by a
  short loop in front of A6's pad, as on EoS TM4C123 Board); CH340C VCC and V3 to their
  capacitors. The CH340C's UD- and UD+ are reached from below, under its body, so the pair
  never crosses.
* D0-D4, from the MCU's lower right to the digital header, laid around the right of the
  crystal block, so the autorouter does not run them diagonally under it as it did before.
  A keep-out inside the MCU's pad ring stops them taking the way round the crystal's MCU side.
* The TPS2116's VOUT to its 100 uF.
"""

from __future__ import annotations

from ..design import NC, USB_C_EDGE, Board, Part
from .owner import CONTACT, LICENCE, LICENCE_TERMS, OWNER

R0603 = "Resistor_SMD:R_0603_1608Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C1206 = "Capacitor_SMD:C_1206_3216Metric"
HOLE = "MountingHole:MountingHole_3.2mm_M3_ISO14580"

MCU_DS = "Microchip DS40002061B"
AN2519 = "Microchip AN2519 (DS00002519B)"


def res(ref, value, a, b, sch, desc, rot=0):
    return Part(ref, "Device:R_Small", value, R0603, sch, {"1": a, "2": b}, fields={"Description": desc},
                sch_rotation=rot)


def cap(ref, value, a, b, sch, desc, fp=C0603, rot=0):
    return Part(ref, "Device:C_Small", value, fp, sch, {"1": a, "2": b}, fields={"Description": desc},
                sch_rotation=rot)


def socket(ref, n, value, pins, sch, desc):
    """A female header for shields: pin 1 is the first signal named in ``pins``."""
    return Part(ref, f"Connector:Conn_01x{n:02d}_Socket", value,
                f"Connector_PinSocket_2.54mm:PinSocket_1x{n:02d}_P2.54mm_Vertical", sch,
                {str(i + 1): net for i, net in enumerate(pins)},
                fields={"Manufacturer": "Samtec", "MPN": f"SSW-1{n:02d}-01-T-S", "Description": desc})


def iso_buffer(ref, a, y, sch, what):
    """An SN74LVC1G17 powered from VUSB between the CH340C and the 5 V side (see the docstring)."""
    return Part(ref, "74xGxx:74LVC1G17", "SN74LVC1G17", "Package_TO_SOT_SMD:SOT-23-5", sch,
                {"2": a, "4": y, "VCC": "VUSB", "GND": "GND", "NC": NC},
                fields={"Manufacturer": "Texas Instruments", "MPN": "SN74LVC1G17DBVR",
                        "Description": f"Schmitt buffer on VUSB, {what}: Ioff 10 uA max unpowered (TI SCES351Y 5.5)"})


W, H = 68.58, 53.34          # 2700 x 2100 mil
MIL = 0.0254


def uno(x_mil, y_mil):
    """A position from the Uno R3 drawings (mils from the lower-left corner, y up) in board mm."""
    return round(x_mil * MIL, 4), round(H - y_mil * MIL, 4)


# Shield headers, by pin 1, and the ICSP header (positions: see the module docstring).
D0_PIN = uno(2500, 2000)      # D0 .. D7 run right to left, 100 mil apart
D8_PIN = uno(1640, 2000)      # D8 .. D13, GND, AREF, SDA, SCL run right to left
POWER_PIN = uno(1100, 100)    # NC, IOREF, RESET, 3V3, 5V, GND, GND, VIN run left to right
A0_PIN = uno(2000, 100)       # A0 .. A5 run left to right
ICSP_PIN = uno(2505, 1200)    # pin 1 (MISO); pins 1-3-5 run down, 2-4-6 one column to the right
HOLES = [uno(600, 2000), uno(550, 100), uno(2600, 1400), uno(2600, 300)]

PARTS = [
    # ---- USB-C, ESD, fuse ------------------------------------------------------------------------
    Part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
         (50, 110), {"VBUS": "VBUS", "GND": "GND", "CC1": "CC1", "CC2": "CC2", "D+": "USB_D+", "D-": "USB_D-",
                     "SBU1": NC, "SBU2": NC, "SHIELD": "GND"},
         fields={"Manufacturer": "Korean Hroparts", "MPN": "TYPE-C-31-M-12", "Description": "USB-C 2.0 receptacle, 16 pins"}),
    res("R1", "5.1k", "CC1", "GND", (90, 95), "Resistor 5.1 kohm 1% 0603 (USB-C sink Rd on CC1, USB Type-C specification)"),
    res("R2", "5.1k", "CC2", "GND", (105, 95), "Resistor 5.1 kohm 1% 0603 (USB-C sink Rd on CC2, USB Type-C specification)"),
    Part("U1", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", (140, 110),
         {"I/O1": "USB_D+", "I/O2": "USB_D-", "GND": "GND", "VBUS": "VBUS"},
         fields={"Manufacturer": "STMicroelectronics", "MPN": "USBLC6-2SC6",
                 "Description": "USB ESD protection, IEC 61000-4-2 level 4 (ST USBLC6-2 datasheet)"}),
    cap("C21", "100n", "VBUS", "GND", (160, 128), "Capacitor 100 nF 50 V X7R 0603 (USBLC6-2 VBUS, ST DS4260 Rev 7 Figure 17, CBUS)"),
    res("R14", "10k", "VUSB", "GND", (195, 100), "Resistor 10 kohm 1% 0603 (VUSB bleeder: buffer Ioff, 30 uA max, gives 0.3 V max without a host)"),
    Part("F1", "Device:Polyfuse_Small", "500mA", "Fuse:Fuse_1206_3216Metric", (175, 95), {"1": "VBUS", "2": "VUSB"},
         fields={"Manufacturer": "Littelfuse", "MPN": "1206L050YR",
                 "Description": "PTC resettable fuse 0.50 A hold, 1.00 A trip, 6 V, R1max 0.70 ohm, 1206 (Littelfuse 1206L series)"}),

    # ---- Barrel jack, reverse-polarity diode, 5 V buck ---------------------------------------------
    Part("J2", "Connector:Barrel_Jack_Switch", "7-12V", "Connector_BarrelJack:BarrelJack_CUI_PJ-102AH_Horizontal",
         (50, 185), {"1": "VJACK", "2": "GND", "3": NC},
         fields={"Manufacturer": "Same Sky", "MPN": "PJ-102AH",
                 "Description": "DC jack 2.0 mm centre pin, connector rated 5 A; board input 7-12 V centre positive (Same Sky PJ-102AH)"}),
    Part("D1", "Device:D_Schottky_Small", "B240A", "Diode_SMD:D_SMA", (85, 175), {"A": "VJACK", "K": "VIN"},
         fields={"Manufacturer": "Diodes Incorporated", "MPN": "B240A-13-F",
                 "Description": "Schottky 40 V 2 A, VF 0.50 V at 2 A, SMA: reverse-polarity protection (Diodes DS13004)"}),
    Part("U2", "Regulator_Switching:AP63205WU", "AP63205", "Package_TO_SOT_SMD:TSOT-23-6", (125, 190),
         {"IN": "VIN", "EN": "VIN", "GND": "GND", "SW": "BUCK_SW", "BST": "BUCK_BST", "FB": "5V_REG"},
         fields={"Manufacturer": "Diodes Incorporated", "MPN": "AP63205WU-7",
                 "Description": "Buck 3.8-32 V in, 5.0 V 2 A out, EN tied to VIN (Diodes DS41326)"}),
    cap("C1", "10u", "VIN", "GND", (100, 205), "Capacitor 10 uF 50 V X5R 1206 (buck input, Diodes DS41326 Table 3 C1)", C1206),
    cap("C2", "100n", "BUCK_SW", "BUCK_BST", (150, 175), "Capacitor 100 nF 50 V X7R 0603 (buck bootstrap, Diodes DS41326 Table 3 C3)"),
    Part("L1", "Device:L_Small", "4.7u", "Inductor_SMD:L_Bourns_SRP5030T", (170, 190), {"1": "BUCK_SW", "2": "5V_REG"},
         fields={"Manufacturer": "Bourns", "MPN": "SRP5030T-4R7M",
                 "Description": "Inductor 4.7 uH, Isat 6.0 A (above the AP63205's 3.1 A limit), Irms 4.6 A, 53 mohm max "
                                "(Diodes DS41326 Table 3 L; Bourns SRP5030T)"}),
    cap("C3", "22u", "5V_REG", "GND", (190, 200), "Capacitor 22 uF 16 V X5R 1206 (buck output, Diodes DS41326 Table 3 C2, 1 of 2)", C1206),
    cap("C4", "22u", "5V_REG", "GND", (205, 200), "Capacitor 22 uF 16 V X5R 1206 (buck output, Diodes DS41326 Table 3 C2, 2 of 2)", C1206),

    # ---- Power mux (jack has priority) and 3.3 V ------------------------------------------------------
    Part("U3", "Power_Management:TPS2116DRL", "TPS2116", "Package_TO_SOT_SMD:SOT-583-8", (250, 115),
         {"VIN1": "5V_REG", "VIN2": "VUSB", "VOUT": "+5V", "GND": "GND", "PR1": "MUX_PR1", "MODE": "5V_REG", "ST": NC},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPS2116DRLR",
                 "Description": "Power mux 2.5 A, priority mode: VIN1 (jack 5 V) first, VIN2 (USB) otherwise (TI SLVSFG1A)"}),
    res("R3", "33k", "5V_REG", "MUX_PR1", (205, 122), "Resistor 33 kohm 1% 0603 (TPS2116 PR1 divider: 1.16 V at 5.0 V, VREF 1.0 V, TI SLVSFG1A 7.6.1.1)", rot=90),
    res("R4", "10k", "MUX_PR1", "GND", (205, 134), "Resistor 10 kohm 1% 0603 (TPS2116 PR1 divider: switches to USB below 4.3 V)", rot=90),
    cap("C20", "10u", "+5V", "GND", (275, 130), "Capacitor 10 uF 16 V X5R 0805 (at TPS2116 VOUT pins, TI SLVSFG1A 7.3.4)", C0805),
    cap("C5", "1u", "VUSB", "GND", (275, 105), "Capacitor 1 uF 16 V X7R 0603 (TPS2116 VIN2, TI SLVSFG1A section 9)"),
    Part("C6", "Device:C_Polarized_Small", "100u", "Capacitor_SMD:CP_Elec_6.3x5.8", (290, 110), {"1": "+5V", "2": "GND"},
         fields={"Manufacturer": "Panasonic", "MPN": "EEE-FK1C101P",
                 "Description": "Capacitor 100 uF 16 V aluminium electrolytic, 6.3 x 5.8 mm (TPS2116 VOUT, TI SLVSFG1A 7.3.4)"}),
    Part("U4", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5", (330, 115),
         {"VIN": "+5V", "EN": "+5V", "GND": "GND", "VOUT": "+3V3", "NC": NC},
         fields={"Manufacturer": "Diodes Incorporated", "MPN": "AP2112K-3.3TRG1",
                 "Description": "LDO 3.3 V 600 mA, SOT-23-5 (Diodes DS39724)"}),
    cap("C7", "1u", "+5V", "GND", (310, 105), "Capacitor 1 uF 16 V X7R 0603 (LDO input, Diodes DS39724 typical application)"),
    cap("C8", "1u", "+3V3", "GND", (355, 105), "Capacitor 1 uF 16 V X7R 0603 (LDO output, Diodes DS39724 typical application)"),
    res("R5", "1.5k", "+5V", "LED_PWR_A", (380, 105), "Resistor 1.5 kohm 1% 0603 (power LED: (5 V - 1.9 V) / 1.5 kohm = 2.1 mA, Kingbright DSAO7432)"),
    Part("D2", "Device:LED_Small", "PWR", "LED_SMD:LED_0603_1608Metric", (395, 105), {"A": "LED_PWR_A", "K": "GND"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LCGCK", "Description": "LED green 0603, VF 1.9 V at 2 mA: power (+5V)"}),

    # ---- USB-UART -------------------------------------------------------------------------------------
    Part("U5", "Interface_USB:CH340C", "CH340C", "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm", (130, 280),
         {"VCC": "VUSB", "GND": "GND", "V3": "CH_V3", "UD+": "USB_D+", "UD-": "USB_D-", "TXD": "CH_TX", "RXD": "CH_RX",
          "~{DTR}": "CH_DTR", "~{RTS}": NC, "~{CTS}": NC, "~{DSR}": NC, "~{RI}": NC, "~{DCD}": NC, "R232": "GND", "NC": NC},
         fields={"Manufacturer": "WCH", "MPN": "CH340C",
                 "Description": "USB to UART, bus-powered from VUSB (4.0-5.3 V), built-in clock; any lot "
                                "(isolated by U8-U10, WCH CH340 datasheet V3D 6.2, 7.7)"}),
    cap("C9", "100n", "VUSB", "GND", (175, 255), "Capacitor 100 nF 50 V X7R 0603 (CH340C VCC on VUSB, WCH CH340 datasheet section 4)"),
    cap("C10", "100n", "CH_V3", "GND", (95, 255), "Capacitor 100 nF 50 V X7R 0603 (CH340C V3 at 5 V supply, WCH CH340 datasheet 5.1)"),
    iso_buffer("U9", "CH_TX", "D0_BUF", (150, 348), "CH340C TXD to D0"),
    iso_buffer("U8", "D1", "CH_RX", (150, 385), "D1 to CH340C RXD"),
    Part("U10", "74xGxx:74LVC1G07", "SN74LVC1G07", "Package_TO_SOT_SMD:SOT-23-5", (230, 385),
         {"2": "CH_DTR", "4": "DTR_BUF", "VCC": "VUSB", "GND": "GND", "NC": NC},
         fields={"Manufacturer": "Texas Instruments", "MPN": "SN74LVC1G07DBVR",
                 "Description": "Open-drain buffer on VUSB, CH340C DTR# to the auto-reset capacitor: output off when "
                                "unpowered, Ioff 10 uA max (TI SCES296AG 5.5, 7.1)"}),
    res("R15", "10k", "DTR_BUF", "+5V", (245, 410), "Resistor 10 kohm 1% 0603 (U10 open-drain pull-up to the MCU's 5 V: "
        "DTR_BUF stays high when VUSB collapses, so unplugging USB cannot reset the MCU)"),
    res("R16", "100k", "CH_DTR", "VUSB", (205, 410), "Resistor 100 kohm 1% 0603 (holds U10's input high while the CH340C "
        "resets; TI SCES296AG 5.3 note 1: inputs held at VCC or GND)"),
    cap("C23", "100n", "VUSB", "GND", (210, 348), "Capacitor 100 nF 50 V X7R 0603 (U9 VCC, TI SCES351Y 8.3)"),
    cap("C22", "100n", "VUSB", "GND", (175, 365), "Capacitor 100 nF 50 V X7R 0603 (U8 VCC, TI SCES351Y 8.3)"),
    cap("C24", "100n", "VUSB", "GND", (245, 360), "Capacitor 100 nF 50 V X7R 0603 (U10 VCC, TI SCES296AG 8.3)"),
    res("R6", "1k", "D0_BUF", "D0", (190, 348), "Resistor 1 kohm 1% 0603 (U9 to D0: a shield driving D0 fights at most 5 mA)", rot=90),
    res("R13", "10k", "+5V", "D0", (125, 348), "Resistor 10 kohm 1% 0603 (D0 pull-up while U9 is unpowered; WCH CH340 7.7: 2-22 kohm on the MCU RXD)"),
    res("R7", "100k", "+5V", "D1", (125, 385), "Resistor 100 kohm 1% 0603 (holds U8's input high while D1 is tri-stated; TI SCES351Y 5.3 note 1)"),
    res("R12", "220", "DTR_BUF", "DTR_C", (272, 385), "Resistor 220 ohm 1% 0603 (auto-reset series: RESET reaches 0.53 V < 0.2 VCC worst case; 23 mA max through U10)", rot=90),
    cap("C11", "100n", "DTR_C", "DTR_JP", (272, 398), "Capacitor 100 nF 50 V X7R 0603 (DTR# auto-reset coupling, about 0.8 ms with the reset pull-ups)", rot=90),
    Part("JP1", "Jumper:SolderJumper_2_Bridged", "AUTO-RST", "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm", (285, 412),
         {"A": "DTR_JP", "B": "RESET"},
         fields={"Description": "Solder jumper, bridged as delivered: cut it for debugWIRE (DS40002061B 25.3: capacitors and "
                                "external reset sources must be disconnected from RESET)"}),

    # ---- ATmega328P -------------------------------------------------------------------------------------
    Part("U6", "MCU_Microchip_ATmega:ATmega328P-A", "ATmega328P-AU", "Package_QFP:TQFP-32_7x7mm_P0.8mm", (300, 260),
         {"VCC": "+5V", "GND": "GND", "AVCC": "AVCC", "AREF": "AREF", "ADC6": NC, "ADC7": NC,
          "XTAL1/PB6": "XTAL1", "XTAL2/PB7": "XTAL2", "~{RESET}/PC6": "RESET",
          "PD0": "D0", "PD1": "D1", "PD2": "D2", "PD3": "D3", "PD4": "D4", "PD5": "D5", "PD6": "D6", "PD7": "D7",
          "PB0": "D8", "PB1": "D9", "PB2": "D10", "PB3": "D11", "PB4": "D12", "PB5": "D13",
          "PC0": "A0", "PC1": "A1", "PC2": "A2", "PC3": "A3", "PC4": "A4_SDA", "PC5": "A5_SCL"},
         fields={"Manufacturer": "Microchip", "MPN": "ATMEGA328P-AU",
                 "Description": f"8-bit AVR, 32 KB flash, 16 MHz at 5 V, TQFP-32 ({MCU_DS})"}),
    cap("C12", "100n", "+5V", "GND", (350, 205), f"Capacitor 100 nF 50 V X7R 0603 (VCC pin 6 / GND pin 5, {AN2519} 2.1)"),
    cap("C13", "100n", "+5V", "GND", (365, 205), f"Capacitor 100 nF 50 V X7R 0603 (VCC pin 4 / GND pin 3, {AN2519} 2.1)"),
    cap("C14", "10u", "+5V", "GND", (380, 205), f"Capacitor 10 uF 16 V X5R 0805 (5 V bulk at the MCU, {AN2519} 2.1)", C0805),
    Part("L2", "Device:L_Small", "10u", "Inductor_SMD:L_Murata_LQH2MCNxxxx02_2.0x1.6mm", (240, 215), {"1": "+5V", "2": "AVCC"},
         fields={"Manufacturer": "Murata", "MPN": "LQH2MCN100K02L",
                 "Description": f"Inductor 10 uH 225 mA, 1.2 ohm +-30 %, 2.0 x 1.6 mm (Murata JELF243A-0053): AVCC LC filter "
                                f"({MCU_DS} 24.6.2, Figure 24-9)"}),
    cap("C15", "100n", "AVCC", "GND", (255, 225), f"Capacitor 100 nF 50 V X7R 0603 (AVCC LC filter, {MCU_DS} Figure 24-9)"),
    cap("C16", "100n", "AREF", "GND", (255, 295), f"Capacitor 100 nF 50 V X7R 0603 (AREF decoupling, {AN2519} 2.2)"),
    Part("Y1", "Device:Crystal_GND24", "16MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", (235, 260),
         {"1": "XTAL1", "3": "XTAL2", "2": "GND", "4": "GND"},
         fields={"Manufacturer": "ECS Inc.", "MPN": "ECS-160-12-33Q-JES-TR",
                 "Description": "Crystal 16 MHz, CL 12 pF, +-20 ppm tolerance, +-50 ppm stability, -40 to 125 C, "
                                "ESR 80 ohm max, C0 7 pF max, drive level 100 uW max, 3.2 x 2.5 mm; pads 1 and 3 "
                                "interchangeable (ECS ECX-33Q Rev. 2023, JES); low-power oscillator fuses only"}),
    Part("C17", "Device:C_Small", "18p", C0603, (220, 280), {"1": "XTAL1", "2": "GND"},
         fields={"Manufacturer": "Yageo", "MPN": "CC0603JRNPO9BN180",
                 "Description": f"Capacitor 18 pF 5% 50 V C0G 0603 (XTAL1 load: 2 x 12 pF - 6 pF, {AN2519} 5.2 Eq. 2)"}),
    Part("C18", "Device:C_Small", "18p", C0603, (250, 280), {"1": "XTAL2", "2": "GND"},
         fields={"Manufacturer": "Yageo", "MPN": "CC0603JRNPO9BN180",
                 "Description": f"Capacitor 18 pF 5% 50 V C0G 0603 (XTAL2 load: 2 x 12 pF - 6 pF, {AN2519} 5.2 Eq. 2)"}),

    # ---- Reset ---------------------------------------------------------------------------------------------
    res("R8", "10k", "+5V", "RESET", (215, 330), f"Resistor 10 kohm 1% 0603 (RESET pull-up, 10 kohm or more for debugWIRE, {AN2519} 3)"),
    Part("D3", "Device:D_Small", "1N4148W", "Diode_SMD:D_SOD-123", (235, 330), {"A": "RESET", "K": "+5V"},
         fields={"Manufacturer": "Diodes Incorporated", "MPN": "1N4148W-7-F",
                 "Description": f"Diode 1N4148W SOD-123: RESET to 5 V clamp ({AN2519} 3; Diodes DS30086)"}),
    res("R9", "330", "RESET", "RST_SW", (255, 340), f"Resistor 330 ohm 1% 0603 (reset button series resistor, {AN2519} 3.1 Figure 3-2)"),
    Part("SW1", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", (280, 345),
         {"1": "RST_SW", "2": "GND"}, fields={"Manufacturer": "C&K", "MPN": "KMR221G LFS", "Description": "Tactile switch, reset"}),

    # ---- "L" LED on D13, buffered ------------------------------------------------------------------------
    Part("U7", "74xGxx:74LVC1G17", "SN74LVC1G17", "Package_TO_SOT_SMD:SOT-23-5", (420, 255),
         {"2": "D13", "4": "LED_L_DRV", "VCC": "+5V", "GND": "GND", "NC": NC},
         fields={"Manufacturer": "Texas Instruments", "MPN": "SN74LVC1G17DBVR",
                 "Description": "Schmitt buffer for the L LED: D13 sees 4.5 pF, so it stays usable as SCK (TI SCES351Y)"}),
    cap("C19", "100n", "+5V", "GND", (440, 240), "Capacitor 100 nF 50 V X7R 0603 (SN74LVC1G17 VCC, TI SCES351Y 8.3)"),
    res("R10", "100k", "D13", "GND", (400, 270), "Resistor 100 kohm 1% 0603 (buffer input held low while D13 is an input; 5 uA x 100 kohm = 0.5 V)"),
    res("R11", "1.5k", "LED_L_DRV", "LED_L_A", (450, 260), "Resistor 1.5 kohm 1% 0603 (L LED: (5 V - 1.85 V) / 1.5 kohm = 2.1 mA, Kingbright DSAO7434)"),
    Part("D4", "Device:LED_Small", "L", "LED_SMD:LED_0603_1608Metric", (470, 260), {"A": "LED_L_A", "K": "GND"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LSYCK", "Description": "LED yellow 0603, VF 1.85 V at 2 mA: L (D13)"}),

    # ---- Shield headers and ICSP ----------------------------------------------------------------------------
    socket("J3", 8, "D0-D7", ["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7"], (505, 110),
           "Socket 1x8 2.54 mm, Uno R3 digital D0-D7 (pin 1 = D0)"),
    socket("J4", 10, "D8-SCL", ["D8", "D9", "D10", "D11", "D12", "D13", "GND", "AREF", "A4_SDA", "A5_SCL"], (505, 175),
           "Socket 1x10 2.54 mm, Uno R3 digital D8-D13, GND, AREF, SDA, SCL (pin 1 = D8)"),
    socket("J5", 8, "POWER", [NC, "+5V", "RESET", "+3V3", "+5V", "GND", "GND", "VIN"], (545, 110),
           "Socket 1x8 2.54 mm, Uno R3 power: NC, IOREF (5 V), RESET, 3V3, 5V, GND, GND, VIN (pin 1 = NC)"),
    socket("J6", 6, "A0-A5", ["A0", "A1", "A2", "A3", "A4_SDA", "A5_SCL"], (545, 180),
           "Socket 1x6 2.54 mm, Uno R3 analog A0-A5 (pin 1 = A0)"),
    Part("J7", "Connector:AVR-ISP-6", "ICSP", "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical", (525, 255),
         {"MISO": "D12", "VCC": "+5V", "SCK": "D13", "MOSI": "D11", "~{RST}": "RESET", "GND": "GND"},
         fields={"Manufacturer": "Samtec", "MPN": "TSW-103-07-G-D",
                 "Description": f"Header 2x3 2.54 mm, unshrouded, so a shield that takes SPI from the ICSP position "
                                f"still mates: AVR ISP for the ATmega328P (SPI and RESET, {AN2519} 4.1)"}),
]
for i, label in enumerate(["top left", "bottom left", "right, upper", "right, lower"]):
    PARTS.append(Part(f"H{i + 1}", "Mechanical:MountingHole", "M3", HOLE, (45 + 15 * i, 362), {},
                      side="B" if i == 0 else "F",
                      fields={"Description": f"Mounting hole 3.2 mm, unplated, Uno R3 position ({label})"}))

# Board placement: (x, y, rotation) in mm, origin top-left. USB-C and the barrel jack on the left
# edge, roughly where the Uno R3 drawings show its USB and power jacks; shield headers, ICSP and
# holes exactly where the drawings put them. The MCU sits under the digital headers, turned so its
# PB4..PD5 side faces D12..D5; crystal and decoupling on its right, AVCC filter on its left, reset
# parts below it. Power on the lower left, the L LED and its buffer on the lower right; a corridor
# is kept clear right of the power parts for A0..A5.
PLACEMENT = {
    "J3": (D0_PIN[0], D0_PIN[1], 270), "J4": (D8_PIN[0], D8_PIN[1], 270),
    "J5": (POWER_PIN[0], POWER_PIN[1], 90), "J6": (A0_PIN[0], A0_PIN[1], 90),
    "J7": (ICSP_PIN[0], ICSP_PIN[1], 0),
    **{f"H{i + 1}": (x, y, 0) for i, (x, y) in enumerate(HOLES)},
    # USB-C, ESD, CC resistors, fuse. U1 is turned so that each line runs straight through it,
    # in on one pin and out of the opposite one (D- 4 -> 3 on top, D+ 6 -> 1 below), as the
    # connector's B7 (D-) and B6 (D+) contacts are ordered
    "J1": (USB_C_EDGE, 15.24, 270), "U1": (11.9, 15.24, 180), "R1": (11.0, 9.9, 0), "R2": (11.0, 19.9, 0),
    "C21": (11.8, 12.1, 0), "F1": (12.0, 23.4, 0), "R14": (12.0, 26.2, 0),
    # CH340C beside the USB-C, its UD-/UD+ pins reached from below, under its body; below it a row
    # of the three VUSB buffers (DTR#, RXD, TXD), their capacitors above them and the DTR#
    # resistor/capacitor/jumper, pull-ups and D0 resistor below
    "U5": (21.5, 15.3, 270), "C10": (22.6, 9.6, 0), "C9": (28.5, 17.0, 90),
    "U10": (22.0, 23.2, 0), "U8": (27.0, 23.2, 0), "U9": (32.0, 23.2, 0),
    "C24": (23.1, 20.3, 0), "C22": (28.1, 20.3, 0), "C23": (31.4, 20.3, 0),
    "R16": (18.2, 23.2, 90), "R15": (20.0, 28.4, 0), "JP1": (23.2, 28.6, 180),
    "R12": (20.0, 26.6, 0), "C11": (23.6, 26.6, 0), "R7": (27.2, 26.6, 0), "R13": (30.8, 26.6, 0),
    "R6": (34.4, 26.9, 90),
    # ATmega328P; the crystal beside XTAL1/XTAL2 (pins 7/8), its load capacitors beside their own
    # pads (C17 right of pad 1, C18 above pad 3); 100 nF upright beside each VCC/GND pair
    # (pins 6/5, 4/3), 10 uF bulk beyond them; AVCC filter on the MCU's left
    "U6": (41.0, 17.0, 180),
    "Y1": (48.6, 12.2, 90), "C17": (51.85, 13.3, 0), "C18": (47.75, 8.6, 90),
    "C12": (47.4, 16.2, 270), "C13": (49.2, 18.0, 270), "C14": (51.9, 18.3, 90),
    "L2": (31.8, 14.6, 90), "C15": (34.1, 15.2, 90), "C16": (34.1, 18.4, 90),
    # reset: pull-up and clamp below the MCU, button by the ICSP header
    "R8": (42.4, 26.6, 90), "D3": (44.7, 26.6, 90), "R9": (51.5, 27.0, 0), "SW1": (56.5, 27.0, 0),
    # L LED and its buffer
    "U7": (56.0, 34.0, 0), "C19": (59.8, 33.0, 90), "R10": (52.2, 34.0, 90), "R11": (56.0, 37.6, 0),
    "D4": (59.6, 37.6, 180),
    # barrel jack, reverse-polarity diode, buck
    "J2": (12.0, 41.2, 270), "D1": (19.0, 41.2, 180), "U2": (26.5, 40.2, 0), "C1": (26.5, 43.6, 0),
    "C2": (29.8, 37.8, 90), "L1": (33.0, 42.3, 0), "C3": (38.4, 42.3, 90), "C4": (41.0, 42.3, 90),
    # power mux, its VIN2 capacitor below it and its output capacitors: 10 uF at the VOUT pins and
    # the 100 uF beside it (TI SLVSFG1A 7.3.4); 3.3 V LDO; the power LED by the left edge
    "U3": (37.6, 36.0, 0), "C20": (37.6, 32.6, 0), "R3": (33.6, 35.4, 0), "R4": (33.6, 37.3, 0), "C5": (40.5, 38.0, 90),
    "C6": (46.4, 35.8, 0), "U4": (29.0, 31.5, 0), "C7": (25.6, 31.4, 90), "C8": (32.4, 31.4, 90),
    "R5": (11.0, 30.5, 90), "D2": (13.0, 30.5, 90),
}
# Laid first, in this order, before the autorouter (see the docstring): the crystal, the MCU's
# decoupling (C12, C13, then C14's 10 uF from C13's 5 V pad, before D0-D4 cross that gap),
# the USB pair (the TM4C123 board's pattern: connector -> ESD -> bridge, then the
# duplicated contacts joined), the CH340C's decoupling, D4..D0 around the crystal block, and
# the TPS2116's bulk capacitor.
PRIORITY = [(("U6", "7"), ("Y1", "1")), (("Y1", "1"), ("C17", "1")),
            (("U6", "8"), ("Y1", "3")), (("Y1", "3"), ("C18", "1")),
            (("U6", "6"), ("C12", "1")), (("U6", "5"), ("C12", "2")),
            (("U6", "4"), ("C13", "1")), (("U6", "3"), ("C13", "2")),
            (("C13", "1"), ("C14", "1")),
            (("J1", "B7"), ("U1", "4")), (("U1", "4"), ("U1", "3")), (("U1", "3"), ("U5", "6")),
            (("J1", "B6"), ("U1", "6")), (("U1", "6"), ("U1", "1")), (("U1", "1"), ("U5", "5")),
            (("J1", "A6"), ("J1", "B6"), "join"), (("J1", "A7"), ("J1", "B7"), "join"),
            (("U5", "16"), ("C9", "1")), (("U5", "4"), ("C10", "1")),
            (("U6", "2"), ("J3", "5")), (("U6", "1"), ("J3", "4")), (("U6", "32"), ("J3", "3")),
            (("U6", "31"), ("J3", "2")), (("U6", "30"), ("J3", "1")),
            (("U3", "7"), ("C6", "1"))]
# Top-layer keep-outs (router and priority routes alike) round the crystal block, open only on
# the MCU's side where XTAL1/XTAL2 come in: above C18, left of C18, right of Y1 and above C17,
# and below C17. Inside the MCU's pad ring, so no top-layer track runs under the package (D4
# took that way round the crystal's MCU side before). Between L1's pads, so nothing runs under
# the inductor on top.
KEEPOUTS = [(45.9, 6.2, 48.3, 7.1), (45.9, 7.1, 46.95, 10.2), (48.3, 6.2, 53.5, 12.9), (50.3, 13.9, 53.5, 16.4),
            (37.75, 13.75, 44.25, 20.25), (31.95, 40.0, 34.05, 44.6)]
_unplaced = sorted({p.ref for p in PARTS} - set(PLACEMENT))
assert not _unplaced, f"parts without a board position: {_unplaced}"
for _p in PARTS:
    _p.pcb = PLACEMENT[_p.ref]


LABEL = 0.8           # the board's minimum silk text height


def _label(text, x, y, angle=0.0, end=None):
    """An upright pin name. With ``end`` ("top" or "bottom") the label keeps that end at ``y`` instead of
    centring on it, so a longer name grows away from its header. KiCad's stroke font takes up to the
    text height per character for wide capitals (G, D, S); 0.1 mm more keeps clear of the header's
    outline."""
    half = len(text) * LABEL / 2 + 0.1
    centre = y + half if end == "top" else y - half if end == "bottom" else y
    return {"text": text, "x": x, "y": round(centre, 2), "size": LABEL, "angle": angle}


TEXTS = [
    {"text": "EoS ATmega328P Board  rev A", "x": 34.0, "y": 27.0, "size": 1.0, "layer": "B_SilkS", "bold": True, "mirror": True},
    {"text": "(c) 2026 Kartikeydheer Srivastava", "x": 34.0, "y": 29.0, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    {"text": "All rights reserved", "x": 34.0, "y": 30.4, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    # front: header pin names, upright beside each pin (shield headers on the top and bottom rows)
    *[_label(t, D0_PIN[0] - 2.54 * i, 4.05, 90, "top") for i, t in enumerate(["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7"])],
    *[_label(t, D8_PIN[0] - 2.54 * i, 4.05, 90, "top")
      for i, t in enumerate(["D8", "D9", "D10", "D11", "D12", "D13", "GND", "AREF", "SDA", "SCL"])],
    *[_label(t, POWER_PIN[0] + 2.54 * i, 49.3, 90, "bottom")
      for i, t in enumerate(["NC", "IOREF", "RESET", "3V3", "5V", "GND", "GND", "VIN"])],
    *[_label(t, A0_PIN[0] + 2.54 * i, 49.3, 90, "bottom") for i, t in enumerate(["A0", "A1", "A2", "A3", "A4", "A5"])],
    # the jack's input, the ICSP header and its pin 1, the reset button, the USB port
    {"text": "7-12V, centre +", "x": 17.3, "y": 35.0, "size": 0.8},
    {"text": "ICSP", "x": 64.9, "y": 30.7, "size": 0.8}, {"text": "1", "x": 61.4, "y": 22.86, "size": 0.8},
    {"text": "RESET", "x": 56.5, "y": 24.3, "size": 0.8},
    {"text": "USB", "x": 4.0, "y": 8.9, "size": 0.8},
]

BOARD = Board(
    name="eos-atmega328p-board",
    title="EoS ATmega328P Board",
    revision="A",
    date="2026-10-12",
    company=OWNER,
    licence=LICENCE,
    contact=CONTACT,
    licence_terms=LICENCE_TERMS,
    credits=["Uno R3 outline (2700 x 2100 mil), shield header positions, ICSP pin 1 at (2505, 1200) mil and mounting holes "
             "at (600, 2000), (550, 100), (2600, 1400), (2600, 300) mil: Matthew Beckler, \"Arduino Uno R3\" dimension "
             "drawing v1.05, Wayne and Layne, public domain (wayneandlayne.com/files/common/arduino_uno_drawing.svg); "
             "facts only, no file copied",
             "Uno R3 mounting holes (3.20 mm at 15.24 / 2.54 / 66.04 / 17.78 / 45.72 / 50.80 mm): Arduino UNO R3 "
             "product reference manual (SKU A000066), section 5.4 (docs.arduino.cc/resources/datasheets/A000066-datasheet.pdf); "
             "facts only",
             "Uno R3 header positions cross-checked against KiCad 10's Module:Arduino_UNO_R3_WithMountingHoles footprint "
             "(KiCad libraries, CC BY-SA 4.0); positions only, the footprint is not used"],
    width=W,
    height=H,
    corner_radius=1.0,
    thickness=1.6,
    layers=2,
    parts=PARTS,
    power_nets={"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V", "VBUS": "power:VBUS"},
    flagged_nets=["GND", "VBUS", "VUSB", "VIN", "5V_REG", "AVCC"],
    headings=[((35, 75), "USB-C, ESD, 500 mA fuse"), ((35, 160), "Barrel jack, reverse-polarity diode, 5 V buck"),
              ((205, 75), "Power mux: jack 5 V first, USB otherwise"), ((300, 75), "3.3 V LDO, power LED"),
              ((85, 235), "USB-UART (CH340C), DTR auto-reset"), ((215, 190), "ATmega328P, 16 MHz crystal, decoupling"),
              ((200, 315), "Reset (AN2519)"), ((390, 225), "L LED on D13, buffered"),
              ((485, 80), "Uno R3 shield headers and ICSP"), ((160, 328), "VUSB isolation buffers"),
              ((40, 350), "Mounting holes"), ((35, 300), "Power nets")],
    power_block=(40.64, 315.0),
    notes=[((300, 380), "EoS ATmega328P Board, rev A. Designed by Kartikeydheer Srivastava. Fits Uno R3 shields.\n"
                       "Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved; see LICENSE.txt.\n"
                       "Values from Microchip DS40002061B and AN2519, WCH CH340 V3D, TI SLVSFG1A (TPS2116),\n"
                       "TI SCES351Y and SCES296AG (buffers), Diodes DS41326 (AP63205) and DS39724 (AP2112),\n"
                       "ECS ECX-33Q (crystal, CL 12 pF -> 18 pF). Low fuse 0xFF (low-power crystal oscillator).\n"
                       "JP1 (bridged as delivered) joins the DTR# auto-reset to RESET: cut it for debugWIRE."),
           ((380, 300), "Power: USB-C 5 V through F1, or 7-12 V on J2 through D1 and the AP63205.\n"
                        "U3 picks the jack's 5 V whenever it is present and blocks reverse current,\n"
                        "so neither input, nor 5 V fed into the 5V pin, back-feeds the other.")],
    priority_routes=PRIORITY,
    router_keepouts=KEEPOUTS,
    # a via costs as much as 10 mm of track in the priority routes, so D0-D4 stay on the top layer round the
    # crystal block instead of dropping a via in the MCU's pad and running under it on the bottom
    maze_via_cost_mm=10.0,
    # 0.127 mm floor: the router's necks at fine-pitch pads are widened to it (0.112 mm before)
    rules={"min_track": 0.127},
    netclasses={"Power": {"track": 0.4, "clearance": 0.15}, "Supply": {"track": 0.3, "clearance": 0.15},
                "USB": {"track": 0.2, "clearance": 0.15}},
    # AVCC in the 0.3 mm class: it also powers PC0-PC3's drivers (DS40002061B 1.1.7)
    net_to_class={"VBUS": "Power", "VJACK": "Power", "VIN": "Power", "BUCK_SW": "Power",
                  "5V_REG": "Supply", "VUSB": "Supply", "+5V": "Supply", "+3V3": "Supply", "AVCC": "Supply",
                  "USB_D+": "USB", "USB_D-": "USB"},
)
