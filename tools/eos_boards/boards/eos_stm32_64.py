"""EoS STM32 64: an STM32F411RE development board in the Nucleo-64 format, designed by Kartikeydheer Srivastava.

Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved: this design file is not under
the repository's MIT licence; see boards/eos/eos-stm32-64/LICENSE.txt.

A 70 x 82.5 mm two-layer board for the STMicroelectronics STM32F411RET6 (LQFP-64), with the
Arduino Uno V3 headers and the two ST morpho 2x19 headers where a Nucleo-64 has them, so
Nucleo-64 shields and morpho cables fit. It does the job of ST's NUCLEO-F411RE, but it is an
original design: no design file of ST's (schematic, layout, CAD, Gerbers, BOM) was opened. Of
ST's board documentation, only the user manual UM1724 Rev 17 was used, and only for two
published facts: the mechanical drawing (its Figure 5) and the connector pin tables (Table 16,
Arduino connectors on NUCLEO-F411RE, and Table 29, ST morpho connector on NUCLEO-F411RE).

Why the STM32F411RE: it is one of the boards UM1724's tables are written for, so every header
pin gets the signal those tables name without reinterpretation; it is in production and widely
stocked; it has USB OTG FS, whose ROM bootloader does DFU on PA11/PA12 (AN2606 Rev 70, section
38), so the board can be flashed over its own USB port with no probe; and BOOT0 is a dedicated
pin (RM0383 Rev 3, Table 2), so no Arduino or morpho pin is shared with the boot strap.

Mechanical facts (UM1724 Figure 5; origin top-left, y down, mm):

* Outline 70.00 x 82.50. The drawing's bottom edge is 80.50 except for a 33.00 mm wide tab that
  reaches 82.50; the generator draws a rounded rectangle, so this board is 70 x 82.5 with no
  notch (2 mm larger than the drawing in the two bottom corners).
* The bottom pin row (CN7/CN10 pins 37-38, A5, D0) is 3.80 + 2.54 + 71.12 = 77.46 from the top
  edge and 3.04 above the 80.50 edge; the morpho rows run up from it at 2.54 mm, so pin 1 is at
  y = 31.74.
* x positions: CN6/CN8 at 10.87 from the left edge, CN5/CN9 48.26 to the right of them (59.13),
  the outer morpho columns 63.50 apart (3.25 and 66.75), each 7.62 from its Arduino column.
  CN7's odd pins are its outer column, CN10's odd pins its inner column, as the drawing marks
  pin 1 (square pad) on each.
* Arduino rows: CN6 pin 8 (VIN) is 5.08 above CN8 pin 1 (A0); CN5 pin 1 (D8) is 4.06 above CN9
  pin 8 (D7); the hole by CN6 is 13.97 above CN6 pin 1, the hole by CN5 3.56 above D15, the hole
  at the bottom 2.54 below the bottom row and 33.02 right of CN8. These match the Uno R3 layout.
  UM1724 does not dimension the holes, so the Uno's 3.2 mm is used, unplated.
* The two holes at the top are this board's own (the drawing has none in that area).

Header signals follow UM1724 Table 16 and Table 29 for NUCLEO-F411RE, pin for pin:

* Pins those tables mark "-" stay unconnected: CN7 9, 10, 11, 26; CN10 10, 18 (the F411 has no
  PB11: its LQFP-64 pin 30 is VCAP_1), 36, 38; CN6 pin 1 (NC).
* "VDD" (CN7 5) is the MCU supply after the IDD jumper JP1; "+3.3V" (CN7 16, CN6 4) and IOREF
  (CN7 12, CN6 2) are the 3.3 V rail. "AVDD" (CN10 7) and AREF (CN5 8) are VDDA: on the LQFP-64
  VREF+ is bonded to VDDA (DS10314 Rev 8, Figure 11), so AREF is an output and a shield must not
  drive it (it would feed VDDA through the bead). "U5V" (CN10 8), the 5 V from the debug USB
  connector, is this board's USB-UART connector's VBUS after its fuse; nothing may be fed into it,
  or it back-powers J1's host. AGND is GND.
* A4 and A5 are "PC1 or PB9" and "PC0 or PB8" in the tables: solder jumpers JP4 and JP6 pick
  PC1/PC0 as delivered; cut and re-bridge for PB9/PB8.
* PH0/PH1 (CN7 29, 31) and PC14/PC15 (CN7 25, 27) are the crystal pins. AN2867 section 7.1
  asks for other signals to be routed away from the oscillator, so they reach the header only
  through 0 ohm links R18-R21, not fitted, each beside its crystal's load capacitor. Remove a
  crystal and its capacitors and fit the links to use those pins on CN7.
* PA12/PA11 (CN10 12, 14) are the native USB pair, so they reach the header likewise only
  through 0 ohm links R24/R25, not fitted, beside the pair: as delivered a header pin, or a
  morpho cable on it, does not hang on the live USB lines. Fit them (and leave J2 unplugged) to
  use PA11/PA12 on CN10.
* PC9 (CN10 1) carries J2's VBUS sense as delivered (JP7, see Native USB); cut JP7 to free it.
* PA13/PA14 (SWDIO/SWCLK) and PB3 (SWO) are on the headers and on the debug connector J3.

Every value follows a datasheet:

* STM32F411RET6 (ST DS10314 Rev 8). Supply per Figure 17 "Power supply scheme" and AN4488 Rev 7
  section 2.2: 100 nF at each of the four VDD pins (19, 32, 48, 64) and one 4.7 uF ceramic on VDD
  ("The 4.7 uF ceramic capacitor must be connected to one of the VDD pin"; AN4488: min 4.7 uF);
  VCAP_1 4.7 uF ceramic, ESR < 1 ohm (Table 16; AN4488 2.2: "1*4.7 uF LowESR < 1 ohm"), laid
  against pin 30 by a priority route; VDDA 100 nF + 1 uF (Figure 17, AN4488 2.2) and fed from
  VDD through a ferrite bead, the analog filtering AN4488 2.2 suggests ("VDDA can be connected to
  VDD through a ferrite bead"); VBAT tied to VDD with 100 nF when no battery is used (AN4488 2.2),
  through solder jumper JP2 so a coin cell can be wired to CN7 pin 33 instead. The bead is TDK
  MMZ1608B601C (600 ohm at 100 MHz, 0.40 ohm max, 500 mA; TDK MMZ1608 catalogue 20200717): at
  the ADC's 1.8 mA max (DS10314 Table 65) it drops under 1 mV.
* NRST: 100 nF to GND (DS10314 Figure 32; AN4488 3.1), the internal 30-50 kohm pull-up
  (Table 56), a reset button B2 and the debug connector's nRESET.
* BOOT0: 10 kohm to GND and a button B3 to VDD (AN4488 Figure 12, 10 kohm). BOOT1 is PB2:
  10 kohm to GND, so BOOT0 high selects system memory (RM0383 Table 2: BOOT1 = 0, BOOT0 = 1),
  not SRAM. Hold B3, press B2: the ROM bootloader starts, with USB DFU on PA11/PA12. AN2606
  section 4.3 asks for the RX pins of the bootloader interfaces not in use to be held at a known
  level, or "Leaving these pins floating during the detection phase can result in activation of
  unused interfaces": USART1_RX (PA10, D2) gets 47 kohm to VDD. Its other RX/MOSI pins on this
  package (SPI1 PA7, SPI2 PB15, SPI3 PC12; AN2606 Table 83) are left to the shield; see README.
* MCU orientation: pin 1 at the top left, so the crystal pins 3-6 face the open board to the
  left of the MCU, the analog pins and their headers are on the same side, and the USB pins
  PA11/PA12 face J2. The crystals are tight against pins 3-6 and every crystal, load-capacitor and
  link connection is a priority route, laid on the top layer before the autorouter runs, so the
  autorouter cannot lengthen them or bring another signal between a crystal and the MCU. The one
  exception is forced by the pinout: VBAT and PC13 (pins 1-2) can only leave past the LSE, so
  their escapes run between Y2 and the MCU; they are a supply and a button input, both slow.
  AN2867 7.1 also asks for "a dedicated underneath ground plane" under the oscillator. The
  generator's router keep-outs cover only the top layer, so two 5 x 10 mm ground pads on the
  bottom side (TP1, TP2, nothing fitted) cover both crystals, their load capacitors and links and
  the oscillator lines up to 1.5 mm from the pins: no other net can be routed on the bottom layer
  there, and the bottom pour joins them into one solid ground. NRST's 100 nF (C20) sits at pin 7.
* HSE: 8 MHz crystal ECS-80-10-30B-CWN-TR (ECS ECX-53B datasheet: ESR 100 ohm max at 8 MHz,
  C0 5 pF max, CL 10 pF, 100 uW max). 8 MHz rather than 24 MHz because AN2606 section 38.1
  says the DFU bootloader measures the HSE with the HSI and is better with a low frequency ("it
  is better to use 8 MHz instead of 25 MHz"); it must be a multiple of 1 MHz from 4 to 26 MHz.
  AN2867 Rev 24 section 3.4: gmcrit = 4 x ESR x (2 pi F)^2 x (C0 + CL)^2 = 4 x 100 x (2 pi x
  8 MHz)^2 x (15 pF)^2 = 0.23 mA/V, under the F411's Gm_crit_max of 1 mA/V (DS10314 Table 37),
  with worst-case crystal figures. Load capacitors from AN2867 section 3.3, CL = CL1 x CL2 /
  (CL1 + CL2) + Cs: Cs = 4 pF (each oscillator pin is 5 pF, DS10314 Table 53 CIO, so 2.5 pF in
  series across the crystal, plus about 1.5 pF of pads and traces), so CL1 = CL2 = 2 x (10 - 4)
  = 12 pF, C0G. Drive level (AN2867 3.5.2) with a rail-to-rail 3.3 V swing: 100 ohm x (pi x
  8 MHz x 14 pF)^2 x 3.3^2 / 2 = 67 uW, under the crystal's 100 uW, so no RExt (AN2867 3.5.3).
* LSE: 32.768 kHz Abracon ABS07-120-32.768kHz-T (Abracon datasheet: ESR 60 kohm max, C0
  1.60 pF max, CL 6.0 pF, 0.5 uW max), listed in AN2867 Table 7 as compatible with the STM32F4
  (gmcrit 0.5273 uA/V at its typical C0). AN4488 6.2 asks for CL <= 7 pF. With the worst-case
  C0 of 1.6 pF, gmcrit = 4 x 60 kohm x (2 pi x 32768 Hz)^2 x (7.6 pF)^2 = 0.59 uA/V, above the
  low-power mode's 0.56 uA/V and well under the high-drive mode's 1.50 uA/V (DS10314 Table 38),
  so firmware should set LSEMOD = 1 (RCC_BDCR bit 3, RM0383). Load capacitors as for the HSE:
  CL1 = CL2 = 2 x (6 - 4) = 4 pF, fitted as 3.9 pF C0G (CL = 5.95 pF).
* User LED LD2 on PA5 and user button B1 on PC13, as UM1724 names them. LD2 (Kingbright
  APTD1608LCGCK, green, VF 1.9 V typ at 2 mA, DSAO7432 V.6B) through 680 ohm: (3.3 - 1.9) / 680
  = 2.1 mA, and through solder jumper JP3, so D13/SPI1_SCK can be freed. B1 pulls PC13 low
  against 10 kohm to VDD (PC13 must not source current, DS10314 Table 8 note 2, and does not
  here); with the 1 uA input leakage the idle level is VDD - 10 mV.
* Debug: an Arm 10-pin Cortex Debug connector (1.27 mm) replaces the NUCLEO's ST-LINK, whose
  firmware is ST's: VTref = VDD, SWDIO PA13, SWCLK PA14, SWO PB3, TDI PA15 (so JTAG works too),
  nRESET NRST (AN4488 Table 8).

USB-UART (virtual COM port on USART2, PA2 TX / PA3 RX, as UM1724 Table 16 puts on D1/D0):
Silicon Labs CP2102N-A02-GQFN20 (data sheet Rev. 1.5) on the board's own 3.3 V, its regulator
unused (Figure 2.3: VREGIN tied to VDD, 3.0-3.6 V in), so it is powered whenever the MCU is and
the MCU's TX can never back-power it. 4.7 uF + 0.1 uF on VREGIN and on VDD ("4.7 uF and 0.1 uF
bypass capacitors required for each power pin ... placed as close to the pins as possible"): the
two 0.1 uF sit against pins 6 and 7 and the 4.7 uF next to them, all joined on the top layer by
priority routes; 1 kohm RSTb pull-up to VDD (section 2.1). Its VBUS pin reads J1's VBUS, ahead
of the fuse as Figure 2.5 draws it, through the 22.1 kohm / 47.5 kohm divider, which section 2.3
requires in both bus- and self-powered designs (5 V reads 3.41 V and 4.40 V reads 3.00 V, above
VIH = VIO - 0.6 V = 2.7 V, Table 3.7; no fuse drop in between), so its D+ pull-up comes on only
while a host supplies J1's VBUS. A 4.7 kohm bleed (R3) holds J1's VBUS down when nothing is
plugged in, against the reverse leakage of OR diode D1 (Nexperia PMEG3010CEH Rev. 02: 1.2 uA typ
at 5 V and 25 C, Table 8; Fig. 2, typical, about 100 uA at 85 C): with the divider it is 4.4
kohm, so 100 uA lifts VBUS to 0.44 V, under USB Type-C vSafe0V (0.8 V), which puts 0.30 V on the
VBUS pin, under its VIL of 0.6 V (Table 3.7). A host attached loses 1.1 mA to it. TXD and RXD
meet PA3 and PA2 through 1 kohm and solder jumpers JP8/JP9 (bridged as delivered; cut them to
free D0/D1 for a shield): with the IDD jumper JP1 cut the MCU is off while the bridge is on, and
its TXD then pushes at most 3.6 V / 1 kohm = 3.6 mA into PA3, a 5 V-tolerant pin rated VDD + 4 V
(DS10314 Table 11); a shield driving D0 fights the bridge through the same 1 kohm, 3.6 mA at
most. The RC is 1 kohm x about 17 pF = 17 ns, against 333 ns per bit at 3 Mbaud, the bridge's
maximum. USART2's ROM bootloader pins are PD5/PD6 (AN2606 Table 83), which the LQFP-64 lacks, so
the COM port cannot flash the chip: use DFU or SWD.

ESD: both USB-C ports use Littelfuse SP0503BAHTG (SP05xxBA series datasheet: three avalanche
diodes to ground, 5.5 V standoff, 30 pF), the part the CP2102N data sheet shows in Figure 2.5,
not a USBLC6-style array whose data-line diodes run to its VBUS pin: after a host unplugs, a
live D+ pull-up could hold VBUS near 2 V through those diodes and hide the unplug from the
VBUS-sensing CP2102N, or from the STM32's VBUS sense on PC9. Each pair runs connector contact,
ESD pad, chip pin on the top layer, through the ESD pads with no stub, laid as priority routes
before the autorouter (as on EoS TM4C123 Board): on J1 the inner contacts A7/A6 lead and B6
joins in front of A7, B7 through a via pair (the order the CP2102N's pins 4/5 need); on J2 the
outer contacts B6/B7 lead, A6 joins behind A7 and A7 in front of A6. U5 takes D- on pin 3, which
the part allows (its three diodes are identical). J2's pair runs down a channel between two
top-layer keep-outs, which hold the lines together and away from the buck inductor's output pad,
and enters PA12/PA11 straight under VDD pin 48's capacitor C13.

Native USB: a second USB-C (J2) on PA11/PA12 (USB OTG FS, device mode), for USB firmware and the
DFU bootloader. The OTG_FS's own VBUS sense pin is PA9, which is Arduino D8, so the hardware
sensing stays off (OTG_FS_GCCFG NOVBUSSENS, RM0383 section 22.5) and J2's VBUS reaches PC9, a
5 V-tolerant pin on CN10 only (DS10314 Table 8, FT), through 22.1 kohm / 47.5 kohm ahead of F2
(3.41 V; under VDD + 4 V even with the MCU unpowered, DS10314 Table 11) and solder jumper JP7,
bridged as delivered. Firmware watches PC9 and keeps the D+ pull-up off (OTG_FS_DCTL SDIS) while
it reads low (RM0383: "VBUS connection can be remapped on another general purpose input pad and
monitored by software"), so the pull-up is never driven into an unpowered host. J2's VBUS has
its own 4.7 kohm bleed (R23), sized as R3. The OTG_FS needs no external pull-up (AN2606 Table
83). The ROM DFU bootloader uses PA11/PA12 only and turns its pull-up on regardless (AN2606
Table 83). Host mode is not supported: no VBUS switch.

Power: both USB-C ports are 5 V sinks (5.1 kohm Rd on CC1 and CC2, USB Type-C specification),
each with a 500 mA polyfuse (Littelfuse 1206L050: 0.50 A hold, 1.00 A trip, 6 V, R1max 0.70 ohm).
The 5 V rail is the OR of four inputs: J1 and J2 through Nexperia PMEG3010CEH Schottky diodes
(data sheet Rev. 02: 1 A, VF 0.44 V max at 0.5 A, IR 1.2 uA typ at 5 V, 50 uA max at 30 V; low
leakage on purpose, see the bleeds above), E5V (CN7 pin 6, 4.75-5.5 V) through a third, and the
VIN buck through a B240A (Diodes DS13004 Rev 22-2: 40 V, 2 A, VF 0.50 V max at 2 A). VIN (CN6
pin 8, CN7 pin 24; 7-12 V, the Arduino VIN range) comes in through another B240A against reverse
polarity to an AP63205 buck (Diodes DS41326 Rev 3-2: 3.8-32 V in, 5.0 V out, 2 A; HS peak
current limit 2.5-3.1 A) with its Table 3 values: C1 = 10 uF (fitted twice, C5 and C25: section
11 asks for "a ceramic capacitor greater than 10 uF", and a 50 V X5R 10 uF loses part of its value
at 12 V of DC bias), C2 = 2 x 22 uF, C3 (BST) = 100 nF,
EN tied to VIN ("can be directly connected to VIN"), and L = 4.7 uH as a Bourns SRP5030T-4R7M
(Bourns SRP5030T datasheet: Isat 6.0 A, Irms 4.6 A, 53 mohm), which stays out of saturation up
to the buck's 3.1 A current limit. Layout per DS41326 "PCB Layout" and Figure 25: the input
capacitor straddles the VIN and GND pins (item 4), the inductor's SW pad sits beside pin 5 with
the bootstrap capacitor between them, and an output capacitor shares the input capacitor's
ground, all joined on the top layer by priority routes with no vias. The feedback line goes round
the buck on the top layer, held 0.5 mm or more from the bootstrap copper by a top-layer keep-out.
No part sits under the buck, but item 3's bottom-layer ground under the device is not enforced:
the generator has no bottom-layer keep-out (see the README for what the routed board has there).
For item 2 the capacitors' grounds get plated 0.5 mm GND
pads, TP3 between C5 and C8 and TP4 below C7: the generator places vias only where its router and
stitching grid do, so these are footprints. Item 2's reason is heat at 2 A (item 1); the 5 V taken
from VIN is budgeted at 0.5 A, where Figure 4 shows about 94 % efficiency at 12 V in (measured on
the 500 kHz AP63200): even at 90 % the loss is 0.28 W, a 25 C rise at the 89 C/W of the TSOT26
(DS41326 thermal table). D5 then drops at most 0.45 V and dissipates about 0.2 W.
3.3 V: AP7361C-33 LDO (Diodes DS37274 Rev 5-2: 1 A, input 2.2-6.0 V, dropout 140 mV max at
300 mA), 4.7 uF in and out as its typical application shows. From a 4.6 V rail it drops 1.3 V:
at 400 mA that is 0.52 W, a 57 C rise at the 110 C/W the datasheet gives for SOT-223 on its
minimum pad, so the 3.3 V rail is budgeted at 400 mA continuous. Power LED LD3 (Kingbright
APTD1608LSURCK, red, VF 1.75 V typ at 2 mA, DSAO7433 V.6A) on 3.3 V through 750 ohm: 2.1 mA.
JP1 (IDD) is a solder jumper, bridged as delivered, from the 3.3 V rail to the MCU's VDD, with
the 2-pin header J4 across it (not fitted): cut JP1 and connect an ammeter to J4 to measure the
MCU's current. Plug-in charge on a USB port (not limited by any soft start): about 4.7 uF on the
5 V rail, 21 uF on 3.3 V and 4.7 uF on VCAP_1 (1.2 V), roughly 97 uC in all, more than the
10 uF that USB 2.0 assumes at plug-in; see the README.
"""

