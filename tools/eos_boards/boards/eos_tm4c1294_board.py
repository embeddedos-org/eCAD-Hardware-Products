"""EoS TM4C1294 Board: a two-site BoosterPack-compatible TM4C1294NCPDT board with 10/100 Ethernet, designed by Kartikeydheer Srivastava.

Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved: this design file is not under
the repository's MIT licence; see boards/eos/eos-tm4c1294-board/LICENSE.txt.

A 124.46 x 55.88 mm six-layer board for the TI TM4C1294NCPDT (Arm Cortex-M4F at 120 MHz, 1 MB
flash, integrated 10/100 Ethernet MAC and PHY, USB 2.0, TQFP-128) with two 40-pin BoosterPack
sites and a 98-hole breakout row ("BoosterPack-compatible" and "for the EK-TM4C1294XL form factor"
are nominative use: the board is not a TI product). It does the job of TI's EK-TM4C1294XL but is
drawn from the chip makers' documents only: no design file of TI's (schematic, layout, CAD,
Gerbers, BOM) was opened. Sources:

* TI SPMS433B, "Tiva TM4C1294NCPDT Microcontroller Data Sheet" (June 18, 2014): "the data sheet".
* TI SPMA056, "System Design Guidelines for the TM4C129x Family of Tiva C Series
  Microcontrollers" (October 2013): "the guide".
* TI SPMZ850G, "Tiva C Series TM4C129x Microcontrollers Silicon Revisions 1, 2, and 3" (errata,
  revised March 2017): "the errata".
* TI SPMU365C, "EK-TM4C1294XL User's Guide" (revised October 2016), published text pages only:
  Table 1-1 (p. 6), the BoosterPack and breakout pin tables 2-1 to 2-4 (pp. 9-19) and the
  dimension drawing, Figure 4-1 (p. 26). Used as mechanical and pinout facts only.

Form factor (SPMU365C Figure 4-1, read off the drawing in inches from the lower-left corner; here in
mm from the top-left): outline 4.9 x 2.2 in. BoosterPack 2's ten-pin rows run from x = 1.45 in (pin
10) to 2.35 in (pin 1), BoosterPack 1's from 3.95 to 4.85 in, each site with its outer rows 0.05 in
and 1.85 in from the top edge and its inner rows 0.15 in and 1.75 in (outer rows 1.8 in apart, inner
1.6 in, as the 40-pin standard has them); both sites face the same way, pin 1 at the right end of
each row. The 98-hole breakout (X11 in SPMU365C) is two rows of 49 at 0.05 in and 0.15 in from the
bottom edge, x = 0.05 to 4.85 in, odd holes in the upper row with hole 1 at the right. Three
0.125 in holes at (3.25, 0.15), (0.85, 1.55) and (3.75, 1.35) in from the top-left. The signal on
each header pin follows SPMU365C Tables 2-1 to 2-4, so BoosterPacks and software written for that
form factor find the same GPIOs. Everything else (circuit, parts, placement, routing) is this
board's own.

Pin map (SPMU365C Tables 2-1 to 2-4). Part J1 holds BoosterPack 1's rows A (outer, odd pins) and B
(inner, even pins), J2 its rows C (inner, odd) and D (outer, even); J3 and J4 the same for
BoosterPack 2; J5 is the 98-hole breakout, pin n = hole n.

  BP1 A: 3V3 PE4 PC4 PC5 PC6 PE5 PD3 PC7 PB2 PB3     B: 5V GND PE0 PE1 PE2 PE3 PD7 PA6 PM4 PM5
  BP1 C: PF1 PF2 PF3 PG0 PL4 PL5 PL0 PL1 PL2 PL3     D: GND PM3 PH2 PH3 RST PD1 PD0 PN2 PN3 PP2
  BP2 A: 3V3 PD2 PP0 PP1 PD4* PD5* PQ0 PP4 PN5 PN4   B: 5V GND PB4 PB5 PK0 PK1 PK2 PK3 PA4 PA5
  BP2 C: PG1 PK4 PK5 PM0 PM1 PM2 PH0 PH1 PK6 PK7     D: GND PM7 PP5 PA7 RST PQ2+PA3 PQ3+PA2 PP3 PQ1 PM6

  * BP2 A.5/A.6 carry PD4/PD5 (UART2) or, with JP1/JP2 turned, PA0/PA1 (CAN0Rx/CAN0Tx, Table 26-5
    encoding 7), the bridge then moving to UART2; PQ2/PA3 and PQ3/PA2 share BP2 D.6/D.7 through 0 ohm
    links R40/R41 (SPI MOSI/MISO and I2C8 SDA/SCL, as SPMU365C 2.1.6.2 describes), so firmware keeps
    the unused one of each an input. Breakout hole 58 has PB0 through 1 kohm (errata GPIO#09), hole
    60 (PB1) is not connected: PB1 senses USB VBUS here. Hole 34 is VREFA+ (see below).

Every value follows a data sheet:

* Supply: VDD, VDDA (pin 8) and VREFA+'s link on one 3.3 V rail, the inner layer 4 plane (the guide
  3.4.1, 3.4.4: VDD and VDDA "connected directly to the same +3.3V power source"; data sheet Table
  27-6, VDD 2.97-3.63 V). 0.1 uF X7R 0402 at the VDD pins, each joined to its pin before routing (the
  guide 3.4.3: "one decoupling capacitor in close proximity to each power-supply pin"; Figure 18): one
  each at pins 7, 16, 39, 47, 69, 79, 90, 101, 113 and 122, one shared by 26 and 28 (PQ3 between
  them) and one by 51 and 52 (adjacent). Those of pins 39, 51/52 and 90 (C4, C6, C46), and RST's
  10 nF (C27), sit on the bottom side under the chip, as the guide's 128-pin example (Table 7) puts
  most of its capacitors on the back: each pin reaches its capacitor through a via inside the pad
  ring, and the pins' outer ends stay free for their neighbours' escapes (on the top side they had
  boxed PG0/PG1, PA2/PA4 and PM4 in, and pin 90 had no way to the plane). Ground pins 17, 48, 80, 114
  and GNDA 10 are joined to their neighbour capacitor's ground pad, which has its via to the inner
  ground plane; pins 55 and 58 (between the Ethernet pins) go inward to C6's ground pad. 10 uF bulk near
  the chip (the guide 3.4.3: VDD and VDDA bulk "typically between 2 uF and 22 uF"). VDDA: 1 uF and
  0.1 uF at pin 8.
* VDDC, the core LDO's filter (data sheet Table 27-15: CLDO 2.5-4.0 uF, ESR <= 100 mohm, "as close
  as possible to pin 115"; the guide 3.4.2 and Table 6: 2.2 uF, 1.0 uF and 0.1 uF closest to pin 115,
  0.1 uF near pin 87, 10 % ceramics totalling 3.3-3.4 uF): 3.4 uF nominal, 3.06-3.74 uF at +-10 %.
  In the guide's order: pin 115 drops through a via inside the pad ring to the 2.2 uF (C19), nearest,
  then the 1 uF (C20) and the 0.1 uF (C21), all three on the bottom side under the chip beside that
  via, each ground pad with a via of its own to the ground plane; on the top side the pins round
  pin 115 leave no room for a 0603 at its end, and a capacitor there boxed PJ0 (pin 116) in. Pin 87
  drops through its own via to its 0.1 uF (C22, bottom side) and on, through the bottom layer, to C20
  (the device USB pair runs between the two pins inside the pad ring). VDDC feeds nothing else.
* ADC reference: VREFA+ (pin 9) from the 3.3 V rail through a 0 ohm link R43 with 1 uF + 0.01 uF to
  GNDA at the pin (the guide 3.4.5: VREFA+ to VDDA when the ADC need not be precise, CREF 1 uF and
  0.01 uF "as close as possible"; Table 26-7). It also reaches breakout hole 34: remove R43 to feed
  an external reference there (data sheet Table 27-34 note c: no current-limiting resistor).
* 25 MHz crystal (the integrated PHY needs 25 MHz +-50 ppm, data sheet Tables 27-50, 27-16 note; the
  guide 4.1.5): NDK NX3225GA-25.000M-STD-CRG-2 (NDK NX3225GA sheet: +-20 ppm at 25 C, +-30 ppm over
  -40..+85 C, ESR <= 50 ohm for 20-50 MHz, CL 8 pF, drive 200 uW max), one of the crystals TI
  simulated: C1 = C2 = 12 pF, Rs = 2 kohm, worst-case drive 181 uW (data sheet Table 27-24). CL =
  12 || 12 + C0 1.1 + CPKG 0.5 + CPCB 0.5 = 8.1 pF (Table 27-23). Rs sits between OSC1 and the crystal
  (Table 27-24 text; the guide 3.6.2). Pads 2 and 4 to ground (NDK: "better to connect with a GND").
* 32.768 kHz crystal: Abracon ABS07-32.768KHZ-T (ABS07 sheet, revised 08-10-22: CL 12.5 pF, ESR <= 70
  kohm at -40..+85 C, C0 0.9-1.2 pF typical, 2.0 pF max, drive 0.5 uW max). Data sheet Table 27-22:
  C1, C2 12-24 pF, ESR <= 50 kohm with OSCDRV = 0 and <= 75 kohm with OSCDRV = 1, which needs C1,2 >
  18 pF; CSHUNT <= 4 pF; drive 0.25 uW. So C1 = C2 = 20 pF and firmware sets OSCDRV: with the errata's
  corrected equation (ELEC#04: CL = C1 C2 / (C1 + C2) + C0 + CPKG + CPCB), CL = 10 + 1.2 + 0.5 + 0.5 =
  12.2 pF typical, 13.0 pF with C0 at its 2.0 pF maximum; CSHUNT 2.2-3.0 pF.
* Hibernation: VBAT from 3.3 V through a BAT54J Schottky (Nexperia BAT54J: VF <= 240 mV at 0.1 mA),
  then RBAT = 51 ohm and CBAT = 0.1 uF (data sheet Figure 7-2 and section 7.3.2 note: 51 ohm +-5 %,
  0.1 uF; the guide 3.4.6, Figure 19). Their 5.1 us keeps VBAT's rise under 0.7 V/us (Table 27-29;
  errata ELEC#02): 3.1 V / 5.1 us = 0.61 V/us even for a step. The diode also keeps VBAT under its
  3.6 V maximum when VDD sits at its own 3.63 V maximum (Table 27-29 note a: "any voltage input
  higher than VBAT Max, must be connected through a diode"). No coin cell: the RTC runs while USB
  power is present, and hibernation is VDD3ON mode (VDD stays on); nothing survives unplugging.
  WAKE: 200 kohm pull-up to VBAT's supply (data sheet Figure 7-2, the crystal configuration; the
  guide 4.15 suggests 1 Mohm, "connected to the same supply voltage that the VBAT pin is connected
  to": the data sheet's figure for a crystal is followed), the button to ground through 470 ohm at
  the pin (the guide 3.5.1 asks for a series resistor on a switch); also breakout hole 95.
* HIB (pin 65) and the Ethernet termination supply: "When entering hibernation in VDD3ON mode, the
  supply rails to the Ethernet resistors R1, R2, R3, R4 found in Figure 20-13 ... must be switched
  off" (data sheet 7.3.9 and the note under Figure 20-13). HIB is asserted (low) in hibernation
  whatever the VDD3ON bit says (HIBCTL, bit 8) and, with VDD3ON set, must not switch the 3.3 V
  regulator. So HIB drives the ON pin of a TI TPS22917 load switch (SLVSDW8B: active-high ON, VIH
  1 V, 80-110 mohm at 3.3-5 V) that makes ETH_VTERM, the supply of the four 49.9 ohm resistors.
  The transformer's centre taps are on ETH_VTERM too: their windings join them to the same lines
  in DC, so leaving them on 3.3 V would hold the lines at 3.3 V with the resistors' supply off
  (inferred; the data sheet names only the resistors). QOD reaches VOUT through 100 ohm, so the
  rail is pulled to 0 V through 250 ohm in all (SLVSDW8B 9.3.3; "Output may not discharge
  completely if QOD is not connected to VOUT"); CT is open (fastest turn-on), and 1 uF sits at
  VIN (SLVSDW8B section 11). The rail reaches the resistors and the centre taps by tracks, so the centre-tap
  capacitors are 1 uF (the guide 4.1.2: "If the center tap connects to a PCB trace instead of a
  plane, the capacitor value should be 1 uF or greater"), and each pair's resistors have their
  0.1 uF (Figure 20-13).
* Reset: data sheet Figure 5-3: RPU 10 kohm, C1 10 nF at the pin, RS 470 ohm in series with the
  button (the guide 3.5.1). RST also reaches both sites' D.5, breakout hole 94 and the debug header.
* Ethernet (data sheet 20.4.3 and Figure 20-13; the guide 4.1): EN0TXOP/EN0TXON/EN0RXIP/EN0RXIN each
  pulled to ETH_VTERM, the switched 3.3 V (see HIB above), by 49.9 ohm 1 % at the chip, one
  terminal on the line (the guide 4.1.1, 3.3.8);
  RBIAS 4.87 kohm 1 % within 6 mm of pin 59 with its own ground via (the guide 4.1.4; data sheet
  Table 27-49: 4.82-4.92 kohm). Magnetics and jack: Wurth Elektronik 7499010121A (WE-RJ45LAN, data
  sheet version 003.001, 2024-07-26: 10/100BASE-TX, 1:1 +-2 % on transmit and receive with centre
  taps, 350 uH minimum, common-mode chokes, Bob Smith termination 4 x 75 ohm and 1000 pF 2 kV to pin
  8, shielded, tab up, green LED 10 (+) to 9, yellow LED 12 (+) to 11, VF 1.8-2.4 V at 20 mA). A
  symmetrical 1:1 transformer is what the data sheet asks for Auto-MDIX (20.4.3). Centre taps (2,
  5) on ETH_VTERM, each with its own 1 uF on the bottom side beside its pin (data sheet Figure 20-13
  note: "located near the physical pins of the transformer"; the guide 4.1.2). Shield and pin 8 are chassis, tied to ground through 1 Mohm and
  4.7 nF 2 kV (data sheet Figure 20-13). ESD: TI TPD4EUSB30 (SLVSAC2G: 5.5 V standoff, 0.8 pF DQA,
  IEC 61000-4-2 level 4), one per pair on the device side between the termination and the jack (the
  guide 4.1.6, which names this position for a device-side array), lines passing straight through
  its flow-through pads. The tab-up jack's pins run in the same order as the chip's (RD-, RD+, TD-,
  TD+ against EN0RXIN, EN0RXIP, EN0TXON, EN0TXOP), so the pairs reach it MDI-wired, with no crossing
  and no via. Jack LEDs on PF0 (EN0LED0) and PF4 (EN0LED1), sourcing current (the guide 4.1.7), 470
  ohm: (3.3 - 1.8) / 470 = 3.2 mA.
* Layout rules for the pairs (the guide 4.1.8, 3.2.3.2, 3.3.8): top layer over the inner ground
  plane, 100 ohm differential target, each pair's lines length-matched within 1.27 mm, the pairs 1.27 mm
  apart where the pins allow (pins 54 and 56 are 0.8 mm apart), termination near the chip, no vias. The
  README's Layout section gives what the routed board measures. See the stack-up note at the end.
* USB device port (J7, USB-C): USB0DP/USB0DM (PL6/PL7) straight to the connector through an
  SP0503BAHTG (Littelfuse SP05xxBA: three TVS channels to ground, 5.5 V standoff, <= 100 nA); the PHY
  has its own D+ pull-up (data sheet 21.2 note). 5.1 kohm Rd on CC1 and CC2 (TI SLVSFJ9 10.3.14.2).
  VBUS to PB1 (USB0VBUS) through 100 ohm (the guide 4.3.1; PB1 is the one 5 V-tolerant pin, data
  sheet 27.14; the errata GPIO#09 workaround 2 points to these USB rules), so firmware can drop the
  pull-up when the host leaves (data sheet 21.2 note: a self-powered device must watch VBUS). A 10
  kohm bleed takes VBUS down within tens of ms of an unplug. Device only: firmware forces device mode
  (USBGPCS DEVMOD), so PB0 is a free GPIO.
* Debug: a 10-pin Cortex Debug header (the guide Table 9) on PC0-PC3 and RST in place of TI's
  on-board ICDI, whose firmware is TI's: Samtec FTSH-105-01-L-DV-K, keyed. The chip's JTAG pins
  have internal pull-ups, enough while the lines are under 2 in (the guide 3.7.1).
* USB-UART (J6): CP2102N-A02-GQFN20 (Silicon Labs CP2102N data sheet Rev. 1.5) as on EoS TM4C123
  Board: on the board's 3.3 V with its regulator unused (Figure 2.3, VREGIN tied to VDD), so it is
  never unpowered while the MCU is (an unpowered CP2102N's inputs are rated only VIO + 2.5 V, Table
  3.10). 4.7 uF + 0.1 uF on VREGIN and on VDD, 1 kohm RSTb pull-up (section 2.1). VBUS sense: the
  22.1 kohm / 47.5 kohm divider of Figure 2.6 (5 V reads 3.41 V, 4.4 V reads 3.0 V, above VIH = VIO -
  0.6 V, Table 3.7) plus a 5.1 kohm bleed: the pin stays under VIL = 0.6 V unless over 185 uA is pushed
  into VDBG, and only the TPS2116's leakage into its unselected input can push any. TXD and RXD reach UART0 (PA0/PA1,
  the guide 4.6's debug UART and the ROM boot loader's) through 1 kohm each, which caps a driver fight
  at 3.3 mA, and through jumpers JP1/JP2 (see above). ESD: SP0503BAHTG (CP2102N Figure 2.5).
* Power: each USB-C port has a Littelfuse 1206L075THYR polyfuse (1206L data sheet, revised 10/29/21:
  0.75 A hold at 20 C, 0.65 A at 40 C, 1.50 A trip, R1max 0.29 ohm). A TI TPS2116 (SLVSFG1A) picks
  the 5 V source in priority mode: MODE on VIN1 and a 27 kohm / 10 kohm divider on PR1 from VIN1 (the
  device port, on the mux's left as the board lays out), so VIN1 is used down to 3.7 x VREF =
  3.40-4.00 V and VIN2 (the debug port) otherwise (7.6.1, Table 6.5: VREF 0.92-1.08 V); it blocks
  reverse current, so neither host is ever fed by the other or by a BoosterPack (7.3.4). 1 uF on each input, 2 x 22 uF on VOUT (soft start wants >= 0.1
  uF, 7.3.2). 3.3 V: TI TLV62569DBV buck (SLVSDG1C: 2.5-5.5 V in, 2 A, 1.5 MHz, VFB 0.588-0.612 V)
  with TI's standard filter, Coilcraft XAL4020-222ME (2.2 uH +-20 %, 38.7 mohm max, Isat 5.6 A;
  Coilcraft document 806-1) and 10 uF X7R 0805 out, 4.7 uF X7R 0805 in (SLVSDG1C Tables 3 and 4);
  feedback 453 kohm / 100 kohm: 0.6 x (1 + 4.53) = 3.318 V, 3.25-3.38 V over VFB's range, inside
  VDD's 2.97-3.63 V; 6.8 pF feed-forward across the upper resistor (8.2.2.2). EN tied to VIN.
  Current: the MCU 133.4 mA IDD maximum in Run mode at 120 MHz with every peripheral, the MAC and the
  PHY on (Table 27-63, SRAM loop, 85 C; 129.9 mA for the flash loop) plus 3.03 mA IDDA, the PHY's line
  drivers about 50 mA more through the termination (estimated: 1 V peak into 25 ohm, data sheet Table
  27-49), the CP2102N 13.7 mA (Table 3.2), the LEDs 16.9 mA (five at 2.1 mA, two jack LEDs at 3.2 mA):
  about 217 mA of 3.3 V. The buck delivers that from 4.75 V at about 0.17 A input (90 % efficiency
  read from SLVSDG1C Figure 6; an estimate). The shared budget is the USB port's 500 mA at 5 V: the
  BoosterPacks and the breakout together may take I(5 V pins) + 0.75 x I(3.3 V pins) <= 300 mA (0.75 =
  3.3 / (5 x 0.9)), about 470 mA in all. At 0.47 A in, the fuse (0.29 ohm) and the TPS2116 (0.06 ohm)
  drop 0.16 V, and the 0.3 mm 5 V tracks (most of them on inner layers) add the drop the README's
  Layout section measures. Power LED: Kingbright APTD1608LCGCK (DSAO7432, VF 1.9 V typ at 2 mA) through
  680 ohm: 2.1 mA.
* User I/O: LEDs on PN1, PN0, PF4 and PF0 (Kingbright APTD1608LCGCK, 680 ohm, 2.1 mA; inside the 8 mA
  drive, data sheet Table 27-7); PF0 and PF4 are EN0LED0 and EN0LED1, so they can also show the
  PHY's link and activity. Buttons on PJ0 and PJ1 to ground through 1 kohm (they also reach the
  breakout): internal pull-ups 12.1-20.2 kohm (13.8-31.4 for PJ1, a slow pad), so a pressed button
  reads under 3.63 x 1 / 13.1 = 0.28 V < VIL = 0.35 VDD (Tables 27-7, 27-34, 27-35).
* I2C pull-ups 2.2 kohm on PB2/PB3 (BP1 A.9/A.10, I2C0) and PN5/PN4 (BP2 A.9/A.10, I2C2) (the guide
  4.7: "must be externally pulled-up to 3.3V ... Typical pull-up values are 2.2 kohm"). 10 kohm
  pull-ups on the chip-select positions BP1 D.3 (PH2), BP2 D.3 (PP5) and BP2 D.9 (PQ1, SSI3Fss: the
  guide 4.5 asks for one on SSIxFSS), so a BoosterPack's SPI device sees no access before firmware.
* Headers: Samtec SSW-110-23-F-D, female with long male leads (the BoosterPack Pinout Standard's
  stackable part, as on EoS TM4C123 Board). The breakout is pads only, like the reference board's
  (SPMU365C 2.1.6.3 names Samtec TSW-149-09-L-S-RE / TSW-149-08-L-S-RA right-angle rows for it).

Six layers: top signal, inner 1 ground, inner 2 and inner 3 signal, inner 4 3.3 V, bottom signal, the
guide's six-layer stack (3.2.2.1, Figure 6: "Stack-ups greater than four layers can be used if
desired for high density designs"). The guide recommends four layers for most designs (3.2.1), for
"a solid ground plane reference for USB and Ethernet signals that have a specific impedance target"
and low-impedance supply planes; six keep both planes and add two routing layers. This board is the
dense case: 90 GPIOs leave a 0.4 mm-pitch TQFP-128 for two BoosterPack sites and a 98-hole breakout,
most of them to two places. On four layers (two signal layers) the autorouter still left 63 of its
connections open after 12 passes and stopped improving. The Ethernet and USB pairs stay on the top
layer over the inner ground plane; the 3.3 V plane (inner 4) never lies directly under them. Two
layers would need 30 mil lines 7 mil apart for 100 ohm (the guide Table 4) and leave no clean ground
under 128 pins. Every net that enters the TQFP-128 (0.25 mm pads at 0.4 mm pitch) is 0.15 mm wide,
the device USB pair 0.13 mm (it passes the chip's corner between pins 32 and 33, where two 0.15 mm
lines do not fit).
"""