from __future__ import annotations

from ..design import NC, Board, Part, USB_C_EDGE
from .owner import CONTACT, LICENCE, LICENCE_TERMS, OWNER

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C1206 = "Capacitor_SMD:C_1206_3216Metric"
LED0603 = "LED_SMD:LED_0603_1608Metric"
SOD123F = "Diode_SMD:D_SOD-123F"
KMR2 = "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2"
USBC = "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"
HOLE = "MountingHole:MountingHole_3.2mm_M3_ISO14580"
SJ2_BRIDGED = "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm"
SJ3_BRIDGED12 = "Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm"

DS = "ST DS10314 Rev 8"
AN4488 = "ST AN4488 Rev 7"
AN2867 = "ST AN2867 Rev 24"
CP = "Silicon Labs CP2102N data sheet Rev. 1.5"
PMEG = "Nexperia PMEG3010CEH data sheet Rev. 02"


# Fitted resistors: Yageo RC_L, 1 %, 0402 (RC0402FR-07...); fitted capacitors: Samsung CL series unless a part
# names its own. Every code was found in a distributor listing (DigiKey, LCSC, Arrow, RS) on 2026-10-13.
RES_MPN = {"5.1k": "RC0402FR-075K1L", "4.7k": "RC0402FR-074K7L", "1k": "RC0402FR-071KL", "22.1k": "RC0402FR-0722K1L",
           "47.5k": "RC0402FR-0747K5L", "750": "RC0402FR-07750RL", "10k": "RC0402FR-0710KL", "680": "RC0402FR-07680RL",
           "47k": "RC0402FR-0747KL"}
SAMSUNG = "Samsung Electro-Mechanics"
CAP_MPN = {("100n", C0402): "CL05B104KO5NNNC", ("1u", C0402): "CL05A105KA5NQNC", ("4.7u", C0805): "CL21A475KAQNNNE",
           ("10u", C1206): "CL31A106KBHNNNE", ("22u", C1206): "CL31A226KAHNNNE", ("12p", C0402): "CL05C120JB5NNNC"}


def res(ref, value, a, b, sch, desc, dnp=False, rot=0):
    mpn = {} if dnp else {"Manufacturer": "Yageo", "MPN": RES_MPN[value]}
    return Part(ref, "Device:R_Small", value, R0402, sch, {"1": a, "2": b}, fields={"Description": desc, **mpn},
                dnp=dnp, sch_rotation=rot)


def cap(ref, value, a, b, sch, desc, fp=C0402, mpn=None, mfr=SAMSUNG):
    return Part(ref, "Device:C_Small", value, fp, sch, {"1": a, "2": b},
                fields={"Description": desc, "Manufacturer": mfr, "MPN": mpn or CAP_MPN[(value, fp)]})


def schottky(ref, anode, cathode, sch, what):
    return Part(ref, "Device:D_Schottky_Small", "PMEG3010CEH", SOD123F, sch, {"A": anode, "K": cathode},
                fields={"Manufacturer": "Nexperia", "MPN": "PMEG3010CEH,115",
                        "Description": f"Schottky 30 V 1 A, VF 0.44 V max at 0.5 A, IR 1.2 uA typ at 5 V ({PMEG}): {what}"})


def b240a(ref, anode, cathode, sch, what):
    return Part(ref, "Device:D_Schottky_Small", "B240A", "Diode_SMD:D_SMA", sch, {"A": anode, "K": cathode},
                fields={"Manufacturer": "Diodes Incorporated", "MPN": "B240A-13-F",
                        "Description": f"Schottky 40 V 2 A, VF 0.50 V max at 2 A, SMA (Diodes DS13004 Rev 22-2): {what}"})


def usb_c(ref, prefix, dp, dm, sch, what):
    return Part(ref, "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", USBC, sch,
                {"VBUS": f"VBUS_{prefix}", "GND": "GND", "CC1": f"CC1_{prefix}", "CC2": f"CC2_{prefix}",
                 "D+": dp, "D-": dm, "SBU1": NC, "SBU2": NC, "SHIELD": "GND"},
                fields={"Manufacturer": "Korean Hroparts", "MPN": "TYPE-C-31-M-12",
                        "Description": f"USB-C 2.0 receptacle, 16 pins: {what}"})


def esd(ref, dp, dm, vbus, sch, what, swap=False):
    """SP0503BAHTG: pin 1 the common anode (GND), pins 2-4 one diode each to it, so the data lines may
    take pins 2 and 3 in either order (``swap`` puts D+ on pin 3), whichever keeps the pair uncrossed."""
    p_dp, p_dm = ("3", "2") if swap else ("2", "3")
    return Part(ref, "Power_Protection:SP0503BAHT", "SP0503BAHTG", "Package_TO_SOT_SMD:SOT-143", sch,
                {"1": "GND", p_dp: dp, p_dm: dm, "4": vbus},
                fields={"Manufacturer": "Littelfuse", "MPN": "SP0503BAHTG",
                        "Description": f"USB ESD protection, {what}: three diodes to GND, none to VBUS "
                                       f"(Littelfuse SP05xxBA datasheet; {CP} Figure 2.5)"})


def socket(ref, n, value, pins, sch, desc):
    """An Arduino header (female, 2.54 mm): pin 1 is the first entry of ``pins``."""
    return Part(ref, f"Connector:Conn_01x{n:02d}_Socket", value,
                f"Connector_PinSocket_2.54mm:PinSocket_1x{n:02d}_P2.54mm_Vertical", sch,
                {str(i + 1): net for i, net in enumerate(pins)},
                fields={"Manufacturer": "Samtec", "MPN": f"SSW-1{n:02d}-01-T-S", "Description": desc})


def morpho(ref, pins, sch, desc):
    """An ST morpho header, 2x19 male, 2.54 mm: ``pins`` maps pin number to net."""
    return Part(ref, "Connector_Generic:Conn_02x19_Odd_Even", ref,
                "Connector_PinHeader_2.54mm:PinHeader_2x19_P2.54mm_Vertical", sch,
                {str(n): pins.get(n, NC) for n in range(1, 39)},
                fields={"Manufacturer": "Samtec", "MPN": "TSW-119-07-L-D", "Description": desc})   # 2 x 19, listed (Octopart)


def button(ref, value, a, sch, what, b="GND"):
    return Part(ref, "Switch:SW_Push", value, KMR2, sch, {"1": a, "2": b},
                fields={"Manufacturer": "C&K", "MPN": "KMR221G LFS", "Description": f"Tactile switch, {what}"})


def jumper(ref, lib_id, fp, value, nets, sch, desc):
    return Part(ref, lib_id, value, fp, sch, nets, fields={"Description": desc})


W, H = 70.0, 82.5
ROW1 = 31.74                       # y of morpho pins 1-2 (UM1724 Figure 5: 77.46 - 18 x 2.54)
CN7_X, CN10_X = 3.25, 64.21        # pin 1 of each morpho header; pin 2 is 2.54 mm to the right
ARD_L, ARD_R = 10.87, 59.13        # Arduino columns: CN6/CN8 and CN5/CN9
MCU = (36.0, 50.0)                 # STM32F411 centre, pin 1 at the top left