from __future__ import annotations

from ..design import NC, Board, Part, USB_C_EDGE
from .owner import CONTACT, LICENCE, LICENCE_TERMS, OWNER

R0402 = "Resistor_SMD:R_0402_1005Metric"
R0603 = "Resistor_SMD:R_0603_1608Metric"
R1206 = "Resistor_SMD:R_1206_3216Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C1206 = "Capacitor_SMD:C_1206_3216Metric"
C1812 = "Capacitor_SMD:C_1812_4532Metric"
HDR = "Connector_PinHeader_2.54mm:PinHeader_"
KMR2 = "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2"
LED0603 = "LED_SMD:LED_0603_1608Metric"
DS = "TI SPMS433B"
GUIDE = "TI SPMA056"
CP2102N = "Silicon Labs CP2102N data sheet Rev. 1.5"
RD = "TI SLVSFJ9 section 10.3.14.2: a sink exposes Rd = 5.1 kohm on CC1 and CC2"
STACK = "female, long male leads, as TI's BoosterPack Pinout Standard (Sept 1, 2013) p. 2 asks and recommends"
MUX = "TI SLVSFG1A"
BUCK = "TI SLVSDG1C"

# Murata parts, as on EoS TM4C123 and EoS F280049C Boards
C100N = "GRM155R71C104KA88D"     # 100 nF 16 V X7R 0402
C10N = "GRM155R71H103KA88D"      # 10 nF 50 V X7R 0402
# MPNs checked on Murata's product database (pimapi.murata.com, 21 Oct 2026): every Murata part below is "In
# Production"; GRM188R71C105KA12, GRM188R61A475KE15, GRM21BR71A475KA73, GRM21BR71A106KE51, GRM31CR61C226ME15 and
# GRM21BR61A106KE19 are "To be discontinued" and GRM1555C1H200JA01 "NRND", so they were replaced
C1U = "GCM188R71C105KA64D"       # 1 uF 16 V X7R 0603
C2U2 = "GRM188R71A225KE15D"      # 2.2 uF 10 V X7R 0603
C4U7 = "GRM188R61C475KE11D"      # 4.7 uF 16 V X5R 0603
C4U7_BUCK = "GRM21BR71A475KE51L"  # 4.7 uF 10 V X7R 0805 (SLVSDG1C Table 3)
C10U_BUCK = "GRM21BR71A106KA73L"  # 10 uF 10 V X7R 0805 (SLVSDG1C Table 3)
C22U = "GRM31CR71A226KE15L"      # 22 uF 10 V X7R 1206