# UM1724 Rev 17 Table 29 (ST morpho connector on NUCLEO-F411RE), by pin. Pins it marks "-" are
# left out (NC). PH0/PH1/PC14/PC15 reach CN7 only through the 0 ohm links R18-R21 (not fitted).
CN7_PINS = {1: "PC10", 2: "PC11", 3: "PC12", 4: "PD2", 5: "VDD_MCU", 6: "E5V", 7: "BOOT0", 8: "GND",
            12: "+3V3", 13: "PA13", 14: "NRST", 15: "PA14", 16: "+3V3", 17: "PA15", 18: "+5V", 19: "GND",
            20: "GND", 21: "PB7", 22: "GND", 23: "PC13", 24: "VIN", 25: "PC14_HDR", 27: "PC15_HDR",
            28: "PA0", 29: "PH0_HDR", 30: "PA1", 31: "PH1_HDR", 32: "PA4", 33: "VBAT", 34: "PB0",
            35: "PC2", 36: "A4", 37: "PC3", 38: "A5"}
CN10_PINS = {1: "PC9", 2: "PC8", 3: "PB8", 4: "PC6", 5: "PB9", 6: "PC5", 7: "VDDA", 8: "U5V", 9: "GND",
             11: "PA5", 12: "PA12_HDR", 13: "PA6", 14: "PA11_HDR", 15: "PA7", 16: "PB12", 17: "PB6", 19: "PC7",
             20: "GND", 21: "PA9", 22: "PB2", 23: "PA8", 24: "PB1", 25: "PB10", 26: "PB15", 27: "PB4",
             28: "PB14", 29: "PB5", 30: "PB13", 31: "PB3", 32: "GND", 33: "PA10", 34: "PC4", 35: "PA2",
             37: "PA3"}

# STM32F411RET6 pins (DS10314 Table 8, LQFP-64 column), by name.
MCU_NETS = {"VDD": "VDD_MCU", "VSS": "GND", "VDDA": "VDDA", "VSSA": "GND", "VCAP1": "VCAP1", "VBAT": "VBAT",
            "NRST": "NRST", "BOOT0": "BOOT0", "PA11": "USB_DM", "PA12": "USB_DP",
            **{p: p for p in ("PA0", "PA1", "PA2", "PA3", "PA4", "PA5", "PA6", "PA7", "PA8", "PA9", "PA10",
                              "PA13", "PA14", "PA15", "PB0", "PB1", "PB2", "PB3", "PB4", "PB5", "PB6", "PB7",
                              "PB8", "PB9", "PB10", "PB12", "PB13", "PB14", "PB15", "PC0", "PC1", "PC2", "PC3",
                              "PC4", "PC5", "PC6", "PC7", "PC8", "PC9", "PC10", "PC11", "PC12", "PC13", "PC14",
                              "PC15", "PD2", "PH0", "PH1")}}