def res(ref, value, a, b, sch, desc, fp=R0402):
    # no single vendor is required (as on EoS RA4M2 Board): any thick-film chip resistor of the stated value and
    # tolerance with the rating below will do. The largest dissipation is the termination's, peaks of 2.5 V across
    # 49.9 ohm in 10 Mb/s mode, where SPMA056 4.1.1 finds 0402 parts' rating acceptable.
    size = {R0402: " 0402", R1206: " 1206"}[fp]
    spec = {R0402: " thick film, 62.5 mW or more", R1206: " thick film, 250 mW or more, 200 V or more"}[fp]
    assert size in desc, ref
    desc = desc.replace(size, size + spec, 1)
    return Part(ref, "Device:R_Small", value, fp, sch, {"1": a, "2": b}, fields={"Description": desc})


def cap(ref, value, a, b, sch, desc, fp=C0402, mpn=None, maker="Murata"):
    return Part(ref, "Device:C_Small", value, fp, sch, {"1": a, "2": b},
                fields={"Description": desc, **({"Manufacturer": maker, "MPN": mpn} if mpn else {})})


def button(ref, value, a, sch, desc):
    return Part(ref, "Switch:SW_Push", value, KMR2, sch, {"1": a, "2": "GND"},
                fields={"Manufacturer": "C&K", "MPN": "KMR221G LFS", "Description": desc})


def led(ref, value, anode, sch, desc):
    return Part(ref, "Device:LED_Small", value, LED0603, sch, {"A": anode, "K": "GND"},
                fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LCGCK", "Description": desc})


def header(ref, value, odd, even, sch, desc):
    """A 2x10 BoosterPack header part: odd pins along the first row, even pins along the second."""
    return Part(ref, "Connector_Generic:Conn_02x10_Odd_Even", value, HDR + "2x10_P2.54mm_Vertical", sch,
                {**{str(2 * k + 1): odd[k] for k in range(10)}, **{str(2 * k + 2): even[k] for k in range(10)}},
                fields={"Manufacturer": "Samtec", "MPN": "SSW-110-23-F-D", "Description": f"{desc}, 2x10 2.54 mm, {STACK}"})


def usb_c(ref, prefix, vbus, sch, desc):
    return Part(ref, "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
                sch, {"VBUS": vbus, "GND": "GND", "CC1": f"{prefix}_CC1", "CC2": f"{prefix}_CC2",
                      "D+": f"{prefix}_D+", "D-": f"{prefix}_D-", "SBU1": NC, "SBU2": NC, "SHIELD": "GND"},
                fields={"Manufacturer": "Korean Hroparts", "MPN": "TYPE-C-31-M-12", "Description": desc})


def esd(ref, prefix, vbus, sch, swap=False):
    """SP0503BAHTG: pin 1 the common (ground), pins 2-4 one TVS each (Littelfuse SP05xxBA pinout).
    Pins 2, 3 and 4 are the same diode to the common anode, so ``swap`` puts D+ on pin 3 and D- on
    pin 2 where that keeps the pair from crossing."""
    dp, dm = ("3", "2") if swap else ("2", "3")
    return Part(ref, "Power_Protection:SP0503BAHT", "SP0503BAHTG", "Package_TO_SOT_SMD:SOT-143", sch,
                {"1": "GND", dp: f"{prefix}_D+", dm: f"{prefix}_D-", "4": vbus},
                fields={"Manufacturer": "Littelfuse", "MPN": "SP0503BAHTG",
                        "Description": "USB ESD, 3 TVS channels to ground (VBUS, D+, D-), 5.5 V standoff, at the connector; "
                                       f"no path from D+/D- into VBUS (Littelfuse SP05xxBA; {CP2102N} Figure 2.5)"})


def fuse(ref, a, b, sch, what):
    return Part(ref, "Device:Polyfuse_Small", "750mA", "Fuse:Fuse_1206_3216Metric", sch, {"1": a, "2": b},
                fields={"Manufacturer": "Littelfuse", "MPN": "1206L075THYR",
                        "Description": f"PTC fuse 0.75 A hold (0.65 A at 40 C), 1.50 A trip, 8 V, R1max 0.29 ohm, 1206, {what} "
                                       "(Littelfuse 1206L, revised 10/29/21)"})


def eth_esd(ref, neg, pos, sch, what):
    """TPD4EUSB30 (DQA), flow-through: a line enters pad 1 or 2 and leaves the pad opposite (10, 9);
    channels 2 (pads 4/7, 5/6) are unused."""
    return Part(ref, "EoS_Parts:TPD4EUSB30_FlowThrough", "TPD4EUSB30", "Package_SON:USON-10_2.5x1.0mm_P0.5mm", sch,
                {"1": neg, "10": neg, "2": pos, "9": pos, "4": NC, "7": NC, "5": NC, "6": NC, "3": "GND", "8": "GND"},
                fields={"Manufacturer": "Texas Instruments", "MPN": "TPD4EUSB30DQAR",
                        "Description": f"ESD protection, {what} pair, device side of the magnetics, flow-through: 5.5 V "
                                       f"standoff, 0.8 pF, IEC 61000-4-2 level 4 (TI SLVSAC2G; {GUIDE} 4.1.6)"})


W, H = 124.46, 55.88
IN = 25.4
MX, MY = 50.0, 24.0          # U1 centre; turned 270 degrees, its Ethernet pins face the jack on the left edge
ROW_A, ROW_B, ROW_C, ROW_D = 0.05 * IN, 0.15 * IN, 1.75 * IN, 1.85 * IN   # BoosterPack rows from the top edge
BP1_PIN1, BP2_PIN1 = 4.85 * IN, 2.35 * IN   # x of each site's pin 1 (SPMU365C Figure 4-1)
X11_ODD, X11_EVEN = H - 0.15 * IN, H - 0.05 * IN


def u1(n: int):
    """Board position of U1 pad n (TQFP-128, KiCad's pad 1 at the top of the left row), U1 turned 270."""
    if n <= 32:
        fx, fy = -7.6625, -6.2 + 0.4 * (n - 1)
    elif n <= 64:
        fx, fy = -6.2 + 0.4 * (n - 33), 7.6625
    elif n <= 96:
        fx, fy = 7.6625, 6.2 - 0.4 * (n - 65)
    else:
        fx, fy = 6.2 - 0.4 * (n - 97), -7.6625
    return (round(MX - fy, 4), round(MY + fx, 4))


# BoosterPack signals by header pin (SPMU365C Tables 2-1 and 2-2), pin 1 first
BP1_A = ["+3V3", "PE4", "PC4", "PC5", "PC6", "PE5", "PD3", "PC7", "PB2", "PB3"]
BP1_B = ["+5V", "GND", "PE0", "PE1", "PE2", "PE3", "PD7", "PA6", "PM4", "PM5"]
BP1_C = ["PF1", "PF2", "PF3", "PG0", "PL4", "PL5", "PL0", "PL1", "PL2", "PL3"]
BP1_D = ["GND", "PM3", "PH2", "PH3", "RST", "PD1", "PD0", "PN2", "PN3", "PP2"]
BP2_A = ["+3V3", "PD2", "PP0", "PP1", "BP2_A5", "BP2_A6", "PQ0", "PP4", "PN5", "PN4"]
BP2_B = ["+5V", "GND", "PB4", "PB5", "PK0", "PK1", "PK2", "PK3", "PA4", "PA5"]
BP2_C = ["PG1", "PK4", "PK5", "PM0", "PM1", "PM2", "PH0", "PH1", "PK6", "PK7"]
BP2_D = ["GND", "PM7", "PP5", "PA7", "RST", "PQ2", "PQ3", "PP3", "PQ1", "PM6"]
# 98-hole breakout (SPMU365C Tables 2-3 and 2-4), by hole number
X11 = {1: "+3V3", 3: "GND", 5: "PB4", 7: "PB5", 9: "PH0", 11: "PH1", 13: "PH2", 15: "PH3", 17: "PC7", 19: "PC6",
       21: "PC5", 23: "PC4", 25: "PA6", 27: "PA7", 29: "PG1", 31: "PG0", 33: "PM3", 35: "GND", 37: "PM2", 39: "PM1",
       41: "PM0", 43: "PL0", 45: "PL1", 47: "PL2", 49: "PL3", 51: "PQ0", 53: "PQ1", 55: "PQ2", 57: "PQ3", 59: "PK7",
       61: "GND", 63: "PK6", 65: "PL4", 67: "PB2", 69: "PB3", 71: "PP2", 73: "PP3", 75: "PK5", 77: "PK4", 79: "PL5",
       81: "PN4", 83: "PN5", 85: "PN0", 87: "PN1", 89: "PN2", 91: "PN3", 93: "PQ4", 95: "WAKE", 97: "+5V",
       2: "+5V", 4: "GND", 6: "PA2", 8: "PA3", 10: "PA4", 12: "PA5", 14: "PE0", 16: "PE1", 18: "PE2", 20: "PE3",
       22: "PE4", 24: "PE5", 26: "PK0", 28: "PK1", 30: "PK2", 32: "PK3", 34: "VREFA", 36: "GND", 38: "PD5", 40: "PD4",
       42: "PD7", 44: "PD6", 46: "PD3", 48: "PD1", 50: "PD0", 52: "PD2", 54: "PP0", 56: "PP1", 58: "PB0_X", 60: NC,
       62: "GND", 64: "PF4", 66: "PF0", 68: "PF1", 70: "PF2", 72: "PF3", 74: "U0RX", 76: "U0TX", 78: "PP4", 80: "PP5",
       82: "PJ0", 84: "PJ1", 86: "PM7", 88: "PM6", 90: "PM5", 92: "PM4", 94: "RST", 96: "GND", 98: "+3V3"}

# TM4C1294NCPDT TQFP-128 pins (data sheet Table 26-5 and Table 26-3), by number. A GPIO is named after
# itself unless a fixed job gives its net another name.
_GPIO = {
    "PA0": 33, "PA1": 34, "PA2": 35, "PA3": 36, "PA4": 37, "PA5": 38, "PA6": 40, "PA7": 41,
    "PB0": 95, "PB1": 96, "PB2": 91, "PB3": 92, "PB4": 121, "PB5": 120,
    "PC0": 100, "PC1": 99, "PC2": 98, "PC3": 97, "PC4": 25, "PC5": 24, "PC6": 23, "PC7": 22,
    "PD0": 1, "PD1": 2, "PD2": 3, "PD3": 4, "PD4": 125, "PD5": 126, "PD6": 127, "PD7": 128,
    "PE0": 15, "PE1": 14, "PE2": 13, "PE3": 12, "PE4": 123, "PE5": 124,
    "PF0": 42, "PF1": 43, "PF2": 44, "PF3": 45, "PF4": 46, "PG0": 49, "PG1": 50,
    "PH0": 29, "PH1": 30, "PH2": 31, "PH3": 32, "PJ0": 116, "PJ1": 117,
    "PK0": 18, "PK1": 19, "PK2": 20, "PK3": 21, "PK4": 63, "PK5": 62, "PK6": 61, "PK7": 60,
    "PL0": 81, "PL1": 82, "PL2": 83, "PL3": 84, "PL4": 85, "PL5": 86, "PL6": 94, "PL7": 93,
    "PM0": 78, "PM1": 77, "PM2": 76, "PM3": 75, "PM4": 74, "PM5": 73, "PM6": 72, "PM7": 71,
    "PN0": 107, "PN1": 108, "PN2": 109, "PN3": 110, "PN4": 111, "PN5": 112,
    "PP0": 118, "PP1": 119, "PP2": 103, "PP3": 104, "PP4": 105, "PP5": 106,
    "PQ0": 5, "PQ1": 6, "PQ2": 11, "PQ3": 27, "PQ4": 102,
}
_ROLE = {"PA0": "U0RX", "PA1": "U0TX", "PC0": "SWCLK", "PC1": "SWDIO", "PC2": "TDI", "PC3": "SWO",
         "PL6": "TGT_D+", "PL7": "TGT_D-", "PB1": "USB0VBUS"}
_USED = set(BP1_A + BP1_B + BP1_C + BP1_D + BP2_A + BP2_B + BP2_C + BP2_D) | set(X11.values()) | {
    "PA2", "PA3", "PB0", "PB1", "PC0", "PC1", "PC2", "PC3", "PD4", "PD5", "PL6", "PL7", "PA0", "PA1", "PJ0", "PJ1"}
U1_NETS = {str(n): _ROLE.get(name, name if name in _USED else NC) for name, n in _GPIO.items()}
U1_NETS.update({
    **{str(n): "+3V3" for n in (7, 16, 26, 28, 39, 47, 51, 52, 69, 79, 90, 101, 113, 122)},
    **{str(n): "GND" for n in (17, 48, 55, 58, 80, 114)},
    "8": "+3V3", "9": "VREFA", "10": "GND", "87": "VDDC", "115": "VDDC", "68": "VBAT",
    "70": "RST", "88": "OSC0", "89": "OSC1", "66": "XOSC0", "67": "XOSC1", "64": "WAKE", "65": "HIB",
    "53": "ETH_RXN", "54": "ETH_RXP", "56": "ETH_TXN", "57": "ETH_TXP", "59": "RBIAS",
})
assert sorted(map(int, U1_NETS)) == list(range(1, 129))
UNUSED_GPIO = sorted(name for name, n in _GPIO.items() if U1_NETS[str(n)] == NC)

# 0.1 uF at the VDD pins: 26 and 28 (PQ3 between) and 51 and 52 (adjacent) share one each; C4 (pin 39) and
# C6 (pins 51/52, its ground pad also taking GND 55/58) sit on the bottom under the chip, as C46 does for
# pin 90; C8 (pins 79/80) is the bottom row's other capacitor
VDD_CAPS = ("7", "16", "26/28", "39", "47", "51/52", "69", "79/80", "101", "113", "122")
UNDER_CHIP = {"39": "; on the bottom side under the chip, reached through a via inside the pad ring (Table 7)",
              "51/52": "; on the bottom side under the chip, through a via inside the pad ring (Table 7); its ground pad "
                       "also takes GND pins 55 and 58"}

PARTS = [
    # ---- TM4C1294NCPDT ---------------------------------------------------------------------------------
    Part("U1", "EoS_MCU:TM4C1294NCPDT", "TM4C1294NCPDT", "Package_QFP:TQFP-128_14x14mm_P0.4mm", (300, 230), U1_NETS,
         fields={"Manufacturer": "Texas Instruments", "MPN": "TM4C1294NCPDTI3",
                 "Description": f"Tiva C Arm Cortex-M4F MCU, 120 MHz, 1 MB flash, 10/100 Ethernet MAC + PHY, USB 2.0, "
                                f"TQFP-128 ({DS}); unused GPIOs open ({', '.join(UNUSED_GPIO) or 'none'}; Table 26-7: NC acceptable)"}),
    # 0.1 uF at each VDD pin (51 and 52 share one), then bulk, VDDA, VREFA+, VDDC
    *[cap(f"C{k + 1}", "100n", "+3V3", "GND", (360 + 12.7 * (k % 7), 110 + 20 * (k // 7)),
          f"Capacitor 100 nF X7R 16 V 0402, VDD pin {p}, joined to the pin before routing ({GUIDE} 3.4.3{UNDER_CHIP.get(p, '')})",
          mpn=C100N)
      for k, p in enumerate(VDD_CAPS)],
    cap("C12", "100n", "+3V3", "GND", (449, 130), f"Capacitor 100 nF X7R 16 V 0402, VDDA pin 8 ({GUIDE} 3.4.3)", mpn=C100N),
    cap("C14", "10u", "+3V3", "GND", (360, 150), f"Capacitor 10 uF X5R 16 V 0805, VDD/VDDA bulk: 2-22 uF ({GUIDE} 3.4.3)",
        C0805, "GRM21BR61C106KE15L"),
    cap("C15", "1u", "+3V3", "GND", (372.7, 150), f"Capacitor 1 uF X7R 16 V 0603, VDDA pin 8 ({GUIDE} 3.4.4)", C0603, C1U),
    cap("C17", "1u", "VREFA", "GND", (398.1, 150), f"Capacitor 1 uF X7R 16 V 0603, CREF at VREFA+ pin 9 to GNDA ({GUIDE} 3.4.5)",
        C0603, C1U),
    cap("C18", "10n", "VREFA", "GND", (410.8, 150), f"Capacitor 10 nF X7R 50 V 0402, CREF at VREFA+ pin 9 to GNDA ({GUIDE} 3.4.5)",
        mpn=C10N),
    res("R43", "0", "+3V3", "VREFA", (423.5, 150), f"Resistor 0 ohm 0402, VREFA+ to the 3.3 V rail ({GUIDE} 3.4.5); remove it to "
        "feed an external reference on breakout hole 34"),
    cap("C19", "2.2u", "VDDC", "GND", (360, 175), f"Capacitor 2.2 uF X7R 10 V 10% 0603, VDDC, closest to pin 115: on the bottom side "
        f"under the chip beside pin 115's via ({DS} Table 27-15 CLDO 2.5-4.0 uF; {GUIDE} 3.4.2, Table 6)", C0603, C2U2),
    cap("C20", "1u", "VDDC", "GND", (372.7, 175), f"Capacitor 1 uF X7R 16 V 10% 0603, VDDC at pin 115, next after C19 on the bottom side "
        f"({GUIDE} 3.4.2)", C0603, C1U),
    cap("C21", "100n", "VDDC", "GND", (385.4, 175), f"Capacitor 100 nF X7R 16 V 10% 0402, VDDC at pin 115, on the bottom side after C19 "
        f"({GUIDE} 3.4.2)", mpn=C100N),
    cap("C22", "100n", "VDDC", "GND", (398.1, 175), f"Capacitor 100 nF X7R 16 V 10% 0402, VDDC at pin 87, on the bottom side under "
        f"the chip next to pin 87's via ({GUIDE} 3.4.2, Table 6)",
        mpn=C100N),
    cap("C46", "100n", "+3V3", "GND", (449, 150), f"Capacitor 100 nF X7R 16 V 0402, VDD pin 90, on the bottom side under the "
        f"chip ({GUIDE} 3.4.3; Table 7 puts most of the 128-pin package's capacitors on the back)", mpn=C100N),

    # ---- Oscillators ------------------------------------------------------------------------------------
    Part("Y1", "Device:Crystal_GND24", "25MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", (380, 200),
         {"1": "OSC0", "3": "OSC1_X", "2": "GND", "4": "GND"},
         fields={"Manufacturer": "NDK", "MPN": "NX3225GA-25.000M-STD-CRG-2",
                 "Description": f"Crystal 25 MHz, +-20 ppm, +-30 ppm over temperature, CL 8 pF, ESR 50 ohm max, 3.2 x 2.5 mm; "
                                f"simulated by TI ({DS} Table 27-24); the PHY needs 25 MHz +-50 ppm (Table 27-50)"}),
    res("R1", "2.0k", "OSC1", "OSC1_X", (400, 190), f"Resistor 2.0 kohm 1% 0402, Rs between OSC1 and Y1 ({DS} Table 27-24 for "
        "NX3225GA-25.000MHZ-STD-CRG-2)"),
    cap("C23", "12p", "OSC0", "GND", (365, 215), f"Capacitor 12 pF C0G 50 V 5% 0402, OSC0 load ({DS} Table 27-24)",
        mpn="GRM1555C1H120JA01D"),
    cap("C24", "12p", "OSC1_X", "GND", (395, 215), f"Capacitor 12 pF C0G 50 V 5% 0402, OSC1 load ({DS} Table 27-24)",
        mpn="GRM1555C1H120JA01D"),
    Part("Y2", "Device:Crystal_Small", "32.768kHz", "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm", (380, 240),
         {"1": "XOSC0", "2": "XOSC1"},
         fields={"Manufacturer": "Abracon", "MPN": "ABS07-32.768KHZ-T",
                 "Description": "Crystal 32.768 kHz, CL 12.5 pF, ESR 70 kohm max, C0 2.0 pF max, 3.2 x 1.5 mm (Abracon ABS07); "
                                f"firmware sets OSCDRV ({DS} Table 27-22)"}),
    cap("C25", "20p", "XOSC0", "GND", (365, 255), f"Capacitor 20 pF C0G 50 V 5% 0402, XOSC0 load: > 18 pF so OSCDRV = 1, "
        f"ESR to 75 kohm; CL 12.2-13.0 pF ({DS} Table 27-22; errata ELEC#04)", mpn="GCM1555C1H200JA16D"),
    cap("C26", "20p", "XOSC1", "GND", (395, 255), f"Capacitor 20 pF C0G 50 V 5% 0402, XOSC1 load ({DS} Table 27-22)",
        mpn="GCM1555C1H200JA16D"),

    # ---- Reset, hibernation --------------------------------------------------------------------------------
    res("R2", "10k", "RST", "+3V3", (420, 190), f"Resistor 10 kohm 1% 0402, RST pull-up ({DS} Figure 5-3)"),
    cap("C27", "10n", "RST", "GND", (432.7, 190), f"Capacitor 10 nF X7R 50 V 0402, RST, at the pin, on the bottom side under the "
        f"chip ({DS} Figure 5-3; {GUIDE} 3.5.1)",
        mpn=C10N),
    res("R3", "470", "RST", "RST_SW", (445.4, 190), f"Resistor 470 ohm 1% 0402, in series with the reset button ({DS} Figure 5-3; "
        f"{GUIDE} 3.5.1)"),
    button("SW3", "RESET", "RST_SW", (460, 195), "Tactile switch, reset (RST through 470 ohm)"),
    Part("D5", "Diode:BAT54J", "BAT54J", "Diode_SMD:D_SOD-323F", (420, 230), {"A": "+3V3", "K": "VBAT_IN"},
         fields={"Manufacturer": "Nexperia", "MPN": "BAT54J",
                 "Description": "Schottky 30 V, VF <= 240 mV at 0.1 mA (Nexperia BAT54J): VBAT from 3.3 V, a diode drop below VDD"}),
    res("R4", "51", "VBAT_IN", "VBAT", (435, 230), f"Resistor 51 ohm 5% 0402, RBAT ({DS} Figure 7-2 and 7.3.2 note; {GUIDE} Figure 19)"),
    cap("C28", "100n", "VBAT", "GND", (447.7, 230), f"Capacitor 100 nF X7R 16 V 0402, CBAT at VBAT pin 68: 5.1 us with RBAT, "
        f"under 0.7 V/us ({DS} Figure 7-2, Table 27-29; errata ELEC#02)", mpn=C100N),
    res("R5", "200k", "WAKE", "VBAT_IN", (420, 260), f"Resistor 200 kohm 1% 0402, WAKE pull-up to VBAT's supply ({DS} Figure 7-2; "
        f"{GUIDE} 4.15)"),
    res("R6", "470", "WAKE", "WAKE_SW", (432.7, 270), f"Resistor 470 ohm 1% 0402, in series with the WAKE button, at the pin "
        f"({GUIDE} 3.5.1, the value of {DS} Figure 5-3's RS)"),
    button("SW4", "WAKE", "WAKE_SW", (445, 265), f"Tactile switch, WAKE to ground through R6: wakes from hibernation ({GUIDE} 4.15)"),

    # ---- Ethernet --------------------------------------------------------------------------------------
    Part("J8", "Connector:RJ45_Wuerth_7499010121A", "7499010121A", "Connector_RJ:RJ45_Wuerth_7499010121A_Horizontal", (40, 290),
         {"1": "ETH_TXP", "2": "ETH_VTERM", "3": "ETH_TXN", "4": "ETH_RXP", "5": "ETH_VTERM", "6": "ETH_RXN", "7": NC,
          "8": "CHASSIS", "9": "GND", "10": "ETH_LEDG", "11": "GND", "12": "ETH_LEDY", "SH": "CHASSIS"},
         fields={"Manufacturer": "Wurth Elektronik", "MPN": "7499010121A",
                 "Description": "RJ45 with magnetics (WE-RJ45LAN 10/100BASE-TX, tab up, 1:1 with centre taps, Bob Smith "
                                "termination to pin 8, green LED 10-9 and yellow LED 12-11; data sheet version 003.001)"}),
    *[res(f"R{7 + k}", "49.9", net, "ETH_VTERM", (80 + 12.7 * k, 250), f"Resistor 49.9 ohm 1% 0402, {name} termination to the "
          f"switched 3.3 V (ETH_VTERM) near the chip, one end on the line ({GUIDE} 4.1.1; {DS} Figure 20-13, 7.3.9)")
      for k, (net, name) in enumerate((("ETH_RXN", "EN0RXIN"), ("ETH_RXP", "EN0RXIP"), ("ETH_TXN", "EN0TXON"),
                                       ("ETH_TXP", "EN0TXOP")))],
    # The termination's supply is switched off in hibernation: data sheet 7.3.9 and the note under Figure 20-13
    # ("When entering hibernation in VDD3ON mode, the supply rails to the Ethernet resistors ... must be switched
    # off"). HIB is asserted (low) in hibernation whatever VDD3ON is (HIBCTL VDD3ON bit description), and the
    # board's VDD stays on, so HIB drives the load switch, not the regulator.
    Part("U9", "Power_Management:TPS22917DBV", "TPS22917", "Package_TO_SOT_SMD:SOT-23-6", (130, 300),
         {"VIN": "+3V3", "GND": "GND", "ON": "HIB", "CT": NC, "QOD": "ETH_QOD", "VOUT": "ETH_VTERM"},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPS22917DBVR",
                 "Description": "Load switch 2 A, 80 mohm, active-high ON (TI SLVSDW8B): ETH_VTERM, the Ethernet termination "
                                f"and centre-tap supply, off while HIB is asserted ({DS} 7.3.9, Figure 20-13 note); CT open "
                                "(SLVSDW8B Table 6-1)"}),
    res("R49", "100", "ETH_VTERM", "ETH_QOD", (130, 320), "Resistor 100 ohm 1% 0402, RQOD from the TPS22917's output to QOD: with "
        "the internal 150 ohm, ETH_VTERM (2.2 uF) falls with a 0.55 ms time constant: 90-10 % in about 1.2 ms, under 0.1 V "
        "in about 1.9 ms after HIB goes low (TI SLVSDW8B Table 6-1, "
        "9.3.3 Equations 3 and 4; section 7.6 lists RQOD = 100 ohm; the output may not discharge completely without QOD)"),
    cap("C45", "1u", "+3V3", "GND", (115, 300), "Capacitor 1 uF X7R 16 V 0603, TPS22917 input (TI SLVSDW8B section 11: CIN 1 uF)",
        C0603, C1U),
    cap("C43", "100n", "ETH_VTERM", "GND", (145, 290), f"Capacitor 100 nF X7R 16 V 0402, receive-pair termination supply ({DS} "
        "Figure 20-13: 0.1 uF at each pair's resistors)", mpn=C100N),
    cap("C44", "100n", "ETH_VTERM", "GND", (145, 310), f"Capacitor 100 nF X7R 16 V 0402, transmit-pair termination supply ({DS} "
        "Figure 20-13)", mpn=C100N),
    res("R11", "4.87k", "RBIAS", "GND", (130, 270), f"Resistor 4.87 kohm 1% 0402, RBIAS within 6 mm of pin 59, own ground via "
        f"({GUIDE} 4.1.4; {DS} Table 27-49: 4.82-4.92 kohm)"),
    eth_esd("U6", "ETH_RXN", "ETH_RXP", (60, 260), "receive (EN0RXIN/EN0RXIP)"),
    eth_esd("U7", "ETH_TXN", "ETH_TXP", (60, 300), "transmit (EN0TXON/EN0TXOP)"),
    cap("C29", "1u", "ETH_VTERM", "GND", (20, 250), f"Capacitor 1 uF X7R 16 V 0603, transmit centre tap J8.2, on the bottom side beside "
        f"the pin: 1 uF because the switched supply reaches it by a track, not a plane ({GUIDE} 4.1.2; {DS} Figure 20-13 "
        "note)", C0603, C1U),
    cap("C30", "1u", "ETH_VTERM", "GND", (20, 270), f"Capacitor 1 uF X7R 16 V 0603, receive centre tap J8.5, on the bottom side beside "
        f"the pin ({GUIDE} 4.1.2; {DS} Figure 20-13 note)", C0603, C1U),
    res("R12", "1M", "CHASSIS", "GND", (20, 310), f"Resistor 1 Mohm 5% 1206, jack shield to ground ({DS} Figure 20-13)", R1206),
    cap("C31", "4.7n", "CHASSIS", "GND", (32, 310), f"Capacitor 4.7 nF 2 kV X7R 1812, jack shield to ground ({DS} Figure 20-13: "
        "4700 pF 2000 V)", C1812, "C1812C472KGRACTU", "KEMET"),
    res("R13", "470", "PF0", "ETH_LEDG", (100, 310), "Resistor 470 ohm 1% 0402, jack green LED from PF0 (EN0LED0): (3.3 - 1.8) / 470 "
        f"= 3.2 mA ({GUIDE} 4.1.7; Wurth 7499010121A VF 1.8-2.4 V)"),
    res("R14", "470", "PF4", "ETH_LEDY", (112.7, 310), "Resistor 470 ohm 1% 0402, jack yellow LED from PF4 (EN0LED1) "
        f"({GUIDE} 4.1.7)"),

    # ---- USB device port (USB0) ----------------------------------------------------------------------------
    usb_c("J7", "TGT", "VBUS_TGT", (40, 190), "USB-C 2.0 receptacle, 16 pins: the TM4C1294's own USB device port"),
    esd("U3", "TGT", "VBUS_TGT", (95, 190)),   # turned 180 degrees: pad 3 (D-) faces contact A7 and pad 2 (D+) faces A6
    res("R15", "5.1k", "TGT_CC1", "GND", (75, 165), f"Resistor 5.1 kohm 1% 0402, USB-C sink Rd on CC1 ({RD})"),
    res("R16", "5.1k", "TGT_CC2", "GND", (87.7, 165), f"Resistor 5.1 kohm 1% 0402, USB-C sink Rd on CC2 ({RD})"),
    fuse("F2", "VBUS_TGT", "VTGT", (120, 175), "device port"),
    res("R17", "100", "VTGT", "USB0VBUS", (140, 190), f"Resistor 100 ohm 1% 0402, VBUS to PB1/USB0VBUS against ESD ({GUIDE} 4.3.1)"),
    res("R18", "10k", "VTGT", "GND", (152.7, 205), "Resistor 10 kohm 1% 0402, device-port VBUS bleed: with the 1 uF on the mux's VIN1 "
        "(C37), VBUS falls in about 10 ms after an unplug, so PB1 sees the host leave"),

    # ---- Debug USB port: CP2102N on UART0 ---------------------------------------------------------------
    usb_c("J6", "DBG", "VBUS_DBG", (40, 90), "USB-C 2.0 receptacle, 16 pins: the CP2102N serial port and the board's first 5 V source"),
    esd("U2", "DBG", "VBUS_DBG", (95, 90)),
    res("R19", "5.1k", "DBG_CC1", "GND", (75, 65), f"Resistor 5.1 kohm 1% 0402, USB-C sink Rd on CC1 ({RD})"),
    res("R20", "5.1k", "DBG_CC2", "GND", (87.7, 65), f"Resistor 5.1 kohm 1% 0402, USB-C sink Rd on CC2 ({RD})"),
    fuse("F1", "VBUS_DBG", "VDBG", (120, 75), "debug port"),
    Part("U5", "Interface_USB:CP2102N-Axx-xQFN20", "CP2102N-A02-GQFN20",
         "Package_DFN_QFN:SiliconLabs_QFN-20-1EP_3x3mm_P0.5mm_EP1.8x1.8mm", (170, 100),
         {"VREGIN": "+3V3", "VDD": "+3V3", "GND": "GND", "D+": "DBG_D+", "D-": "DBG_D-", "VBUS": "BR_VBUS",
          "~{RST}": "BR_RST", "TXD": "BR_TXD", "RXD": "BR_RXD",
          **{p: NC for p in ("RS485/GPIO.1", "CLK/GPIO.0", "NC", "~{SUSPEND}", "~{WAKEUP}", "SUSPEND", "~{CTS}",
                             "~{RTS}", "~{RXT}/GPIO.3", "~{TXT}/GPIO.2")}},
         fields={"Manufacturer": "Silicon Labs", "MPN": "CP2102N-A02-GQFN20R",
                 "Description": f"USB-UART bridge on UART0, on the board's 3.3 V, its regulator unused ({CP2102N} Figure 2.3)"}),
    cap("C32", "4.7u", "+3V3", "GND", (215, 70), f"Capacitor 4.7 uF X5R 16 V 0603, CP2102N VREGIN ({CP2102N} Figure 2.3)", C0603, C4U7),
    cap("C33", "100n", "+3V3", "GND", (227.7, 70), f"Capacitor 100 nF X7R 16 V 0402, CP2102N VREGIN, at the pin ({CP2102N} Figure 2.3)",
        mpn=C100N),
    cap("C34", "4.7u", "+3V3", "GND", (240.4, 70), f"Capacitor 4.7 uF X5R 16 V 0603, CP2102N VDD ({CP2102N} Figure 2.3)", C0603, C4U7),
    cap("C35", "100n", "+3V3", "GND", (253.1, 70), f"Capacitor 100 nF X7R 16 V 0402, CP2102N VDD, at the pin ({CP2102N} Figure 2.3)",
        mpn=C100N),
    res("R21", "22.1k", "VDBG", "BR_VBUS", (215, 125), f"Resistor 22.1 kohm 1% 0402, CP2102N VBUS divider ({CP2102N} Figure 2.6)"),
    res("R22", "47.5k", "BR_VBUS", "GND", (227.7, 140), f"Resistor 47.5 kohm 1% 0402, CP2102N VBUS divider: 3.41 V from 5 V "
        f"({CP2102N} Figure 2.6, Table 3.7)"),
    res("R23", "5.1k", "VDBG", "GND", (240.4, 140), "Resistor 5.1 kohm 1% 0402, VBUS bleed: with the divider 4.75 kohm, so up to "
        f"185 uA into VDBG keeps the CP2102N VBUS pin under VIL 0.6 V ({CP2102N} Table 3.7); 1.0 mA from a host"),
    res("R24", "1k", "BR_RST", "+3V3", (240.4, 125), f"Resistor 1 kohm 1% 0402, CP2102N RSTb pull-up to VDD ({CP2102N} 2.1)"),
    res("R25", "1k", "BR_TXD", "XB_RX", (253.1, 125), "Resistor 1 kohm 1% 0402, CP2102N TXD toward U0Rx: caps a driver fight at 3.3 mA"),
    res("R26", "1k", "XB_TX", "BR_RXD", (265.8, 125), "Resistor 1 kohm 1% 0402, U0Tx toward CP2102N RXD: caps a driver fight at 3.3 mA"),
    Part("JP1", "Connector_Generic:Conn_02x02_Odd_Even", "UART/CAN RX", HDR + "2x02_P2.54mm_Vertical", (280, 150),
         {"1": "XB_RX", "2": "U0RX", "3": "PD4", "4": "BP2_A5"},
         fields={"Manufacturer": "Samtec", "MPN": "TSW-102-07-G-D",
                 "Description": "Jumpers, fit two Samtec SNT-100-BK-G 2.54 mm shunts: 1-2 and 3-4 (UART) bridge TXD to "
                                "PA0/U0Rx and PD4 to BP2 A.5; 1-3 and "
                                "2-4 (CAN) bridge TXD to PD4/U2Rx and PA0/CAN0Rx to BP2 A.5 (SPMU365C 2.1.6.2)"}),
    Part("JP2", "Connector_Generic:Conn_02x02_Odd_Even", "UART/CAN TX", HDR + "2x02_P2.54mm_Vertical", (305, 150),
         {"1": "XB_TX", "2": "U0TX", "3": "PD5", "4": "BP2_A6"},
         fields={"Manufacturer": "Samtec", "MPN": "TSW-102-07-G-D",
                 "Description": "Jumpers, fit two Samtec SNT-100-BK-G 2.54 mm shunts: 1-2 and 3-4 (UART) bridge PA1/U0Tx to "
                                "RXD and PD5 to BP2 A.6; 1-3 and "
                                "2-4 (CAN) bridge PD5/U2Tx to RXD and PA1/CAN0Tx to BP2 A.6"}),

    # ---- 5 V selection, 3.3 V -------------------------------------------------------------------------------
    Part("U4", "Power_Management:TPS2116DRL", "TPS2116", "Package_TO_SOT_SMD:SOT-583-8", (200, 160),
         {"VIN1": "VTGT", "VIN2": "VDBG", "VOUT": "+5V", "GND": "GND", "PR1": "MUX_PR1", "MODE": "VTGT", "ST": NC},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPS2116DRLR",
                 "Description": f"Power mux 2.5 A, priority mode: VIN1 (device port) first, VIN2 (debug port) otherwise, reverse "
                                f"current blocking ({MUX} 7.3.4, 7.6.1)"}),
    res("R27", "27k", "VTGT", "MUX_PR1", (175, 185), f"Resistor 27 kohm 1% 0402, TPS2116 PR1 divider: VIN1 kept down to 3.7 x VREF "
        f"= 3.40-4.00 V ({MUX} 7.6.1.1)"),
    res("R28", "10k", "MUX_PR1", "GND", (175, 200), f"Resistor 10 kohm 1% 0402, TPS2116 PR1 divider (VREF 0.92-1.08 V, {MUX} Table 6.5)"),
    cap("C36", "1u", "VDBG", "GND", (180, 140), f"Capacitor 1 uF X7R 16 V 0603, TPS2116 VIN2, on its pin's side ({MUX} section 9)",
        C0603, C1U),
    cap("C37", "1u", "VTGT", "GND", (192.7, 140), f"Capacitor 1 uF X7R 16 V 0603, TPS2116 VIN1, on its pin's side ({MUX} section 9)",
        C0603, C1U),
    cap("C38", "22u", "+5V", "GND", (215, 160), f"Capacitor 22 uF X7R 10 V 1206, TPS2116 VOUT, 5 V rail ({MUX} 7.3.2, 7.3.4)", C1206, C22U),
    cap("C39", "22u", "+5V", "GND", (227.7, 160), f"Capacitor 22 uF X7R 10 V 1206, 5 V rail ({MUX} 7.3.4)", C1206, C22U),
    Part("U8", "Regulator_Switching:TLV62569DBV", "TLV62569", "Package_TO_SOT_SMD:SOT-23-5", (250, 200),
         {"VIN": "+5V", "EN": "+5V", "GND": "GND", "SW": "BUCK_SW", "FB": "BUCK_FB"},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TLV62569DBVR",
                 "Description": f"Buck converter 2 A, 1.5 MHz, 2.5-5.5 V in, 3.3 V out ({BUCK})"}),
    Part("L1", "Device:L_Small", "2.2uH", "Inductor_SMD:L_Coilcraft_XAL4020-XXX", (270, 195), {"1": "BUCK_SW", "2": "+3V3"},
         fields={"Manufacturer": "Coilcraft", "MPN": "XAL4020-222MEC",
                 "Description": f"Inductor 2.2 uH 20%, 38.7 mohm max, Isat 5.6 A, 4 x 4 mm ({BUCK} Tables 3 and 4; Coilcraft "
                                "document 806-1)"}),
    cap("C40", "4.7u", "+5V", "GND", (240, 225), f"Capacitor 4.7 uF X7R 10 V 0805, buck input, at VIN ({BUCK} Table 3, 8.2.2.5)",
        C0805, C4U7_BUCK),
    cap("C41", "10u", "+3V3", "GND", (285, 225), f"Capacitor 10 uF X7R 10 V 0805, buck output ({BUCK} Tables 3 and 4: 2.2 uH with "
        "10 uF)", C0805, C10U_BUCK),
    res("R29", "453k", "+3V3", "BUCK_FB", (260, 225), f"Resistor 453 kohm 1% 0402, feedback upper: 0.6 x (1 + 453/100) = 3.318 V "
        f"({BUCK} Equation 2)"),
    res("R30", "100k", "BUCK_FB", "GND", (272.7, 240), f"Resistor 100 kohm 1% 0402, feedback lower ({BUCK} 8.2.2.2: <= 200 kohm)"),
    cap("C42", "6.8p", "+3V3", "BUCK_FB", (260, 240), f"Capacitor 6.8 pF C0G 50 V 0402, feed-forward across R29 ({BUCK} 8.2.2.2)",
        mpn="GRM1555C1H6R8CA01D"),
    res("R31", "680", "+3V3", "LED_PWR_A", (300, 200), "Resistor 680 ohm 1% 0402, power LED: (3.3 - 1.9) / 680 = 2.1 mA "
        "(Kingbright DSAO7432)"),
    led("D6", "PWR", "LED_PWR_A", (315, 200), "LED green 0603, 3.3 V present (VF 1.9 V typ at 2 mA, DSAO7432)"),

    # ---- Debug header -------------------------------------------------------------------------------------
    Part("J9", "Connector:Conn_ARM_JTAG_SWD_10", "Cortex Debug", "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD",
         (440, 395), {"VTref": "+3V3", "SWDIO/TMS": "SWDIO", "GND": "GND", "SWCLK/TCK": "SWCLK", "SWO/TDO": "SWO",
                      "KEY": NC, "NC/TDI": "TDI", "GNDDetect": "GND", "~{RESET}": "RST"},
         fields={"Manufacturer": "Samtec", "MPN": "FTSH-105-01-L-DV-K",
                 "Description": f"Arm Cortex Debug 10-pin, 1.27 mm, keyed (pin 7 KEY), SWD/JTAG on PC0-PC3 and RST ({GUIDE} Table 9)"}),

    # ---- User I/O ---------------------------------------------------------------------------------------------
    *[x for k, (pin, net) in enumerate((("PN1", "PN1"), ("PN0", "PN0"), ("PF4", "PF4"), ("PF0", "PF0")))
      for x in (res(f"R{32 + k}", "680", net, f"LED{k + 1}_A", (40 + 25 * k, 330),
                    f"Resistor 680 ohm 1% 0402, user LED on {pin}: (3.3 - 1.9) / 680 = 2.1 mA (Kingbright DSAO7432)"),
                led(f"D{k + 1}", pin, f"LED{k + 1}_A", (52 + 25 * k, 330), f"LED green 0603, user LED on {pin}"))],
    res("R36", "1k", "PJ0", "SW1_A", (40, 360), "Resistor 1 kohm 1% 0402, PJ0 button: limits a driver on breakout hole 82 to 3.3 mA"),
    button("SW1", "PJ0", "SW1_A", (60, 365), "Tactile switch, user button on PJ0"),
    res("R37", "1k", "PJ1", "SW2_A", (85, 360), "Resistor 1 kohm 1% 0402, PJ1 button: limits a driver on breakout hole 84 to 3.3 mA"),
    button("SW2", "PJ1", "SW2_A", (105, 365), "Tactile switch, user button on PJ1"),
    *[res(f"R{38 + k}", "2.2k", net, "+3V3", (130 + 12.7 * k, 360), f"Resistor 2.2 kohm 1% 0402, I2C pull-up on {net} ({GUIDE} 4.7: "
          "typical 2.2 kohm)") for k, net in enumerate(("PB2", "PB3"))],
    res("R40", "0", "PQ2", "PA3", (180, 360), "Resistor 0 ohm 0402, joins PA3 (I2C8SDA) to PQ2 (SSI3XDAT0) on BP2 D.6 (SPMU365C "
        "2.1.6.2); remove to separate"),
    res("R41", "0", "PQ3", "PA2", (192.7, 360), "Resistor 0 ohm 0402, joins PA2 (I2C8SCL) to PQ3 (SSI3XDAT1) on BP2 D.7 (SPMU365C "
        "2.1.6.2); remove to separate"),
    res("R42", "1k", "PB0", "PB0_X", (205.4, 360), "Resistor 1 kohm 1% 0402, PB0 to breakout hole 58: slows edges under 2 ns "
        "(errata GPIO#09)"),
    *[res(f"R{44 + k}", "2.2k", net, "+3V3", (218.1 + 12.7 * k, 360), f"Resistor 2.2 kohm 1% 0402, I2C pull-up on {net} ({GUIDE} 4.7)")
      for k, net in enumerate(("PN5", "PN4"))],
    *[res(f"R{46 + k}", "10k", net, "+3V3", (243.5 + 12.7 * k, 360), f"Resistor 10 kohm 1% 0402, {net} pull-up: a BoosterPack's "
          f"SPI chip select stays off before firmware ({GUIDE} 4.5)") for k, net in enumerate(("PH2", "PP5", "PQ1"))],

    # ---- BoosterPack headers and breakout -------------------------------------------------------------------------
    header("J1", "BoosterPack 1 A/B", BP1_A, BP1_B, (420, 300), "BoosterPack 1 rows A (odd pins, outer) and B (even pins, inner)"),
    header("J2", "BoosterPack 1 C/D", BP1_C, BP1_D, (475, 300), "BoosterPack 1 rows C (odd pins, inner) and D (even pins, outer)"),
    header("J3", "BoosterPack 2 A/B", BP2_A, BP2_B, (420, 345), "BoosterPack 2 rows A (odd pins, outer) and B (even pins, inner)"),
    header("J4", "BoosterPack 2 C/D", BP2_C, BP2_D, (475, 345), "BoosterPack 2 rows C (odd pins, inner) and D (even pins, outer)"),
    Part("J5", "EoS_Connectors:Conn_02x49_Odd_Even", "Breakout 2x49", "EoS_Packages:PinHeader_2x49_P2.54mm_Vertical", (565, 230),
         {str(n): X11.get(n, NC) for n in range(1, 99)}, dnp=True,
         fields={"Description": "98-hole breakout, 2 x 49 on 2.54 mm, pads only: fit right-angle rows (Samtec TSW-149-09-L-S-RE "
                                "and TSW-149-08-L-S-RA, SPMU365C 2.1.6.3) to plug the board into a breadboard"}),
]
for i, (x, y) in enumerate(((3.25 * IN, 0.15 * IN), (0.85 * IN, 1.55 * IN), (3.75 * IN, 1.35 * IN))):
    PARTS.append(Part(f"H{i + 1}", "Mechanical:MountingHole", "M3 clearance", "MountingHole:MountingHole_3.2mm_M3",
                      (250 + 15 * i, 395), {}, fields={"Description": "Non-plated M3 clearance hole, 3.2 mm; centre from SPMU365C "
                                                                    "Figure 4-1 (0.125 in hole, enlarged 0.025 mm for M3)"}))