PARTS = [
    # ---- J1: USB-C for the virtual COM port and power ---------------------------------------------
    usb_c("J1", "VCP", "VCP_D+", "VCP_D-", (40, 95), "virtual COM port (CP2102N) and 5 V power"),
    res("R1", "5.1k", "CC1_VCP", "GND", (75, 70), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC1, USB Type-C specification)"),
    res("R2", "5.1k", "CC2_VCP", "GND", (90, 70), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC2, USB Type-C specification)"),
    esd("U5", "VCP_D+", "VCP_D-", "VBUS_VCP", (120, 95), "J1", swap=True),   # D- on the left, as at J1's A7 and U2
    Part("F1", "Device:Polyfuse_Small", "500mA", "Fuse:Fuse_1206_3216Metric", (145, 80), {"1": "VBUS_VCP", "2": "U5V"},
         fields={"Manufacturer": "Littelfuse", "MPN": "1206L050YR",
                 "Description": "PTC resettable fuse 0.50 A hold, 1.00 A trip, 6 V, 1206, J1 VBUS (Littelfuse 1206L datasheet)"}),
    res("R3", "4.7k", "U5V", "GND", (160, 95), f"Resistor 4.7 kohm 1% 0402: J1 VBUS bleed; with the divider 4.4 kohm, so D1's "
        f"leakage at 85 C (about 100 uA typical at 5 V, {PMEG} Fig. 2) leaves 0.44 V, under vSafe0V 0.8 V and the CP2102N "
        f"VBUS VIL ({CP} Table 3.7)"),
    schottky("D1", "U5V", "+5V", (180, 70), "J1 VBUS into the 5 V rail"),

    # ---- CP2102N USB-UART on the board's 3.3 V, VBUS-sensing J1 ----------------------------------------
    Part("U2", "Interface_USB:CP2102N-Axx-xQFN20", "CP2102N-A02-GQFN20",
         "Package_DFN_QFN:SiliconLabs_QFN-20-1EP_3x3mm_P0.5mm_EP1.8x1.8mm", (75, 175),
         {"VREGIN": "+3V3", "VDD": "+3V3", "GND": "GND", "D+": "VCP_D+", "D-": "VCP_D-", "VBUS": "VCP_VBUS",
          "~{RST}": "VCP_RST", "TXD": "VCP_TXD", "RXD": "VCP_RXD",
          **{p: NC for p in ("RS485/GPIO.1", "CLK/GPIO.0", "NC", "~{SUSPEND}", "~{WAKEUP}", "SUSPEND", "~{CTS}",
                             "~{RTS}", "~{RXT}/GPIO.3", "~{TXT}/GPIO.2")}},
         fields={"Manufacturer": "Silicon Labs", "MPN": "CP2102N-A02-GQFN20R",
                 "Description": f"USB to UART bridge on the board's 3.3 V, own regulator unused ({CP} Figure 2.3)"}),
    cap("C1", "4.7u", "+3V3", "GND", (120, 140), f"Capacitor 4.7 uF 25 V X5R 0805 (CP2102N VREGIN; {CP} Figure 2.3)", C0805),
    cap("C2", "100n", "+3V3", "GND", (132, 140), f"Capacitor 100 nF 16 V X7R 0402 (CP2102N VREGIN; {CP} Figure 2.3)"),
    cap("C3", "4.7u", "+3V3", "GND", (144, 140), f"Capacitor 4.7 uF 25 V X5R 0805 (CP2102N VDD; {CP} Figure 2.3)", C0805),
    cap("C4", "100n", "+3V3", "GND", (156, 140), f"Capacitor 100 nF 16 V X7R 0402 (CP2102N VDD; {CP} Figure 2.3)"),
    res("R4", "1k", "VCP_RST", "+3V3", (120, 170), f"Resistor 1 kohm 1% 0402 (CP2102N RSTb pull-up to VDD; {CP} section 2.1)"),
    res("R5", "22.1k", "VBUS_VCP", "VCP_VBUS", (135, 170), f"Resistor 22.1 kohm 1% 0402 (CP2102N VBUS divider, fed from J1's VBUS "
        f"ahead of F1 as in {CP} Figure 2.5)"),
    res("R6", "47.5k", "VCP_VBUS", "GND", (150, 170), f"Resistor 47.5 kohm 1% 0402 (CP2102N VBUS divider: 3.41 V at 5 V; {CP} Figure 2.5)"),
    res("R7", "1k", "VCP_TXD", "VCP_TX_J", (120, 205), "Resistor 1 kohm 1% 0402: CP2102N TXD toward PA3 (D0); a shield driving D0, "
        f"or PA3 with the MCU off (JP1 cut), sees at most 3.6 mA ({DS} Table 11: VDD + 4 V on FT pins)"),
    res("R8", "1k", "VCP_RX_J", "VCP_RXD", (135, 205), "Resistor 1 kohm 1% 0402: PA2 (D1) toward CP2102N RXD"),
    jumper("JP8", "Jumper:SolderJumper_2_Bridged", SJ2_BRIDGED, "D0", {"A": "VCP_TX_J", "B": "PA3"}, (120, 225),
           "Solder jumper, bridged as delivered: CP2102N TXD to PA3 / D0; cut to free D0 for a shield"),
    jumper("JP9", "Jumper:SolderJumper_2_Bridged", SJ2_BRIDGED, "D1", {"A": "PA2", "B": "VCP_RX_J"}, (150, 225),
           "Solder jumper, bridged as delivered: PA2 / D1 to CP2102N RXD; cut to free D1 for a shield"),

    # ---- 5 V rail: four inputs ORed, VIN buck ---------------------------------------------------------
    schottky("D3", "E5V", "+5V", (200, 85), "E5V (CN7 pin 6) into the 5 V rail"),
    b240a("D4", "VIN", "VIN_P", (200, 115), "VIN reverse-polarity protection"),
    Part("U4", "Regulator_Switching:AP63205WU", "AP63205", "Package_TO_SOT_SMD:TSOT-23-6", (240, 125),
         {"IN": "VIN_P", "EN": "VIN_P", "GND": "GND", "SW": "BUCK_SW", "BST": "BUCK_BST", "FB": "5V_BUCK"},
         fields={"Manufacturer": "Diodes Incorporated", "MPN": "AP63205WU-7",
                 "Description": "Buck 3.8-32 V in, 5.0 V 2 A out, EN tied to VIN (Diodes DS41326 Rev 3-2)"}),
    cap("C5", "10u", "VIN_P", "GND", (215, 140), "Capacitor 10 uF 50 V X5R 1206 (buck input across VIN/GND pins, Diodes DS41326 "
        "Table 3 C1, layout item 4)", C1206),
    cap("C25", "10u", "VIN_P", "GND", (228, 140), "Capacitor 10 uF 50 V X5R 1206 (second buck input capacitor: two 10 uF keep the "
        "input above the 10 uF of Diodes DS41326 section 11 after DC-bias loss at 12 V)", C1206),
    *[Part(ref, "Connector:TestPoint", "GND", "TestPoint:TestPoint_THTPad_D1.0mm_Drill0.5mm", (sx, 140), {"1": "GND"}, dnp=True,
           fields={"Description": f"Plated GND pad (0.5 mm hole, nothing fitted) beside the {what} ground: ties the top and "
                                  "bottom ground there (Diodes DS41326 PCB Layout item 2) and takes a probe's ground"})
      for ref, sx, what in (("TP3", 325, "buck input/output capacitors'"), ("TP4", 337, "buck output capacitor C7's"))],
    cap("C6", "100n", "BUCK_SW", "BUCK_BST", (262, 108), "Capacitor 100 nF 50 V X7R 0402 (buck bootstrap, Diodes DS41326 Table 3 C3)",
        mpn="CL05B104KB54PNC"),
    Part("L1", "Device:L_Small", "4.7u", "Inductor_SMD:L_Bourns_SRP5030T", (275, 125), {"1": "BUCK_SW", "2": "5V_BUCK"},
         fields={"Manufacturer": "Bourns", "MPN": "SRP5030T-4R7M",
                 "Description": "Inductor 4.7 uH, Isat 6.0 A, Irms 4.6 A, 53 mohm: above the AP63205's 3.1 A current limit "
                                "(Diodes DS41326 Table 3 L and section 10; Bourns SRP5030T datasheet)"}),
    cap("C7", "22u", "GND", "5V_BUCK", (290, 140), "Capacitor 22 uF 25 V X5R 1206 (buck output, Diodes DS41326 Table 3 C2, 1 of 2)", C1206),
    cap("C8", "22u", "GND", "5V_BUCK", (302, 140), "Capacitor 22 uF 25 V X5R 1206 (buck output, Diodes DS41326 Table 3 C2, 2 of 2)", C1206),
    b240a("D5", "5V_BUCK", "+5V", (315, 115), "VIN buck into the 5 V rail, budgeted at 0.5 A"),

    # ---- 3.3 V LDO, power LED, IDD jumper -------------------------------------------------------------
    Part("U3", "Regulator_Linear:AP7361C-33E", "AP7361C-33", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", (240, 185),
         {"VI": "+5V", "VO": "+3V3", "GND": "GND"},
         fields={"Manufacturer": "Diodes Incorporated", "MPN": "AP7361C-33E-13",
                 "Description": "LDO 3.3 V 1 A, SOT-223; input 2.2-6.0 V (Diodes DS37274 Rev 5-2); budgeted at 400 mA"}),
    cap("C9", "4.7u", "+5V", "GND", (215, 190), "Capacitor 4.7 uF 25 V X5R 0805 (LDO input: DS37274 typical application 4.7 uF, "
        "at least 1 uF)", C0805),
    cap("C10", "4.7u", "+3V3", "GND", (265, 190), "Capacitor 4.7 uF 25 V X5R 0805 (LDO output: DS37274 typical application 4.7 uF, "
        "at least 2.2 uF)", C0805),
    res("R13", "750", "+3V3", "LED_PWR_A", (285, 185), "Resistor 750 ohm 1% 0402 (power LED: (3.3 - 1.75 V) / 750 = 2.1 mA, "
        "Kingbright DSAO7433)"),
    Part("LD3", "Device:LED_Small", "PWR", LED0603, (300, 195), {"A": "LED_PWR_A", "K": "GND"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LSURCK",
                 "Description": "LED red 0603, VF 1.75 V typ at 2 mA (DSAO7433 V.6A): 3.3 V present"}),
    jumper("JP1", "Jumper:SolderJumper_2_Bridged", SJ2_BRIDGED, "IDD", {"A": "+3V3", "B": "VDD_MCU"}, (235, 215),
           "Solder jumper, bridged as delivered: 3.3 V to the MCU's VDD. Cut it and connect an ammeter across J4 "
           "to measure the MCU's current"),
    Part("J4", "Connector_Generic:Conn_01x02", "IDD", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
         (265, 220), {"1": "+3V3", "2": "VDD_MCU"}, dnp=True,
         fields={"Description": "Header 1x2 2.54 mm, not fitted: ammeter across JP1 (1 = 3.3 V rail, 2 = MCU VDD)"}),

    # ---- J2: USB-C to the MCU's USB OTG FS -------------------------------------------------------------
    usb_c("J2", "USB", "USB_DP", "USB_DM", (355, 95), "STM32F411 USB OTG FS (device), DFU bootloader, and 5 V power"),
    res("R9", "5.1k", "CC1_USB", "GND", (390, 70), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC1, USB Type-C specification)"),
    res("R10", "5.1k", "CC2_USB", "GND", (405, 70), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC2, USB Type-C specification)"),
    esd("U6", "USB_DP", "USB_DM", "VBUS_USB", (430, 95), "J2"),
    Part("F2", "Device:Polyfuse_Small", "500mA", "Fuse:Fuse_1206_3216Metric", (455, 80), {"1": "VBUS_USB", "2": "VUSB"},
         fields={"Manufacturer": "Littelfuse", "MPN": "1206L050YR",
                 "Description": "PTC resettable fuse 0.50 A hold, 1.00 A trip, 6 V, 1206, J2 VBUS (Littelfuse 1206L datasheet)"}),
    schottky("D2", "VUSB", "+5V", (470, 70), "J2 VBUS into the 5 V rail"),
    res("R11", "22.1k", "VBUS_USB", "VUSB_SENSE", (470, 100), "Resistor 22.1 kohm 1% 0402 (J2 VBUS sense divider, ahead of F2: "
        f"3.41 V at 5 V keeps PC9 under VDD + 4 V even unpowered, {DS} Table 11)"),
    res("R12", "47.5k", "VUSB_SENSE", "GND", (485, 100), "Resistor 47.5 kohm 1% 0402 (J2 VBUS sense divider)"),
    res("R23", "4.7k", "VUSB", "GND", (500, 75), f"Resistor 4.7 kohm 1% 0402: J2 VBUS bleed; with the divider 4.4 kohm, so D2's "
        f"leakage at 85 C (about 100 uA typical at 5 V, {PMEG} Fig. 2) leaves 0.44 V, under vSafe0V 0.8 V"),
    res("R24", "0", "PA12_HDR", "USB_DP", (530, 70), "Resistor 0 ohm 0402, not fitted: PA12 (USB D+) to CN10 pin 12 when J2 is "
        "not used; fitted, it hangs the header on the live USB line", dnp=True, rot=90),
    res("R25", "0", "PA11_HDR", "USB_DM", (545, 70), "Resistor 0 ohm 0402, not fitted: PA11 (USB D-) to CN10 pin 14 when J2 is "
        "not used", dnp=True, rot=90),
    jumper("JP7", "Jumper:SolderJumper_2_Bridged", SJ2_BRIDGED, "VBUS>PC9", {"A": "VUSB_SENSE", "B": "PC9"}, (515, 100),
           "Solder jumper, bridged as delivered: J2's VBUS to PC9 (CN10 pin 1, no Arduino pin), so firmware can keep the "
           "OTG_FS D+ pull-up off while J2 has no VBUS (RM0383 22.5: VBUS sensed in software on a GPIO); cut to free PC9"),

    # ---- Debug connector, buttons, user LED -------------------------------------------------------------
    Part("J3", "Connector:Conn_ARM_JTAG_SWD_10", "Cortex Debug", "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD",
         (550, 95), {"VTref": "VDD_MCU", "SWDIO/TMS": "PA13", "GND": "GND", "SWCLK/TCK": "PA14", "SWO/TDO": "PB3",
                     "KEY": NC, "NC/TDI": "PA15", "GNDDetect": "GND", "~{RESET}": "NRST"},
         fields={"Manufacturer": "Samtec", "MPN": "FTSH-105-01-L-DV-K",
                 "Description": f"Arm Cortex Debug 10-pin, 1.27 mm: SWD (PA13/PA14), SWO PB3, TDI PA15 ({AN4488} Table 8); "
                                "replaces the NUCLEO's ST-LINK"}),
    button("B1", "USER", "PC13", (505, 145), "user button B1 on PC13 (pressed reads 0)"),
    res("R16", "10k", "PC13", "VDD_MCU", (530, 140), f"Resistor 10 kohm 1% 0402 (B1 pull-up; 1 uA leakage gives VDD - 10 mV, {DS} Table 53)"),
    button("B2", "RESET", "NRST", (505, 170), "reset button B2 (NRST)"),
    button("B3", "BOOT0", "BOOT0", (505, 195), "BOOT0 button B3: hold and press B2 for the ROM bootloader (USB DFU)", b="VDD_MCU"),
    jumper("JP3", "Jumper:SolderJumper_2_Bridged", SJ2_BRIDGED, "LD2", {"A": "PA5", "B": "LD2_J"}, (500, 225),
           "Solder jumper, bridged as delivered: LD2 on PA5; cut to free D13 / SPI1_SCK"),
    res("R17", "680", "LD2_J", "LD2_A", (525, 220), "Resistor 680 ohm 1% 0402 (LD2: (3.3 - 1.9 V) / 680 = 2.1 mA, Kingbright DSAO7432)"),
    Part("LD2", "Device:LED_Small", "USER", LED0603, (545, 230), {"A": "LD2_A", "K": "GND"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LCGCK",
                 "Description": "LED green 0603, VF 1.9 V typ at 2 mA (DSAO7432 V.6B): user LED LD2 on PA5"}),

    # ---- STM32F411RET6 and its supply --------------------------------------------------------------------
    Part("U1", "MCU_ST_STM32F4:STM32F411RETx", "STM32F411RET6", "Package_QFP:LQFP-64_10x10mm_P0.5mm", (215, 315), MCU_NETS,
         fields={"Manufacturer": "STMicroelectronics", "MPN": "STM32F411RET6",
                 "Description": f"Arm Cortex-M4F 100 MHz, 512 KB flash, 128 KB SRAM, USB OTG FS, LQFP-64 ({DS})"}),
    *[cap(f"C{11 + i}", "100n", "VDD_MCU", "GND", (100 + 12 * i, 265), f"Capacitor 100 nF 16 V X7R 0402 (VDD pin {pin}; "
          f"{DS} Figure 17, {AN4488} 2.2: one per VDD pin)") for i, pin in enumerate((19, 32, 48, 64))],
    cap("C15", "4.7u", "VDD_MCU", "GND", (148, 265), f"Capacitor 4.7 uF 25 V X5R 0805 (VDD bulk; {DS} Figure 17 note 2, "
        f"{AN4488} 2.2 min 4.7 uF)", C0805),
    cap("C16", "4.7u", "GND", "VCAP1", (160, 265), f"Capacitor 4.7 uF 25 V X5R 0805 ceramic, ESR < 1 ohm, at pin 30 (VCAP_1; {DS} "
        f"Table 16, {AN4488} 2.2)", C0805),
    Part("FB1", "Device:FerriteBead_Small", "600R", "Inductor_SMD:L_0603_1608Metric", (100, 300), {"1": "VDD_MCU", "2": "VDDA"},
         fields={"Manufacturer": "TDK", "MPN": "MMZ1608B601CTAH0",
                 "Description": f"Ferrite bead 600 ohm at 100 MHz, 0.40 ohm, 500 mA, 0603: VDDA from VDD ({AN4488} 2.2; "
                                "TDK MMZ1608 catalogue 20200717)"}),
    cap("C17", "1u", "GND", "VDDA", (112, 300), f"Capacitor 1 uF 25 V X5R 0402 (VDDA; {DS} Figure 17, {AN4488} 2.2)"),
    cap("C18", "100n", "GND", "VDDA", (124, 300), f"Capacitor 100 nF 16 V X7R 0402 (VDDA, at pin 13; {DS} Figure 17, {AN4488} 2.2)"),
    jumper("JP2", "Jumper:SolderJumper_2_Bridged", SJ2_BRIDGED, "VBAT", {"A": "VDD_MCU", "B": "VBAT"}, (105, 330),
           f"Solder jumper, bridged as delivered: VBAT to VDD with no battery ({AN4488} 2.2); cut to feed VBAT on CN7 pin 33"),
    cap("C19", "100n", "GND", "VBAT", (130, 330), f"Capacitor 100 nF 16 V X7R 0402 (VBAT; {AN4488} 2.2)"),
    cap("C20", "100n", "NRST", "GND", (145, 300), f"Capacitor 100 nF 16 V X7R 0402 (NRST; {DS} Figure 32, {AN4488} 3.1)"),
    res("R14", "10k", "BOOT0", "GND", (157, 300), f"Resistor 10 kohm 1% 0402 (BOOT0 low as delivered; {AN4488} Figure 12)"),
    res("R15", "10k", "PB2", "GND", (169, 300), f"Resistor 10 kohm 1% 0402 (BOOT1 = PB2 low, so BOOT0 high boots system memory; "
        f"RM0383 Table 2, {AN4488} Figure 12)"),
    res("R22", "47k", "PA10", "VDD_MCU", (181, 300), "Resistor 47 kohm 1% 0402 (USART1_RX PA10 held high while the ROM bootloader "
        "picks an interface; ST AN2606 Rev 70 section 4.3 and Table 83)"),

    # ---- Crystals, and the links that free their pins for CN7 ----------------------------------------------
    Part("Y1", "Device:Crystal_GND24", "8MHz", "Crystal:Crystal_SMD_5032-4Pin_5.0x3.2mm", (60, 300),
         {"1": "PH1", "3": "PH0", "G": "GND"},
         fields={"Manufacturer": "ECS Inc.", "MPN": "ECS-80-10-30B-CWN-TR",
                 "Description": "Crystal 8 MHz, CL 10 pF, ESR 100 ohm max, C0 5 pF max, 5.0 x 3.2 mm (ECS ECX-53B); "
                                f"gmcrit 0.23 mA/V < 1 mA/V ({AN2867} 3.4, {DS} Table 37)"}),
    cap("C21", "12p", "PH0", "GND", (45, 320), f"Capacitor 12 pF 50 V C0G 0402 (HSE load: 2 x (10 pF - 4 pF), {AN2867} 3.3)"),
    cap("C22", "12p", "GND", "PH1", (75, 320), f"Capacitor 12 pF 50 V C0G 0402 (HSE load: 2 x (10 pF - 4 pF), {AN2867} 3.3)"),
    Part("Y2", "Device:Crystal_Small", "32.768kHz", "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm", (60, 350),
         {"1": "PC14", "2": "PC15"},
         fields={"Manufacturer": "Abracon", "MPN": "ABS07-120-32.768KHZ-T",
                 "Description": "Crystal 32.768 kHz, CL 6 pF, ESR 60 kohm max, C0 1.6 pF max, 3.2 x 1.5 mm (Abracon ABS07-120); "
                                f"{AN2867} Table 7; firmware sets LSEMOD = 1 (high drive)"}),
    cap("C23", "3.9p", "PC14", "GND", (45, 365), f"Capacitor 3.9 pF 50 V C0G 0402 (LSE load: 2 x (6 pF - 4 pF), {AN2867} 3.3)",
        mpn="GRM1555C1H3R9CA01D", mfr="Murata"),
    cap("C24", "3.9p", "GND", "PC15", (75, 365), f"Capacitor 3.9 pF 50 V C0G 0402 (LSE load: 2 x (6 pF - 4 pF), {AN2867} 3.3)",
        mpn="GRM1555C1H3R9CA01D", mfr="Murata"),
    *[Part(ref, "Connector:TestPoint", "GND", "Connector_Wire:SolderWirePad_1x01_SMD_5x10mm", (sx, 360), {"1": "GND"}, side="B",
           dnp=True, fields={"Description": "Bottom-side ground pad 5 x 10 mm under the crystals (nothing fitted): keeps the bottom "
                                            f"layer there solid ground, with no other net under the oscillators ({AN2867} 7.1)"})
      for ref, sx in (("TP1", 110), ("TP2", 122))],
    res("R18", "0", "PH0_HDR", "PH0", (30, 385), "Resistor 0 ohm 0402, not fitted: PH0 to CN7 pin 29 when Y1 is removed "
        f"({AN2867} 7.1: other signals routed away from the oscillator)", dnp=True, rot=90),
    res("R19", "0", "PH1_HDR", "PH1", (50, 385), "Resistor 0 ohm 0402, not fitted: PH1 to CN7 pin 31 when Y1 is removed",
        dnp=True, rot=90),
    res("R20", "0", "PC14_HDR", "PC14", (70, 385), "Resistor 0 ohm 0402, not fitted: PC14 to CN7 pin 25 when Y2 is removed",
        dnp=True, rot=90),
    res("R21", "0", "PC15_HDR", "PC15", (90, 385), "Resistor 0 ohm 0402, not fitted: PC15 to CN7 pin 27 when Y2 is removed",
        dnp=True, rot=90),

    # ---- Arduino Uno V3 headers (UM1724 Table 16) and ST morpho headers (UM1724 Table 29) --------------------
    socket("CN6", 8, "POWER", [NC, "+3V3", "NRST", "+3V3", "+5V", "GND", "GND", "VIN"], (470, 270),
           "Arduino power 1x8: NC, IOREF (3.3 V), RESET, +3.3V, +5V, GND, GND, VIN (UM1724 Table 16)"),
    socket("CN8", 6, "ANALOG", ["PA0", "PA1", "PA4", "PB0", "A4", "A5"], (470, 330),
           "Arduino analog 1x6: A0 PA0, A1 PA1, A2 PA4, A3 PB0, A4 PC1 or PB9, A5 PC0 or PB8 (UM1724 Table 16)"),
    socket("CN5", 10, "D8-D15", ["PA9", "PC7", "PB6", "PA7", "PA6", "PA5", "GND", "VDDA", "PB9", "PB8"], (545, 270),
           "Arduino digital 1x10: D8 PA9, D9 PC7, D10 PB6, D11 PA7, D12 PA6, D13 PA5, GND, AREF (AVDD), D14 PB9, D15 PB8 "
           "(UM1724 Table 16)"),
    socket("CN9", 8, "D0-D7", ["PA3", "PA2", "PA10", "PB3", "PB5", "PB4", "PB10", "PA8"], (545, 340),
           "Arduino digital 1x8: D0 PA3, D1 PA2, D2 PA10, D3 PB3, D4 PB5, D5 PB4, D6 PB10, D7 PA8 (UM1724 Table 16)"),
    morpho("CN7", CN7_PINS, (320, 310), "ST morpho CN7, 2x19 2.54 mm (UM1724 Table 29, NUCLEO-F411RE)"),
    morpho("CN10", CN10_PINS, (400, 310), "ST morpho CN10, 2x19 2.54 mm (UM1724 Table 29, NUCLEO-F411RE; pin 18 NC, no PB11)"),
    jumper("JP4", "Jumper:SolderJumper_3_Bridged12", SJ3_BRIDGED12, "A4", {"A": "PC1", "C": "A4", "B": "PB9"}, (465, 375),
           "Solder jumper: A4 = PC1 (1-2, as delivered) or PB9 (2-3) (UM1724 Table 16: PC1 or PB9)"),
    jumper("JP6", "Jumper:SolderJumper_3_Bridged12", SJ3_BRIDGED12, "A5", {"A": "PC0", "C": "A5", "B": "PB8"}, (500, 375),
           "Solder jumper: A5 = PC0 (1-2, as delivered) or PB8 (2-3) (UM1724 Table 16: PC0 or PB8)"),
]
# Mounting holes, unplated 3.2 mm: three at the positions UM1724 Figure 5 gives, two of the board's own at the top.
HOLES = [("H1", (ARD_L, 27.93), "F", "by CN6 (UM1724 Figure 5)"), ("H2", (ARD_R, 29.20), "B", "by CN5 (UM1724 Figure 5)"),
         ("H3", (43.89, 80.00), "F", "bottom (UM1724 Figure 5)"), ("H4", (4.0, 4.0), "F", "top left"),
         ("H5", (66.0, 4.0), "F", "top right")]