HOLES = {"H1": (3.25 * IN, 0.15 * IN), "H2": (0.85 * IN, 1.55 * IN), "H3": (3.75 * IN, 1.35 * IN)}

# Board placement: (x, y, rotation) in mm, origin top-left. The headers and holes sit where SPMU365C
# Figure 4-1 puts them. U1 is turned 270 degrees: pins 1-32 run right to left along its top, 33-64
# down its left (the Ethernet pins 53-57 face the jack), 65-96 left to right along its bottom (the
# oscillators and USB), 97-128 up its right (JTAG at the bottom). The jack is on the left edge, its
# face 1 mm proud. The device USB-C stands on the top edge above the jack, left of BoosterPack 2, so its
# pair reaches the chip's top-left corner without crossing any of the chip's escapes; the debug USB-C,
# the CP2102N, the UART/CAN jumpers, the 5 V mux and the 3.3 V buck fill the top half of the gap between
# the sites (BP2 reaches x = 2.70 in, BP1 starts at 3.80 in), the JTAG header sits beside the chip's
# JTAG pins, and the lower half of the gap stays open for the lines to BoosterPack 1 and the breakout.
# User LEDs and buttons sit with the reset and WAKE buttons by the left edge, below the jack. Every USB-C
# is USB_C_EDGE from its edge.
JX, JY = 18.69, 28.5          # J8 pin 1 (turned 180: pins 1, 3, 5, 7 at x = JX; 2, 4, 6, 8 at JX - 2.54)
TGT_X, DBG_X = 29.5, 91.4     # device (above the jack) and debug (right of H1) USB-C centres on the top edge
PLACEMENT = {
    "U1": (MX, MY, 270),
    "J1": (BP1_PIN1, ROW_A, 270), "J2": (BP1_PIN1, ROW_C, 270),
    "J3": (BP2_PIN1, ROW_A, 270), "J4": (BP2_PIN1, ROW_C, 270),
    "J5": (BP1_PIN1, X11_ODD, 270),
    **{ref: (x, y, 0) for ref, (x, y) in HOLES.items()},
    # decoupling, each capacitor outside its pin(s): top row (pins 7-28)
    "C1": (54.5, 14.0, 90), "C12": (55.5, 14.0, 90), "C15": (55.0, 11.5, 90),
    "C18": (52.8, 14.4, 180), "C17": (52.5, 12.3, 180),
    "C2": (50.0, 14.4, 180), "C3": (45.8, 14.0, 90),
    # left row (pins 39-52); C4 (pin 39) and C6 (pins 51/52, with GND 55/58) on the bottom under the chip
    "C4": (46.2, 23.2, 0), "C5": (40.5, 23.6, 270), "C6": (46.6, 26.0, 270),
    # bottom row (pins 69-90): VDD69, VDD79/GND80 on top; RST's capacitor (pin 70), VDDC87's and pin 90's on the
    # bottom under the chip, so the PM pins (71-78) get out between C7 and C8 and the PL pins (81-86) between C8
    # and OSC0's line
    "C7": (46.3, 34.0, 270), "C27": (46.4, 28.4, 0), "C8": (49.6, 33.6, 0), "C22": (53.0, 27.6, 0),
    "C46": (51.0, 28.6, 0),
    # right row (pins 101-122): VDD101, VDD113/GND114 with VDDC115's three, VDD122
    "C9": (59.6, 28.6, 0), "C10": (59.6, 23.6, 90), "C19": (54.7, 23.0, 0), "C20": (54.7, 24.7, 0),
    # C21 sits up and right of C19, so C19's ground pad has room for its own via straight above it
    "C21": (55.2, 21.3, 0), "C11": (59.6, 20.2, 0),
    "C14": (38.6, 10.6, 0),
    # 32.768 kHz crystal down-left of pins 66/67, its load capacitors beside its pads
    "Y2": (41.3, 35.6, 90), "C25": (39.1, 34.35, 180), "C26": (39.1, 36.85, 180),
    # 25 MHz crystal below pins 88/89: OSC0 down between the pads into pad 1, OSC1 through Rs into pad 3
    "Y1": (53.0, 37.6, 0), "R1": (54.3, 34.8, 270), "C23": (49.95, 38.45, 180), "C24": (56.05, 36.75, 0),
    # VBAT below its pin (68): CBAT, then RBAT, then the diode; RST's pull-up and series resistor beside
    # them; reset and WAKE buttons near the left edge
    "C28": (46.0, 36.0, 0), "R4": (45.52, 37.9, 90), "D5": (45.5, 40.5, 270),
    "R2": (48.0, 36.3, 0), "R3": (48.0, 37.5, 0),
    "R5": (36.6, 31.2, 90), "R6": (38.6, 31.6, 0),
    "SW3": (31.4, 47.0, 0), "SW4": (25.6, 47.0, 0),
    # Ethernet, all on the top layer: the receive pair leaves pins 53/54 under C6 and climbs to the level
    # of U6's pads (22.5/23.0); the transmit pair runs straight from pins 56/57 to U7's (27.0/27.5).
    # Each termination resistor stands across its line with its line end 0.15 mm outside the pair and
    # its supply end away from the pair: R7 above the receive pair, R10 below the transmit pair, and
    # R8 and R9 in the gap the climb opens between the pairs (SPMA056 4.1.8: the pairs at least
    # 1.27 mm apart). RBIAS beside pin 59, ESD parts by the jack, each centre tap's capacitor on the bottom
    # side beside its own pin (J8.2 left of it, J8.5 right of it).
    "R7": (35.3, 21.84, 90), "R8": (35.3, 23.72, 270), "R9": (36.8, 26.34, 90), "R10": (36.8, 28.21, 270),
    "R11": (39.6, 28.6, 180),
    "U6": (28.0, 23.5, 0), "U7": (28.0, 28.0, 0),
    "J8": (JX, JY, 180), "C29": (13.8, 27.23, 0), "C30": (20.9, 23.42, 180),
    # the termination supply's load switch below the transmit lines, its output (pin 6) under C44 and towards
    # R10's supply end, its ON pin (3) at the bottom, where HIB arrives along the board below R5 and R6; C43
    # beside R7's supply end
    "U9": (32.8, 30.4, 0), "C45": (29.75, 30.4, 270), "C44": (34.2, 24.6, 270), "C43": (35.3, 19.95, 90),
    "R49": (35.4, 30.2, 270),
    "R12": (4.5, 35.8, 90), "C31": (9.5, 35.4, 0), "R13": (27.4, 30.6, 0), "R14": (27.4, 19.2, 0),
    # device USB-C (USB0): ESD part just below the connector (SPMA056 4.3: "as close as possible to the USB
    # connector"), the pair then running down to the chip's top-left corner; CC resistors, fuse and VBUS bleed; PB0's 1 kohm and PB1's 100 ohm below pins 95 and 96, in that order, so their
    # lines leave the chip side by side
    "J7": (TGT_X, USB_C_EDGE, 180), "U3": (TGT_X, 10.25, 180), "R15": (TGT_X + 3.0, 10.2, 270),
    "R16": (TGT_X - 3.0, 11.0, 90), "F2": (22.0, 6.0, 270), "R18": (22.0, 10.0, 90),
    "R42": (57.8, 35.0, 270), "R17": (59.0, 35.0, 90),
    # debug USB-C and CP2102N (EoS TM4C123 Board's arrangement: the bridge below-left of the ESD part, its
    # D+/D- pins 4/5 facing the pair)
    "J6": (DBG_X, USB_C_EDGE, 180), "U2": (DBG_X, 10.4, 180), "R19": (DBG_X + 3.0, 10.2, 270),
    "R20": (DBG_X - 2.7, 11.6, 90), "F1": (86.4, 13.4, 270),
    "U5": (DBG_X - 1.5, 20.6, 0), "R21": (DBG_X - 5.3, 19.6, 90), "R22": (DBG_X - 5.3, 21.7, 90),
    "R24": (DBG_X - 0.9, 23.8, 270), "R23": (DBG_X - 6.6, 18.4, 90), "R25": (DBG_X + 2.4, 19.7, 90),
    "R26": (DBG_X + 2.4, 21.8, 90), "C35": (DBG_X - 2.4, 24.7, 0), "C34": (DBG_X - 2.4, 26.3, 0),
    "C33": (DBG_X + 0.9, 24.7, 0), "C32": (DBG_X + 1.0, 26.3, 0),
    # 5 V priority mux below H1 (VIN1, the device port's VTGT, on its left; VIN2, the debug port, on its
    # right), the 3.3 V buck below it: input capacitor at VIN (pin 4), the inductor below SW (pin 3), the
    # output capacitor beside the inductor's 3.3 V end, the feedback parts at FB (pin 5)
    "U4": (78.0, 11.0, 0), "C37": (75.7, 11.3, 90), "C36": (80.3, 11.3, 90), "C38": (78.0, 14.2, 0),
    "R27": (73.4, 10.6, 90), "R28": (73.4, 12.7, 90),
    "U8": (78.0, 19.0, 0), "L1": (77.5, 23.2, 270), "C40": (81.1, 20.4, 270), "C41": (81.5, 24.0, 90),
    "R29": (82.0, 15.0, 180), "R30": (82.0, 16.1, 0), "C42": (82.0, 13.9, 180), "C39": (78.8, 27.4, 0),
    "R31": (82.5, 28.0, 0), "D6": (85.0, 28.0, 180),
    # UART/CAN jumpers next to BoosterPack 2's A row, the JTAG header beside the chip's JTAG pins
    "JP1": (63.3, 2.3, 0), "JP2": (69.5, 2.3, 0),
    "J9": (72.0, 31.0, 0),
    # user LEDs (each turned so its anode faces its resistor) and buttons by the left edge
    "R32": (11.0, 39.6, 0), "D1": (13.5, 39.6, 180), "R33": (11.0, 41.2, 0), "D2": (13.5, 41.2, 180),
    "R34": (11.0, 42.8, 0), "D3": (13.5, 42.8, 180), "R35": (11.0, 44.4, 0), "D4": (13.5, 44.4, 180),
    "SW1": (5.0, 47.0, 0), "R36": (8.4, 47.0, 90), "SW2": (12.0, 47.0, 0), "R37": (15.4, 47.0, 90),
    # pull-ups and links by their header pins
    "R38": (99.0, 6.8, 90), "R39": (100.2, 6.8, 90), "R44": (60.2, 8.2, 90), "R45": (61.4, 8.2, 90),
    "R46": (113.0, 41.2, 90), "R47": (52.0, 41.2, 90), "R48": (39.2, 41.6, 90),
    "R40": (58.4, 40.8, 90), "R41": (59.6, 40.8, 90), "R43": (51.2, 11.0, 0),
}
_unplaced = sorted({p.ref for p in PARTS} - set(PLACEMENT))
assert not _unplaced, f"parts without a board position: {_unplaced}"
# Back side, under the chip body (SPMA056 Table 7's 128-pin example has most of its capacitors on the back):
# the pins' outer ends stay free for their neighbours' escapes, each pin reaching its capacitor through a
# via inside the pad ring. They sit 2.5-3.5 mm inside the pad ends, below and left of the device USB pair's
# path under the chip, so their own plane vias (placed away from the chip's centre) leave the pad ends'
# inner side open for escape vias.
BOTTOM = {"C4", "C6", "C19", "C20", "C21", "C22", "C27", "C29", "C30", "C46"}
for _p in PARTS:
    _p.pcb = PLACEMENT[_p.ref]
    if _p.ref in BOTTOM:
        _p.side = "B"