for i, (ref, _, side, label) in enumerate(HOLES):
    PARTS.append(Part(ref, "Mechanical:MountingHole", "M3", HOLE, (250 + 18 * i, 400), {}, side=side,
                      fields={"Description": f"Mounting hole 3.2 mm, unplated, {label}"}))

# Board placement: (x, y, rotation) in mm, origin top-left. The headers and the three lower holes are
# where UM1724 Figure 5 puts them. Along the top edge: J1 (COM port and power), the reset and BOOT0
# buttons, the debug connector, the user button and LED, J2 (native USB). Below them, left to right:
# the CP2102N, the 5 V OR and the 3.3 V LDO, the VIN buck (DS41326 Figure 25: C5 across pins 3/4,
# C6 and L1 beside pins 5/6), J2's protection. The MCU sits between the headers with pin 1 at the
# top left: the LSE crystal Y2 against pins 3-4 (PC14 up past the VBAT/PC13 escapes, PC15 straight
# in), the HSE crystal Y1 just beyond it against pins 5-6 (PH1 straight in under Y2, PH0 between
# Y1's pad rows), each with its load capacitors and links beside its pads. H2 is fitted from the
# back, as a screw head on top would hit CN5; its 5.5 mm head circle (ISO 14580) clears CN5 pin
# 10's drill but not its pad ring (3.56 mm from the hole), so a nylon support belongs there.
PLACEMENT = {
    "CN7": (CN7_X, ROW1, 0), "CN10": (CN10_X, ROW1, 0),
    "CN6": (ARD_L, 41.90, 0), "CN8": (ARD_L, 64.76, 0), "CN5": (ARD_R, 55.62, 180), "CN9": (ARD_R, 77.46, 180),
    **{ref: (x, y, 0) for ref, (x, y), _, _ in HOLES},
    # top edge
    "J1": (17.0, USB_C_EDGE, 180), "J2": (55.0, USB_C_EDGE, 180), "J3": (35.0, 5.0, 0),
    "B2": (26.5, 3.0, 0), "B3": (26.5, 7.6, 0), "B1": (43.6, 3.0, 0),
    "LD2": (39.6, 64.0, 180), "R17": (37.0, 64.0, 0),
    # J1: protection, fuse, bleed, OR diode, R1/R2 under their CC contacts; the CP2102N with its 0.1 uF at
    # pins 6/7 and 4.7 uF beside them, the VBUS divider and RSTb pull-up at pins 8/9, D0/D1 jumpers
    "U5": (17.0, 11.8, 0), "R1": (19.1, 9.4, 270), "R2": (14.6, 10.0, 270), "F1": (21.6, 15.6, 90),
    "R3": (19.0, 15.8, 90), "D1": (25.0, 15.0, 90),
    "U2": (8.6, 16.8, 180), "C2": (10.6, 14.0, 0), "C4": (11.8, 15.0, 0), "C1": (11.05, 12.4, 0), "C3": (11.05, 10.3, 0),
    "R4": (5.4, 14.6, 180), "R5": (8.85, 12.2, 270), "R6": (7.4, 13.3, 180), "R7": (7.6, 21.2, 90), "R8": (9.6, 21.2, 90),
    "JP8": (5.0, 24.2, 0), "JP9": (5.0, 27.2, 0),
    # 3.3 V LDO, IDD jumper and its ammeter header, power LED, E5V diode
    "U3": (35.0, 14.8, 0), "C9": (28.4, 12.5, 0), "C10": (28.4, 17.1, 0),
    "JP1": (25.0, 21.0, 0), "J4": (24.0, 24.6, 90),
    "R13": (32.0, 21.0, 0), "LD3": (35.0, 21.0, 180), "D3": (30.8, 27.6, 0),
    # VIN buck (DS41326 Figure 25), reverse diode, second input capacitor C25, OR diode D5 above L1 (fed from
    # its output pad), plated GND pads TP3/TP4 at the capacitors' grounds
    "U4": (42.5, 20.5, 0), "C5": (42.5, 24.0, 0), "C6": (45.15, 20.0, 90), "L1": (49.3, 20.5, 0),
    "C7": (51.5, 25.9, 90), "C8": (47.3, 24.6, 0), "D4": (36.6, 26.8, 180), "D5": (49.0, 15.8, 0),
    "C25": (38.8, 22.7, 90), "TP3": (44.9, 26.8, 0), "TP4": (51.5, 29.3, 0),
    # J2 and U6 at x 55, so the pair runs down the channel east of the buck; R9/R10 under their CC contacts;
    # D2 beside D5; fuse, VBUS sense and bleed; R24/R25 (CN10 pins 12/14) beside the pair
    "U6": (55.0, 11.8, 0), "R9": (59.0, 11.2, 270), "R10": (51.0, 11.2, 270), "F2": (57.6, 15.8, 90),
    "D2": (46.5, 12.6, 0), "R11": (60.6, 13.6, 90), "R12": (60.6, 16.2, 90), "R23": (60.6, 18.8, 90),
    "JP7": (60.2, 22.4, 0), "R24": (52.8, 33.0, 0), "R25": (55.6, 33.0, 180),
    # MCU and its decoupling: VDD pins 19 and 32 on the bottom side, 48 on the right (C13 just above the USB
    # pair's entry, C15 north of the corner, both laid first so the pair cannot cut the corner), 64 on top
    "U1": (MCU[0], MCU[1], 0),
    "C11": (33.0, 58.4, 90), "C16": (39.3, 58.6, 90), "C12": (41.8, 58.4, 90), "C13": (43.65, 46.65, 0),
    "C15": (42.2, 41.6, 0), "C14": (31.4, 41.6, 90),
    "R14": (34.6, 39.2, 0), "R15": (37.2, 61.6, 0), "JP3": (34.4, 64.0, 0), "R22": (47.2, 49.0, 0),
    # VDDA: 100 nF at pins 12/13, then 1 uF and the bead; NRST capacitor at pin 7
    "C18": (27.6, 52.25, 0), "C17": (25.6, 52.25, 0), "FB1": (25.6, 54.2, 0), "C20": (28.2, 49.55, 180),
    # VBAT and PC13 escape up past the corner
    "C19": (27.3, 40.8, 0), "JP2": (24.0, 40.8, 0), "R16": (28.4, 38.3, 0),
    # LSE against pins 3-4, HSE against pins 5-6, load capacitors and links beside the pads
    "Y2": (27.3, 46.25, 90), "C23": (27.3, 43.2, 90), "C24": (25.05, 47.3, 0), "R20": (25.6, 43.7, 0), "R21": (25.05, 45.9, 0),
    "Y1": (21.9, 47.6, 90), "C21": (20.9, 43.5, 90), "C22": (22.9, 51.7, 90), "R18": (18.4, 43.5, 0), "R19": (20.4, 51.7, 0),
    # bottom side: ground pads under both crystals and their load capacitors
    "TP1": (20.18, 47.4, 0), "TP2": (25.5, 47.4, 0),
    # A4/A5 selection beside CN8
    "JP4": (16.5, 74.92, 0), "JP6": (16.5, 77.8, 0),
}
_unplaced = sorted({p.ref for p in PARTS} - set(PLACEMENT))
assert not _unplaced, f"parts without a board position: {_unplaced}"
for _p in PARTS:
    _p.pcb = PLACEMENT[_p.ref]

# Laid before the autorouter, in this order, and locked (pcb_build.py): the VBAT and PC13 escapes
# first, so the crystal lines go round them; then each crystal line, its load capacitor and its link;
# VCAP_1, VDDA and NRST at their pins; the buck's input, switch, bootstrap and output loops, its
# feedback line (round the buck on the top layer), D5's feed and C25; VDD pin 48's capacitors; the
# native USB pair, D+ (the inner line of the bend) then D-, connector to ESD pad to MCU, and J2's
# second contacts; the COM-port pair, D- (inner) then D+, and J1's second contacts; the CN10 links;
# last the CP2102N's supply pins to their capacitors.
PRIORITY = [
    (("U1", "1"), ("C19", "2")), (("U1", "2"), ("R16", "1")),
    (("U1", "4"), ("Y2", "2")), (("U1", "3"), ("Y2", "1")), (("U1", "6"), ("Y1", "1")), (("U1", "5"), ("Y1", "3")),
    (("Y2", "1"), ("C23", "1")), (("Y2", "2"), ("C24", "2")), (("Y1", "1"), ("C22", "2")), (("Y1", "3"), ("C21", "1")),
    (("R20", "2"), ("C23", "1"), "join"), (("R21", "2"), ("C24", "2"), "join"),
    (("R18", "2"), ("C21", "1"), "join"), (("R19", "2"), ("C22", "2"), "join"),
    (("U1", "30"), ("C16", "2")), (("U1", "13"), ("C18", "2")), (("U1", "7"), ("C20", "1")),
    # Each VSS pin to the ground end of the capacitor beside it (VSS 31 to VCAP_1's), each of which has
    # a ground via: with no via allowed in TP2, the 2026-10-21 rebuilds left one VSS pin or another on a
    # via-less sliver of top pour, up to 23 mm of track from a via.
    (("U1", "31"), ("C16", "1")), (("U1", "18"), ("C11", "2")), (("U1", "47"), ("C13", "2")),
    (("U1", "63"), ("C14", "2")),
    (("U4", "3"), ("C5", "1")), (("U4", "2"), ("U4", "3"), "join"), (("U4", "4"), ("C5", "2")),
    (("U4", "5"), ("C6", "1")), (("U4", "6"), ("C6", "2")), (("C6", "1"), ("L1", "1")),
    (("D4", "1"), ("C5", "1"), "join"),
    (("L1", "2"), ("C7", "2")), (("C8", "2"), ("L1", "2"), "join"), (("C8", "1"), ("C5", "2")),
    (("U4", "1"), ("L1", "2")), (("L1", "2"), ("D5", "2")), (("C25", "1"), ("D4", "1"), "join"),
    (("U1", "48"), ("C13", "1")), (("U1", "48"), ("C15", "1")),
    (("J2", "B6"), ("U6", "2")), (("U6", "2"), ("U1", "45")), (("J2", "B7"), ("U6", "3")), (("U6", "3"), ("U1", "44")),
    (("J2", "A6"), ("J2", "B6"), "join"), (("J2", "A7"), ("J2", "B7"), "join"),
    (("J1", "A7"), ("U5", "2")), (("U5", "2"), ("U2", "5")), (("J1", "A6"), ("U5", "3")), (("U5", "3"), ("U2", "4")),
    (("J1", "B6"), ("J1", "A6"), "join"), (("J1", "B7"), ("J1", "A7"), "join"),
    (("R24", "2"), ("U6", "2"), "join"), (("R25", "2"), ("U6", "3"), "join"),
    (("U2", "7"), ("C2", "1")), (("U2", "6"), ("C4", "1")), (("U2", "6"), ("U2", "7")),
    (("C2", "1"), ("C1", "1")), (("C1", "1"), ("C3", "1")),
    (("C2", "2"), ("C1", "2")), (("C4", "2"), ("C2", "2")), (("C1", "2"), ("C3", "2")),
]