# Laid before the autorouter, in this order, and locked (pcb_build.py priority_routes):
# * the Ethernet pairs, chip to termination resistor to ESD part to jack, and RBIAS, top layer;
# * the crystals: pin -> (Rs ->) crystal pad -> load capacitor, top layer, no via;
# * PB0 and PB1 (pins 95, 96) to their resistors just below them;
# * the device USB pair: contacts A6/A7 to U3's pads, then pins 93/94 back to U3 under the chip's body,
#   inside its pad ring: the pair enters the ring at the corner between pins 32 and 33, so none of the
#   chip's escapes has to cross it on the top layer (the corner leaves 0.89 mm between the pads'
#   corners, room for two 0.13 mm lines at 0.15 mm clearance). D- goes first, from the chip, so it
#   takes the corner's inner side and D+ fits beside it. Then the receptacle's second contacts B6/B7;
# * the debug USB pair (as on EoS TM4C123 Board), the CP2102N's RSTb and ground pin;
# * the TPS2116's VOUT pins joined between its rows, and MODE to VIN1;
# * each decoupling capacitor to its pin(s), ground pins 55 and 58 (between the Ethernet pins) joined
#   to pin 48 inside the pad ring, VDDC pin 87 to its capacitor and, through the bottom layer under
#   the chip, to pin 115's capacitors.
PRIORITY = [
    # the transmit pair first, straight out; the receive pair then climbs over R9 to U6's level
    # each line enters its ESD part's flow-through pad on the chip side (10, 9), hops to the twin pad (1, 2)
    # and leaves from it for the jack: ending every route on a pad, so the autorouter sees the twins joined
    # and does not lay a second track beside the first
    (("U1", "56"), ("R9", "1")), (("R9", "1"), ("U7", "10")), (("U7", "10"), ("U7", "1")), (("U7", "1"), ("J8", "3")),
    (("U1", "57"), ("R10", "1")), (("R10", "1"), ("U7", "9")), (("U7", "9"), ("U7", "2")), (("U7", "2"), ("J8", "1")),
    (("U1", "53"), ("R7", "1")), (("R7", "1"), ("U6", "10")), (("U6", "10"), ("U6", "1")), (("U6", "1"), ("J8", "6")),
    (("U1", "54"), ("R8", "1")), (("R8", "1"), ("U6", "9")), (("U6", "9"), ("U6", "2")), (("U6", "2"), ("J8", "4")),
    (("U1", "59"), ("R11", "1")),
    (("U1", "88"), ("Y1", "1")), (("Y1", "1"), ("C23", "1")),
    (("U1", "89"), ("R1", "1")), (("R1", "2"), ("Y1", "3")), (("Y1", "3"), ("C24", "1")),
    (("U1", "66"), ("Y2", "1")), (("Y2", "1"), ("C25", "1")),
    (("U1", "67"), ("Y2", "2")), (("Y2", "2"), ("C26", "1")),
    # HIB (pin 65) is boxed in by XOSC0's line just below its pad: out of the pad to the left, below R5/R6,
    # to the load switch's ON pin; then the switch's QOD to its output, the output to C44 and on to R10's
    # supply end, and C43 to R7's supply end. The rest of ETH_VTERM is left to the router.
    (("U1", "65"), ("U9", "3")),
    (("U9", "6"), ("R10", "2")), (("U9", "5"), ("R49", "2")), (("R49", "1"), ("U9", "6")),
    (("C43", "1"), ("R7", "2")), (("R8", "2"), ("C44", "1")), (("C44", "1"), ("R9", "2")), (("C45", "1"), ("U9", "1")),
    # the gap between the pairs (R8, R9, C44) to the switch's side (R10, U9): under the transmit pair, through
    # the bottom layer
    (("R9", "2"), ("R10", "2")),
    (("U1", "95"), ("R42", "1")), (("U1", "96"), ("R17", "2")),
    (("J7", "A7"), ("U3", "3")), (("U1", "93"), ("U3", "3")),
    (("J7", "A6"), ("U3", "2")), (("U1", "94"), ("U3", "2")),
    (("J7", "B6"), ("J7", "A6"), "join"), (("J7", "B7"), ("J7", "A7"), "join"),
    (("J6", "A6"), ("U2", "2")), (("U2", "2"), ("U5", "4")),
    (("J6", "A7"), ("U2", "3")), (("U2", "3"), ("U5", "5")),
    (("J6", "B6"), ("J6", "A6"), "join"), (("J6", "B7"), ("J6", "A7"), "join"),
    (("U5", "9"), ("R24", "1")), (("U5", "3"), ("U5", "21")),
    # VREGIN (7) and VDD (6) joined at the corner and down to C35, so BR_VBUS (8) leaves between them and R24
    (("U5", "7"), ("U5", "6")), (("U5", "6"), ("C35", "1")),
    (("U4", "2"), ("U4", "7")), (("U4", "5"), ("C37", "1")), (("U4", "6"), ("C36", "1")),
    (("U1", "7"), ("C1", "1")), (("U1", "8"), ("C12", "1")), (("C12", "1"), ("C15", "1")),
    (("C1", "2"), ("C12", "2")),          # C1's ground end has no room for a via of its own: C12's
    (("U1", "9"), ("C18", "1")), (("U1", "10"), ("C18", "2")), (("C18", "1"), ("C17", "1")),
    (("U1", "16"), ("C2", "1")), (("U1", "17"), ("C2", "2")),
    (("U1", "26"), ("C3", "1")), (("U1", "28"), ("C3", "1")),
    (("U1", "39"), ("C4", "1")), (("U1", "47"), ("C5", "1")), (("U1", "48"), ("C5", "2")),
    (("U1", "51"), ("C6", "1")), (("U1", "52"), ("U1", "51")),
    # GND 55 and 58 (between the Ethernet pins) go inward to C6's ground pad under the chip, not along the
    # pad ends to pin 48, which boxed pins 49-52 in
    (("U1", "55"), ("C6", "2")), (("U1", "58"), ("U1", "55")), (("U1", "90"), ("C46", "1")),
    (("U1", "69"), ("C7", "1")), (("U1", "70"), ("C27", "1")),
    (("U1", "79"), ("C8", "1")), (("U1", "80"), ("C8", "2")),
    (("U1", "101"), ("C9", "1")), (("U1", "113"), ("C10", "1")), (("U1", "114"), ("C10", "2")),
    (("U1", "115"), ("C19", "1")), (("C19", "1"), ("C20", "1")), (("C19", "1"), ("C21", "1")),
    (("U1", "122"), ("C11", "1")),
    # VDDC: pin 87 to its own capacitor, then to pin 115's 1 uF: the device pair runs between the two pins
    # inside the pad ring, so this join drops to the bottom layer under the chip
    (("U1", "87"), ("C22", "1")), (("U1", "87"), ("C20", "1")),
    # each transformer centre tap to its own 1 uF on the bottom side (SPMS433B Figure 20-13 note)
    (("J8", "2"), ("C29", "1")), (("J8", "5"), ("C30", "1")),
]

# Router keep-outs on the bottom layer under each crystal and its load capacitors: nothing but ground under
# them. Their lines from the pins have the inner-1 ground plane right under them, so the keep-outs stop short
# of the pin row: a keep-out there forbids vias too and left the bottom-row pins (PL0-PL5, PM) no way out.
# On the top layer the crystal's own lines, laid first, fill the area (a top-layer keep-out would also keep
# those lines out, since the routers apply it to every net).
KEEPOUTS = [
    (38.0, 33.4, 42.6, 37.8, "B.Cu"),      # 32.768 kHz: Y2, C25, C26
    (48.9, 35.8, 57.1, 39.4, "B.Cu"),      # 25 MHz: Y1, C23, C24
]
# No top-layer strip beside OSC0's line: one (0.2 mm wide, x 52.55-52.75 from y 32.75 to 37.2) held PL5
# 0.54-0.65 mm from it, but it narrowed the one top-layer way out that PL0-PL5 share between C8 and OSC0,
# and PL2 (pin 83) was left unrouted in two of five builds with it.
# The ground pours on the outer layers are held off the chassis copper (the jack's shield pins, its pin 8
# and the chassis ends of R12 and C31): 0.66-1.16 mm round those pads on the routed board (SPMA056 3.3.6,
# 4.1.8: a chassis ground pulled back from the logic ground). Only the outer pours can be held off: the
# generator's pour keep-outs are outer-layer rule areas (build.spec_for accepts F.Cu or B.Cu), and the inner
# planes cover the whole board.
POUR_KEEPOUTS = [(x0, y0, x1, y1, layer) for layer in ("F.Cu", "B.Cu") for x0, y0, x1, y1 in (
    (10.6, 13.9, 15.1, 18.4),              # shield pin at (12.85, 16.155), 2.2 mm pad
    (10.6, 29.7, 15.1, 34.2),              # shield pin at (12.85, 31.955)
    (14.3, 17.8, 18.0, 21.0),              # pin 8 (Bob Smith termination) at (16.15, 19.61)
    (2.9, 36.0, 6.1, 38.9),                # R12's chassis pad at (4.5, 37.26)
    (5.7, 32.7, 9.2, 38.1),                # C31's chassis pad at (7.45, 35.4)
)]
# The decoupling capacitors take their plane vias before the priority routes (fanout_first), so the
# lines laid first cannot box a capacitor's via spot in.
DECOUPLING = [f"C{k}" for k in (*range(1, 13), 14, 15, *range(17, 23), 27, 29, 30, 43, 44, 45, 46)]