TEXTS = [
    {"text": "EoS STM32 64  rev A", "x": 33.0, "y": 71.0, "size": 1.0, "layer": "B_SilkS", "bold": True, "mirror": True},
    {"text": "(c) 2026 Kartikeydheer Srivastava", "x": 33.0, "y": 73.0, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    {"text": "All rights reserved", "x": 33.0, "y": 74.4, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    # front: which USB-C is which, the buttons (RESET and BOOT0 sit side by side; DFU needs the right one), and
    # every solder jumper the README asks a user to cut or bridge
    {"text": "COM", "x": 9.3, "y": 7.6, "size": 1.0}, {"text": "USB", "x": 47.9, "y": 9.6, "size": 1.0},
    {"text": "RESET", "x": 23.3, "y": 3.0, "size": 0.8, "angle": 90},
    {"text": "BOOT0", "x": 23.3, "y": 7.6, "size": 0.8, "angle": 90},
    {"text": "USER", "x": 47.3, "y": 3.0, "size": 0.8, "angle": 90},
    {"text": "IDD", "x": 25.0, "y": 18.6, "size": 0.8}, {"text": "VBUS>PC9", "x": 60.2, "y": 24.5, "size": 0.8},
    {"text": "D0", "x": 2.2, "y": 24.2, "size": 0.8}, {"text": "D1", "x": 2.2, "y": 27.2, "size": 0.8},
    {"text": "A4", "x": 19.6, "y": 74.92, "size": 0.8}, {"text": "A5", "x": 19.6, "y": 77.8, "size": 0.8},
]

BOARD = Board(
    name="eos-stm32-64",
    title="EoS STM32 64",
    revision="A",
    date="2026-10-12",
    company=OWNER,
    licence=LICENCE,
    contact=CONTACT,
    licence_terms=LICENCE_TERMS,
    credits=["Nucleo-64 outline (70.00 x 82.50 mm), Arduino and ST morpho header positions and mounting holes: "
             "STMicroelectronics UM1724 Rev 17, Figure 5 (mechanical dimensions); facts only, no file of ST's copied",
             "Arduino and ST morpho header signal assignment for NUCLEO-F411RE: STMicroelectronics UM1724 Rev 17, "
             "Table 16 and Table 29; facts only"],
    width=W,
    height=H,
    corner_radius=1.5,
    thickness=1.6,
    layers=2,
    # A via beside each ground pad of the crystal load capacitors, the VBAT capacitor and Y1's case:
    # AN2867 section 7.1 asks for the oscillator ground to reach the MCU ground nearby. Without the via
    # that sat in TP2 (no longer allowed), that group hung on one 0.15 mm track (2026-10-20 rebuild).
    # And one beside each of the MCU's VSS pads: VSS 18 (with C11) sat on a via-less sliver on master,
    # and VSS 63 did on the first rebuild with the crystal vias.
    # And the VDDA/VSSA capacitors and the NRST capacitor: the analog ground group (VSSA 12, C17, C18) hung
    # on one 0.15 mm track on the 2026-10-21 rebuild, because a fine-pitch pin has no room for its own via.
    ground_vias=["U1", "C11", "C12", "C13", "C14", "C16", "C17", "C18", "C19", "C20", "C21", "C22", "C23",
                 "C24", "Y1"],
    parts=PARTS,
    power_nets={"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V"},
    flagged_nets=["GND", "+5V", "VDD_MCU", "VDDA", "VBAT", "VIN_P"],
    priority_routes=PRIORITY,
    no_fanout=["TP1", "TP2"],   # the generator's 2 x 2 vias in an exposed pad would land in the crystal copper above
    router_keepouts=[(52.8, 14.0, 53.8, 28.8), (54.45, 14.0, 56.75, 28.8), (42.6, 18.5, 48.3, 19.2)],
    maze_via_cost_mm=5.0,      # the priority routes stay on the top layer: the buck's feedback line goes round
                               # the buck rather than under its switch node (DS41326 layout item 3)
    headings=[((30, 45), "J1: USB-C, COM port and power"), ((60, 130), "CP2102N USB-UART on 3.3 V, VBUS-sensing J1"),
              ((185, 45), "5 V rail: J1, J2, E5V, VIN (buck), ORed"), ((200, 160), "3.3 V LDO, power LED, IDD jumper"),
              ((340, 45), "J2: USB-C to the STM32 USB OTG FS"), ((490, 45), "Debug connector, buttons, user LED"),
              ((175, 245), "STM32F411RET6"), ((90, 250), "VDD, VCAP, VDDA, VBAT, NRST, BOOT, PA10"),
              ((30, 285), "HSE 8 MHz, LSE 32.768 kHz"), ((300, 245), "ST morpho (UM1724 Table 29)"),
              ((450, 245), "Arduino Uno V3 (UM1724 Table 16)"), ((240, 390), "Mounting holes"), ((35, 392), "Power nets")],
    power_block=(40.64, 400.0),
    notes=[((330, 380), "EoS STM32 64, rev A. Designed by Kartikeydheer Srivastava.\n"
                       "Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved; see LICENSE.txt.\n"
                       "Values from ST DS10314 Rev 8, RM0383 Rev 3, AN4488 Rev 7, AN2867 Rev 24, AN2606 Rev 70;\n"
                       "Silicon Labs CP2102N Rev. 1.5; Diodes DS37274, DS41326, DS13004; Nexperia PMEG3010CEH;\n"
                       "Littelfuse SP05xxBA; Bourns SRP5030T; ECS ECX-53B; Abracon ABS07-120; TDK MMZ1608; Kingbright.\n"
                       "Firmware: HSE 8 MHz crystal (not bypass); LSE high drive (LSEMOD = 1);\n"
                       "USB: J2's VBUS on PC9 (JP7): keep the D+ pull-up off (SDIS) while PC9 is low.\n"
                       "BOOT0: hold B3, press B2 (DFU). RDP Level 2 locks out SWD and DFU for good.\n"
                       "IDD: cut JP1, ammeter across J4. JP8/JP9 cut: D0/D1 free of the COM port.")],
    netclasses={"Power": {"track": 0.4, "clearance": 0.15}, "Supply": {"track": 0.3, "clearance": 0.15},
                "USB": {"track": 0.2, "clearance": 0.15}},
    net_to_class={**{n: "Power" for n in ("VBUS_VCP", "U5V", "VBUS_USB", "VUSB", "E5V", "VIN", "VIN_P", "BUCK_SW",
                                          "5V_BUCK", "+5V")},
                  "+3V3": "Supply", "VDD_MCU": "Supply",
                  **{n: "USB" for n in ("VCP_D+", "VCP_D-", "USB_DP", "USB_DM")}},
)