TEXTS = [
    {"text": "EoS TM4C1294 Board  rev A", "x": 111.8, "y": 32.0, "size": 1.0, "layer": "B_SilkS", "bold": True, "mirror": True},
    {"text": "(c) 2026 Kartikeydheer Srivastava", "x": 111.8, "y": 34.0, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    {"text": "All rights reserved", "x": 111.8, "y": 35.4, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    # front: the sites and their rows, which USB-C is which, the jumpers' two settings, buttons and LEDs
    {"text": "BOOSTERPACK 1", "x": 111.8, "y": 24.0, "size": 1.0},
    {"text": "5V, 3V3 PINS = OUT", "x": 111.8, "y": 26.0, "size": 0.8},
    {"text": "BOOSTERPACK 2", "x": 65.4, "y": 24.0, "size": 1.0, "angle": 90},
    # row letters beside each site's pin-10 end, clear of the headers' outlines (99.0 and 35.5 mm) and of the
    # USB-C outlines (96.1 and 34.2 mm)
    *[{"text": t, "x": x, "y": y, "size": 0.8} for x in (98.2, 34.75)
      for t, y in (("A", ROW_A), ("B", ROW_B), ("C", ROW_C), ("D", ROW_D))],
    {"text": "1", "x": BP1_PIN1, "y": 49.6, "size": 0.8}, {"text": "97", "x": 1.27, "y": 49.6, "size": 0.8},
    {"text": "USB DEV", "x": 37.0, "y": 8.0, "size": 1.0}, {"text": "UART", "x": DBG_X, "y": 14.6, "size": 1.0},
    {"text": "SWD", "x": 72.0, "y": 26.6, "size": 1.0},
    {"text": "RX", "x": 64.57, "y": 7.6, "size": 0.8}, {"text": "TX", "x": 70.77, "y": 7.6, "size": 0.8},
    {"text": "UART 1-2 3-4", "x": 67.7, "y": 8.9, "size": 0.8}, {"text": "CAN 1-3 2-4", "x": 67.7, "y": 10.1, "size": 0.8},
    {"text": "PJ0", "x": 5.0, "y": 49.6, "size": 0.8}, {"text": "PJ1", "x": 12.0, "y": 49.6, "size": 0.8},
    {"text": "RESET", "x": 31.4, "y": 49.6, "size": 0.8}, {"text": "WAKE", "x": 25.6, "y": 49.6, "size": 0.8},
    *[{"text": t, "x": 16.6, "y": y, "size": 0.8} for t, y in (("PN1", 39.6), ("PN0", 41.2), ("PF4", 42.8), ("PF0", 44.4))],
    {"text": "PWR", "x": 85.0, "y": 29.6, "size": 0.8},
]

BOARD = Board(
    name="eos-tm4c1294-board",
    title="EoS TM4C1294 Board",
    revision="A",
    date="2026-10-12",
    company=OWNER,
    licence=LICENCE,
    contact=CONTACT,
    licence_terms=LICENCE_TERMS,
    credits=["Outline, header and breakout positions, mounting-hole centres and the signal on each header pin: TI SPMU365C "
             "(EK-TM4C1294XL User's Guide), Table 1-1, Tables 2-1 to 2-4 and Figure 4-1, used as mechanical and pinout facts "
             "only; hole drill enlarged from 3.175 to 3.2 mm for M3 clearance",
             "BoosterPack header type (female with long male leads) from TI's BoosterPack Pinout Standard (updated Sept 1, "
             "2013), used as a fact only"],
    width=W,
    height=H,
    corner_radius=0.5,     # J1 pin 1 is 0.05 in from both edges (Figure 4-1): its pad stays 0.39 mm from the corner
    thickness=1.6,
    layers=6,
    planes=[("GND", "In1.Cu"), ("+3V3", "In4.Cu")],
    fanout_avoid=[(MX, MY)],
    fanout_first=DECOUPLING,
    local_footprints=["EoS_Packages"],
    parts=PARTS,
    priority_routes=PRIORITY,
    router_keepouts=KEEPOUTS,
    pour_keepouts=POUR_KEEPOUTS,
    maze_via_cost_mm=20.0,
    power_nets={"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V"},
    flagged_nets=["GND", "+3V3", "VDBG", "VTGT", "VDDC", "VBAT", "VREFA", "CHASSIS"],
    headings=[((30, 45), "Debug USB-C, ESD (SP0503), fuse"), ((150, 45), "CP2102N USB-UART (on 3.3 V, VBUS sense + bleed)"),
              ((30, 150), "Device USB-C (USB0), ESD (SP0503), fuse, VBUS sense"), ((150, 130), "5 V priority mux, 3.3 V buck, power LED"),
              ((265, 145), "TM4C1294NCPDT"), ((350, 95), "Decoupling, VDDA, VREFA+, VDDC (SPMA056 3.4)"),
              ((350, 185), "25 MHz and 32.768 kHz crystals"), ((410, 180), "Reset (Fig. 5-3)"),
              ((410, 215), "Hibernation: VBAT, WAKE"), ((30, 240), "Ethernet: termination on ETH_VTERM (off in hibernation, HIB), RBIAS, ESD, MagJack"),
              ((410, 285), "BoosterPack sites and 98-hole breakout"), ((410, 380), "Cortex Debug header"),
              ((30, 320), "User LEDs, buttons, pull-ups, links"), ((240, 385), "Mounting holes")],
    power_block=(40.64, 410.0),
    notes=[((330, 130), "EoS TM4C1294 Board, rev A, two BoosterPack-compatible (40-pin) sites, 98-hole breakout, 10/100 Ethernet.\n"
                        "Designed by Kartikeydheer Srivastava.\n"
                        "Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved; see LICENSE.txt.\n"
                        "Values from TI SPMS433B (TM4C1294NCPDT), SPMA056 and SPMZ850G; Silicon Labs CP2102N Rev. 1.5; TI SLVSFG1A,\n"
                        "SLVSDG1C, SLVSAC2G, SLVSDW8B; Littelfuse SP05xxBA and 1206L; Wurth 7499010121A; NDK NX3225GA; Abracon ABS07;\n"
                        "Coilcraft XAL4000; Nexperia BAT54J; Kingbright.\n"
                        "Firmware: OSCDRV = 1 (C25/C26 20 pF); USB as a forced device, VBUS on PB1; PD7 is NMI-locked.\n"
                        "HIB switches ETH_VTERM (termination and centre taps) off in hibernation (SPMS433B 7.3.9).\n"
                        "JP1/JP2: 1-2 + 3-4 = UART0 to the bridge, PD4/PD5 on BP2 A.5/A.6; 1-3 + 2-4 = CAN0 on BP2, bridge on UART2.\n"
                        "Budget: 5 V pins + 0.75 x 3.3 V pins <= 300 mA in all. 3.3 V and 5 V header pins are outputs.")],
    # Every net entering the TQFP-128 (0.25 mm pads, 0.4 mm pitch) is 0.15 mm wide: the router needs 0.19 mm
    # from a pad's centre line to the next pad, so a wider track cannot get in. Power into the 0.5 mm-pitch
    # TPS2116 and CP2102N at 0.3 mm; the debug USB and Ethernet pairs at 0.15 mm, the device USB pair at
    # 0.13 mm, so that both its lines pass the corner between pins 32 and 33 (see the stack-up note).
    netclasses={"Power": {"track": 0.4, "clearance": 0.15}, "Supply": {"track": 0.3, "clearance": 0.15},
                "USB": {"track": 0.15, "clearance": 0.15}, "USB0": {"track": 0.13, "clearance": 0.15},
                "Ethernet": {"track": 0.15, "clearance": 0.15}},
    net_to_class={"VBUS_DBG": "Power", "VBUS_TGT": "Power", "BUCK_SW": "Power",
                  "VDBG": "Supply", "VTGT": "Supply", "+5V": "Supply", "ETH_VTERM": "Supply",
                  "DBG_D+": "USB", "DBG_D-": "USB", "TGT_D+": "USB0", "TGT_D-": "USB0",
                  "ETH_RXN": "Ethernet", "ETH_RXP": "Ethernet", "ETH_TXN": "Ethernet", "ETH_TXP": "Ethernet"},
)
