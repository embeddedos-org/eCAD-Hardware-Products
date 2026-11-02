"""EoS LPC55S69 Board: an NXP LPC55S69 development board that fits Uno R3 shields, designed by Kartikeydheer Srivastava.

Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved: this design file is not under
the repository's MIT licence; see boards/eos/eos-lpc55s69-board/LICENSE.txt.

A 68.58 x 53.34 mm four-layer board for the NXP LPC55S69JBD100 (dual Cortex-M33, HLQFP-100),
with Arduino Uno R3 shield headers, two USB-C ports (the chip's USB0 full-speed device port and
a CP2102N debug UART), an Arm 10-pin SWD header, reset, ISP and user buttons, an RGB LED and a
power LED. It does the job of NXP's LPCXpresso55S69; none of that board's design files was
opened. The circuit comes from the chip makers' data sheets and application notes:

* NXP LPC55S6x data sheet Rev. 2.5 (29 August 2024; the Wayback Machine copy of nxp.com's PDF,
  since nxp.com refuses scripted downloads), "DS" below; NXP AN13033 Rev. 2.1 "Hardware Design
  Guidelines for LPC55(S)xx" (Wayback copy), "AN13033"; NXP UM11126 Rev. 1.3 (Wayback copy).
* Pins: DS Table 3, HLQFP-100 column. On this package the exposed pad is the only VSS (DS
  Table 3), so it is soldered to ground (pad 101).
* Supplies, all from one 3.3 V rail: VDD, VBAT_DCDC, VBAT_PMU, USB0_3V3, USB1_3V3 (DS Table 4
  and AN13033 Table 12: "Tie to VBAT_DCDC"); VDDA and VREFP through a ferrite bead (Bourns
  MH1608-221Y: 220 ohm at 100 MHz, 100 mohm, 2 A), since both feed the 16-bit ADC. VREFN, VSSA,
  VSS_DCDC, USB0_VSS and USB1_VSS go to ground ("VSS, VSSA, and VREFN must be shortened to GND",
  AN13033 Table 6).
* Decoupling (AN13033 Table 6, HLQFP-100 column, and Figure 2): 100 nF X7R on each of the nine
  VDD pins and 10 uF for the VDD domain; 10 uF + 100 nF each on USB0_3V3, USB1_3V3, VDDA and
  VREFP; 22 uF + 100 nF + 47 pF on VBAT_DCDC (DS Figure 6) and 100 nF on VBAT_PMU (AN13033
  Figure 2, C27).
* DC-DC converter (DS section 6.1.2, Figure 6): LX to a 4.7 uH inductor, its output 22 uF to
  ground, VDD_PMU and FB tied together ("VDD_PMU and FB are tied at PCB level", DS Table 3),
  plus 100 nF at VDD_PMU (AN13033 Figure 2, C12). The inductor is a Bourns SRN4018-4R7M
  (4.7 uH +-20 %, 84 mohm, Isat 2.0 A, Irms 1.9 A); the chip draws 6.2 mA typical at 150 MHz
  (DS Table 16), so the rating is far above the load.
* Supply ramp: VBAT_DCDC must rise in no less than 0.5 ms (0-105 C) and 2.6 ms (-40 C) (DS
  Table 25; AN13033 section 10 suggests an LDO with soft start). The TPS7A91 LDO (TI SBVS282A)
  ramps its output in tSS = VREF x CNR/SS / INR/SS (Equation 6): with SS_CTRL to ground,
  INR/SS is 4.0-9.0 uA, so CNR/SS = 47 nF gives 4.2-9.4 ms (3.8 ms with -10 % capacitance).
  Output 3.283 V from R1 = 3.57 kohm, R2 = 1.15 kohm (Table 7-1), 10 uF in and out (section
  5.3), EN tied to IN (section 7.1.2.1), PG unused (Table 4-1: "can be left floating"). TI's
  10 uF minimum allows for 50 % DC-bias loss (section 7.1.3), so it asks for 5 uF in use. The
  output capacitor is a 10 uF 16 V X5R 0805 (Murata GRM21BR61C106KE15L): Murata's C-DC bias
  curve (25 C) gives about -35 % at 3.3 V, so about 6.5 uF. The input capacitor is a 22 uF 10 V
  X5R 0805 (GRM21BR61A226ME51L), because the 10 uF part keeps only about 4.7 uF at 5 V: the
  22 uF part's curve gives -64 % at 5 V and -67 % at 5.5 V, about 8.0 and 7.3 uF (6.4 and 5.8 uF
  at its -20 % tolerance).
* 3.3 V budget: the board itself draws an estimated 70 mA or less: the LPC55S69 6.2 mA typical
  at 150 MHz with the core alone (DS Table 16; NXP gives no maximum, so 50 mA is allowed for
  peripherals and USB), the CP2102N 9.5 mA typical (CP2102N data sheet Table 3.2), the LEDs and
  pull-ups about 7 mA. Shields may take up to 150 mA from the 3V3 pin. At 220 mA and 5.5 V in
  the TPS7A91 dissipates 0.50 W: 31 C above ambient at the JEDEC RthetaJA of 62.5 C/W (SBVS282A
  section 5.4). Its thermal pad has no via in the pad: the generator gives in-pad vias only to
  pads over 2 mm on both sides, and this one is 1.2 x 2.0 mm, so it reaches the ground plane
  through the top-layer ground pour and that pour's vias, and the real rise is higher by an
  amount not known. The 3V3 and IOREF pins are outputs: OUT may not rise more than 0.3 V above
  IN (SBVS282A section 5.1), and with no USB power IN is near 0 V.
* Clocks: 16 MHz crystal (DS Table 3: "For USB HS ISP mode, 16 MHz crystal is required"), ECS
  ECX-33Q with CL = 8 pF and 80 ohm ESR (ECS-160-8-33Q-JES-TR); 32.768 kHz Abracon ABS07,
  CL = 7 pF, 70 kohm ESR (ABS07-32.768KHZ-7-T). Both loads lie in the 6-10 pF range the chip's
  internal capacitor banks tune (DS sections 13.3 and 13.4; UM11126 chapter 12), and AN13033
  section 4.1 advises keeping the external load capacitors unpopulated: their pads are here,
  marked DNP, with AN13033's value CX = 2 CL - (CPad + CParasitic) with CPad = 3 pF and 2 pF
  stray: 11 pF (16 MHz) and 9 pF (32.768 kHz).
* USB0 (full speed, device): 33 ohm series resistors on DP and DM (DS Figure 30). USB0_VBUS
  (PIO0_22, DS section 13.5) through a 4.7 kohm / 6.8 kohm divider: 5.25 V reads 3.10 V and
  5.5 V reads 3.25 V, under the 3.6 V limit; 4.4 V still reads 2.43 V with the 40 kohm minimum
  internal pull-down enabled (DS Table 24), above VIH = 0.7 x VDD = 2.32 V. The divider's
  11.5 kohm also bleeds the port's VBUS.
* USB1 (high speed) is not used. The generator can't hold a 90 ohm differential pair or check
  it, so USB1_DP/DM are left open, USB1_VBUS goes to 3.3 V (AN13033 Table 12) and USB1_3V3 is
  powered and decoupled, as DS Table 4 and AN13033 Table 12 ask for an unused port.
* Reset, ISP, SWD (AN13033 section 6, Table 10, Figure 7): 10 kohm pull-ups on SWDIO, SWO and
  RESETN, 10 kohm pull-down on SWCLK. SWO is PIO0_10 (function 6, DS Table 3). The ISP button
  pulls PIO0_5 low (UM11126 Table 167: low at reset = ISP boot); PIO0_5's internal pull-up is
  on at reset (DS Table 3), and no pull-down is fitted (AN13033 Table 10's TDI pull-down would
  force ISP boot).
* Debug UART: Silicon Labs CP2102N-A02-GQFN24 (data sheet Rev. 1.5) on FLEXCOMM0
  (PIO0_29 = FC0_RXD, PIO0_30 = FC0_TXD; the ROM's UART ISP pins, UM11126 Table 169). It runs
  from the board's 3.3 V (Figure 2.3, VREGIN tied to VDD), so it is never unpowered while the
  LPC55S69 is, and VIO is tied to VDD; 4.7 uF + 0.1 uF on VREGIN/VDD and on VIO (section 2.1),
  each 0.1 uF beside its pins (VIO/VDD pins 5 and 6, VREGIN pin 7: Figure 2.3, "placed as close
  to the pins as possible"); 1 kohm pull-up on RSTb (section 2.1). VBUS sense through 22.1 kohm
  / 47.5 kohm (Figure 2.6, the self-powered case; Figure 2.5 gives the same values), plus a
  5.1 kohm bleed from the debug port's VBUS to ground (see the VBUS bleed note below).
  Unused CTS, DSR, DCD, RI and GPIO pins are open (section 4.3.1: weak pull-ups by default).
* VBUS bleed: with no host on the debug port, only the power mux's reverse leakage (TI
  SLVSFG1A IREV, 0.15 uA typical at 105 C; no maximum given) can lift that VBUS. The CP2102N
  reads its VBUS pin as low up to VIL = 0.6 V (Table 3.7); the divider puts 47.5/69.6 of VBUS on
  it, so VBUS may reach 0.88 V. With the bleed the node is 4.75 kohm: 185 uA of leakage is
  needed to fake a host. A host pays 1.0 mA.
* USB ESD: Littelfuse SP0503BAHTG on both ports, diodes to ground only, as the CP2102N data
  sheet shows (Figures 2.5 and 2.6); both ports' chips sense VBUS. Pin 1 is the common node and
  pins 2-4 are one TVS each (Littelfuse SP05xxBA data sheet, pinout), so D+ and D- may take
  either of pins 2 and 3. Each pair runs from the receptacle through its ESD part to the chip
  as a priority route on the top layer, with no stub (see PRIORITY). USB-C as a 5 V sink:
  5.1 kohm Rd on CC1 and CC2 (TI SLVSFJ9 section 10.3.14.2). Each VBUS has a Littelfuse
  1206L050 polyfuse (0.50 A hold, 1.00 A trip, 6 V, R1max 0.70 ohm).
* Power mux: TI TPS2116 (SLVSFG1A) in priority mode, MODE tied to VIN1 (the debug port) and PR1
  from VIN1 through 27 kohm / 10 kohm: the debug port is used down to 3.7 x VREF = 3.40-4.00 V
  (VREF 0.92-1.08 V, Table 6.5; 3.35-4.05 V with 1 % resistors), and USB0 below that (section
  7.6.1.1). The lower end keeps the LDO in regulation until the switch: 3.283 V plus the
  TPS7A91's dropout, which scales as 0.2 ohm x IOUT (200 mV at 1 A, SBVS282A section 5.5 and
  Equation 1: 44 mV at 220 mA), plus 13 mV across the mux (RON 60 mohm max, Table 6.5). The
  upper end stays below what a working port delivers: 4.40 V, the USB 2.0 minimum at a device,
  less F2's 0.15 V at 220 mA and R1max. Reverse current blocking (section 7.3.4) keeps either
  port, and 5 V fed into the 5V header pin, from the other. 1 uF on each input (section 9),
  100 uF on VOUT (section 7.3.4).
* I2C on the SDA/SCL header pins: PIO0_13/PIO0_14 (FC1, I2C ISP pins, true open-drain, DS Table
  3 note 5: "requires an external pull-up"). 2.2 kohm to 3.3 V: above TI SLVA689A's RP(min) =
  (3.3 - 0.4) V / 3 mA = 0.97 kohm, and fast-mode's 300 ns rise holds up to 161 pF.
* LEDs: power LED Kingbright APTD1608LCGCK (green, VF 1.9 V typ at 2 mA, DSAO7432) through
  680 ohm from 3.3 V: 2.1 mA. RGB LED LiteOn LTST-C19HE1WT (common anode, DS22-2008-0044):
  green and blue need up to 3.9 V at 20 mA, too much for a 3.3 V GPIO, so the anode is on 5 V
  and each cathode has a Nexperia BSS138BK low-side switch (VGSth 0.48-1.6 V, RDSon <= 6.5 ohm at
  VGS = 2.5 V, ID = 10 mA: Rev. 1 Table 6). At 5 mA LiteOn's Fig. 2 gives VF 2.15 V (red) and
  2.75 V (green, blue): 560 ohm gives 5.1 mA and 470 ohm 4.8 mA. 100 kohm holds each gate low
  while its pin is still high-impedance after reset (DS section 6.1: pulls off at reset).
* Buttons: C&K KMR2 tactile switches. User button on PIO1_27 with a 10 kohm pull-up (the
  internal pull-up is off at reset, DS section 6.1).

Arduino Uno R3 mechanics (origin top-left, y down; the sources use mils from the lower-left,
y up), facts only: outline 2700 x 2100 mil and the header positions (digital 10-pin from 740
mil and 8-pin from 1800 mil on the 2000-mil row; power 8-pin from 1100 mil and analog 6-pin
from 2000 mil on the 100-mil row) from Matthew Beckler's "Arduino Uno R3" dimension drawing
v1.05 (public domain), as EoS Uno uses them. The 3.20 mm holes: (600, 2000), (2600, 1400) and
(2600, 300) mil, and the bottom-left hole's 100 mil height, from Arduino's UNO R3 product
reference manual (A000066) section 5.4; that figure does not dimension the bottom-left hole's
x, so its 550 mil comes from Beckler's drawing. The outline is the full 2700 x 2100 mil
rectangle, not the Uno's stepped and chamfered right-hand edge (A000066 section 5.4), as on the
repository's other Uno-size boards; it may not fit an Uno-shaped case or bumper. The R3 pinout
puts the 10-pin socket's end 0.69 mm from the top-left hole's edge, so that hole (H1) is placed
from the back, as on EoS Uno: a screw or standoff there goes in from the bottom, since a
top-side M3 head (5.5 mm) would hit that socket.

Pin map (DS Table 3 functions): D0/D1 = PIO0_8/PIO0_9 (FC5 USART RXD/TXD); D2-D9 = PIO1_10,
PIO1_22 (CTIMER2_MAT3), PIO1_23, PIO1_17 (SCT0_OUT4), PIO0_0 (CTIMER0_MAT0), PIO0_18,
PIO1_14, PIO1_19 (CTIMER3_MAT1); D10-D13 = the high-speed SPI: PIO1_1 (HS_SPI_SSEL1), PIO0_26
(MOSI), PIO1_3 (MISO), PIO1_2 (SCK); SDA/SCL = PIO0_13/PIO0_14; A0-A5 = PIO1_0 (ADC0_11),
PIO0_16 (ADC0_8), PIO0_23 (ADC0_0), PIO0_15 (ADC0_2), PIO0_31 (ADC0_3), PIO1_8 (ADC0_4).
IOREF is 3.3 V: the LPC55S69's pins take at most VDD + 0.5 V (DS Table 11), so shields must
use 3.3 V logic. AREF and VIN are not connected (see the README).

Four layers: inner layer 1 is ground and inner layer 2 is 3.3 V. AN13033 section 9.3 asks for
separate ground and supply layers; the exposed pad is the chip's only VSS, so its return
current wants a plane right under it; and fifteen 3.3 V pins sit on all four sides of the
HLQFP-100, which on two layers would need a ring cutting every signal's escape.
"""

from __future__ import annotations

from ..design import NC, Board, Part, USB_C_EDGE
from .owner import CONTACT, LICENCE, LICENCE_TERMS, OWNER

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C1210 = "Capacitor_SMD:C_1210_3225Metric"
HOLE = "MountingHole:MountingHole_3.2mm_M3_ISO14580"
USB_C = "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"
KMR2 = "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2"

DS = "NXP LPC55S6x DS Rev. 2.5"
AN = "NXP AN13033 Rev. 2.1"
CP = "Silicon Labs CP2102N DS Rev. 1.5"


def res(ref, value, a, b, sch, desc, rot=0):
    return Part(ref, "Device:R_Small", value, R0402, sch, {"1": a, "2": b}, fields={"Description": desc},
                sch_rotation=rot)


# Capacitor part numbers, each checked against distributor listings (value, voltage, dielectric, case);
# left out where no listing confirmed one (1 uF X7R 0402) and on the DNP crystal pads.
C100N = ("Samsung Electro-Mechanics", "CL05B104KO5NNNC")    # 100 nF 16 V X7R 0402
C10U_0603 = ("Murata", "GRM188R61A106MAALD")                # 10 uF 10 V X5R 0603
C10U_0805 = ("Murata", "GRM21BR61C106KE15L")                # 10 uF 16 V X5R 0805
C22U = ("Murata", "GRM21BR61A226ME51L")                     # 22 uF 10 V X5R 0805
C4U7 = ("Murata", "GRM188R61A475KE15D")                     # 4.7 uF 10 V X5R 0603


def cap(ref, value, a, b, sch, desc, fp=C0402, rot=0, dnp=False, mpn=None):
    fields = {"Description": desc, **({"Manufacturer": mpn[0], "MPN": mpn[1]} if mpn else {})}
    return Part(ref, "Device:C_Small", value, fp, sch, {"1": a, "2": b}, fields=fields, sch_rotation=rot, dnp=dnp)


def socket(ref, n, value, pins, sch, desc):
    """A female header for shields: pin 1 is the first signal named in ``pins``."""
    return Part(ref, f"Connector:Conn_01x{n:02d}_Socket", value,
                f"Connector_PinSocket_2.54mm:PinSocket_1x{n:02d}_P2.54mm_Vertical", sch,
                {str(i + 1): net for i, net in enumerate(pins)},
                fields={"Manufacturer": "Samtec", "MPN": f"SSW-1{n:02d}-01-T-S", "Description": desc})


def usb_c(ref, prefix, sch, what):
    return Part(ref, "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", USB_C, sch,
                {"VBUS": f"VBUS_{prefix}", "GND": "GND", "CC1": f"{prefix}_CC1", "CC2": f"{prefix}_CC2",
                 "D+": f"{prefix}_C_DP", "D-": f"{prefix}_C_DM", "SBU1": NC, "SBU2": NC, "SHIELD": "GND"},
                fields={"Manufacturer": "Korean Hroparts", "MPN": "TYPE-C-31-M-12",
                        "Description": f"USB-C 2.0 receptacle, 16 pins: {what}"})


def esd(ref, prefix, sch, swap=False):
    # pins 2, 3 and 4 are the same diode to the common anode (pin 1, Littelfuse SP05xxBA pinout), so
    # a port may use either order
    dp, dm = ("3", "2") if swap else ("2", "3")
    return Part(ref, "Power_Protection:SP0503BAHT", "SP0503BAHTG", "Package_TO_SOT_SMD:SOT-143", sch,
                {"1": "GND", dp: f"{prefix}_C_DP", dm: f"{prefix}_C_DM", "4": f"VBUS_{prefix}"},
                fields={"Manufacturer": "Littelfuse", "MPN": "SP0503BAHTG",
                        "Description": "USB ESD protection, three diodes to GND on D+, D- and VBUS, no path between "
                                       f"them (Littelfuse SP05xxBA: pin 1 common; {CP} Figures 2.5 and 2.6)"})


def fuse(ref, a, b, sch):
    return Part(ref, "Device:Polyfuse_Small", "500mA", "Fuse:Fuse_1206_3216Metric", sch, {"1": a, "2": b},
                fields={"Manufacturer": "Littelfuse", "MPN": "1206L050YR",
                        "Description": "PTC resettable fuse 0.50 A hold, 1.00 A trip, 6 V, 1206 (Littelfuse 1206L datasheet)"})


def button(ref, value, net, sch, what):
    return Part(ref, "Switch:SW_Push", value, KMR2, sch, {"1": net, "2": "GND"},
                fields={"Manufacturer": "C&K", "MPN": "KMR221G LFS", "Description": f"Tactile switch, {what}"})


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

# LPC55S69 pins used (DS Table 3); every other PIO is left open (DS Table 4: an unused PIO may be
# left unconnected when software drives it low).
MCU_PINS = {
    "PIO0_8": "D0", "PIO0_9": "D1", "PIO1_10": "D2", "PIO1_22": "D3", "PIO1_23": "D4", "PIO1_17": "D5",
    "PIO0_0": "D6", "PIO0_18": "D7", "PIO1_14": "D8", "PIO1_19": "D9", "PIO1_1": "D10", "PIO0_26": "D11",
    "PIO1_3": "D12", "PIO1_2": "D13", "PIO0_13": "SDA", "PIO0_14": "SCL",
    "PIO1_0": "A0", "PIO0_16": "A1", "PIO0_23": "A2", "PIO0_15": "A3", "PIO0_31": "A4", "PIO1_8": "A5",
    "PIO0_11": "SWCLK", "PIO0_12": "SWDIO", "PIO0_10": "SWO", "PIO0_5": "ISP_N",
    "PIO0_29": "FC0_RXD", "PIO0_30": "FC0_TXD", "PIO0_22": "USB0_VBUS_S",
    "PIO0_2": "LED_R", "PIO0_3": "LED_G", "PIO1_31": "LED_B", "PIO1_27": "USER_BTN",
}
MCU_NETS = {f"PIO{port}_{i}": NC for port in (0, 1) for i in range(32)}
MCU_NETS.update(MCU_PINS)
MCU_NETS.update({
    "VDD": "+3V3", "VBAT_DCDC": "+3V3", "VBAT_PMU": "+3V3", "USB0_3V3": "+3V3", "USB1_3V3": "+3V3",
    "USB1_VBUS": "+3V3", "VDDA": "VDDA", "VREFP": "VDDA",
    "VSS": "GND", "VSSA": "GND", "VREFN": "GND", "VSS_DCDC": "GND", "USB0_VSS": "GND", "USB1_VSS": "GND",
    "VDD_PMU": "VDD_PMU", "FB": "VDD_PMU", "LX": "DCDC_LX", "RESETN": "RESETN",
    "XTAL32M_P": "XTAL_P", "XTAL32M_N": "XTAL_N", "XTAL32K_P": "X32K_P", "XTAL32K_N": "X32K_N",
    "USB0_DP": "USB0_DP", "USB0_DM": "USB0_DM", "USB1_DP": NC, "USB1_DM": NC,
})

PARTS = [
    # ---- USB0 port (J1): USB-C, ESD, CC, fuse, series resistors, VBUS sense ---------------------------
    usb_c("J1", "USB", (40, 100), "USB0, the LPC55S69's full-speed device port"),
    res("R1", "5.1k", "USB_CC1", "GND", (75, 85), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC1, TI SLVSFJ9 section 10.3.14.2)"),
    res("R2", "5.1k", "USB_CC2", "GND", (90, 85), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC2, TI SLVSFJ9 section 10.3.14.2)"),
    esd("U1", "USB", (110, 100), swap=True),   # D+ above D- at J1, U1, R5/R6 and the LPC55S69
    fuse("F1", "VBUS_USB", "VBUS_USB_F", (140, 85)),
    res("R5", "33", "USB_C_DP", "USB0_DP", (75, 125), f"Resistor 33 ohm 1% 0402 (USB0_DP series, RS = 33 ohm, {DS} Figure 30)"),
    res("R6", "33", "USB_C_DM", "USB0_DM", (90, 125), f"Resistor 33 ohm 1% 0402 (USB0_DM series, RS = 33 ohm, {DS} Figure 30)"),
    res("R7", "4.7k", "VBUS_USB", "USB0_VBUS_S", (120, 140), f"Resistor 4.7 kohm 1% 0402 (USB0_VBUS divider: 5.5 V reads 3.25 V, under 3.6 V, {DS} section 13.5)", rot=90),
    res("R8", "6.8k", "USB0_VBUS_S", "GND", (120, 155), f"Resistor 6.8 kohm 1% 0402 (USB0_VBUS divider: 4.4 V reads 2.43 V with the 40 kohm pull-down, {DS} Table 24)", rot=90),

    # ---- Debug port (J2): USB-C, ESD, CC, fuse, VBUS bleed --------------------------------------------
    usb_c("J2", "DBG", (40, 200), "debug UART (CP2102N)"),
    res("R3", "5.1k", "DBG_CC1", "GND", (75, 185), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC1, TI SLVSFJ9 section 10.3.14.2)"),
    res("R4", "5.1k", "DBG_CC2", "GND", (90, 185), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC2, TI SLVSFJ9 section 10.3.14.2)"),
    esd("U2", "DBG", (110, 200), swap=True),   # D+ above D- at both U2 and the CP2102N
    fuse("F2", "VBUS_DBG", "VBUS_DBG_F", (140, 185)),
    res("R11", "5.1k", "VBUS_DBG", "GND", (75, 225), f"Resistor 5.1 kohm 1% 0402 (VBUS bleed: with the divider 4.75 kohm, so 185 uA of leakage keeps the CP2102N VBUS pin under VIL 0.6 V, {CP} Table 3.7)", rot=90),

    # ---- Power mux (debug port first), 3.3 V LDO with soft start, power LED ------------------------------
    Part("U3", "Power_Management:TPS2116DRL", "TPS2116", "Package_TO_SOT_SMD:SOT-583-8", (200, 100),
         {"VIN1": "VBUS_DBG_F", "VIN2": "VBUS_USB_F", "VOUT": "+5V", "GND": "GND", "PR1": "MUX_PR1",
          "MODE": "VBUS_DBG_F", "ST": NC},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPS2116DRLR",
                 "Description": "Power mux 2.5 A, priority mode: VIN1 (debug port) first, VIN2 (USB0) otherwise, reverse blocking (TI SLVSFG1A)"}),
    res("R12", "27k", "VBUS_DBG_F", "MUX_PR1", (170, 125), "Resistor 27 kohm 1% 0402 (TPS2116 PR1 divider: VIN1 kept down to 3.7 x VREF = 3.40-4.00 V, above 3.283 V + TPS7A91 dropout, below 4.40 V less F2; TI SLVSFG1A 7.6.1.1, SBVS282A 5.5)", rot=90),
    res("R13", "10k", "MUX_PR1", "GND", (170, 140), "Resistor 10 kohm 1% 0402 (TPS2116 PR1 divider, VREF 0.92-1.08 V, TI SLVSFG1A Table 6.5)", rot=90),
    cap("C1", "1u", "VBUS_DBG_F", "GND", (175, 85), "Capacitor 1 uF 10 V X7R 0402 (TPS2116 VIN1, TI SLVSFG1A section 9)"),
    cap("C2", "1u", "VBUS_USB_F", "GND", (190, 85), "Capacitor 1 uF 10 V X7R 0402 (TPS2116 VIN2, TI SLVSFG1A section 9)"),
    cap("C3", "100u", "+5V", "GND", (230, 85), "Capacitor 100 uF 10 V X5R 1210 (TPS2116 VOUT, about 100 uF where reverse blocking can occur, TI SLVSFG1A 7.3.4)", C1210, mpn=("Murata", "GRM32ER61A107ME20L")),
    Part("U4", "Regulator_Linear:TPS7A91", "TPS7A91", "Package_DFN_QFN:Texas_S-PDSO-N10_EP1.2x2mm", (280, 105),
         {"IN": "+5V", "EN": "+5V", "SS_CTRL": "GND", "NR/SS": "LDO_NR", "FB": "LDO_FB", "OUT": "+3V3",
          "PG": NC, "GND": "GND"},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPS7A9101DSKR",
                 "Description": "LDO 1 A, adjustable, NR/SS soft start: 3.283 V, ramp 4.2-9.4 ms (TI SBVS282A)"}),
    cap("C4", "22u", "+5V", "GND", (250, 85), "Capacitor 22 uF 10 V X5R 0805 (TPS7A91 input, 10 uF or more, TI SBVS282A 5.3; about 8.0 uF left at 5 V and 7.3 uF at 5.5 V by Murata's DC-bias curve, above the 5 uF that 7.1.3's 50 % derating implies)", C0805, mpn=C22U),
    cap("C5", "10u", "+3V3", "GND", (310, 85), "Capacitor 10 uF 16 V X5R 0805 (TPS7A91 output, 10 uF or more, TI SBVS282A 5.3 and 7.1.3)", C0805, mpn=C10U_0805),
    cap("C6", "47n", "LDO_NR", "GND", (255, 130), "Capacitor 47 nF X7R 0402 (TPS7A91 NR/SS: tSS = 0.8 V x 47 nF / 4.0-9.0 uA = 4.2-9.4 ms, TI SBVS282A Eq. 6; NXP DS Table 25 asks >= 2.6 ms)", mpn=("Murata", "GRM155R71C473KA01D")),
    res("R14", "3.57k", "+3V3", "LDO_FB", (305, 120), "Resistor 3.57 kohm 0.1% 0402 (TPS7A91 R1, 3.283 V, TI SBVS282A Table 7-1)", rot=90),
    res("R15", "1.15k", "LDO_FB", "GND", (305, 140), "Resistor 1.15 kohm 0.1% 0402 (TPS7A91 R2, 3.283 V, TI SBVS282A Table 7-1)", rot=90),
    res("R16", "680", "+3V3", "LED_PWR_A", (335, 100), "Resistor 680 ohm 1% 0402 (power LED: (3.3 V - 1.9 V) / 680 ohm = 2.1 mA, Kingbright DSAO7432)"),
    Part("D1", "Device:LED_Small", "PWR", "LED_SMD:LED_0603_1608Metric", (350, 100), {"A": "LED_PWR_A", "K": "GND"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LCGCK", "Description": "LED green 0603, VF 1.9 V typ at 2 mA (DSAO7432): power (3.3 V)"}),

    # ---- Debug UART: CP2102N on the board's 3.3 V, VBUS sense from the debug port -----------------------------
    Part("U5", "Interface_USB:CP2102N-Axx-xQFN24", "CP2102N-A02-GQFN24", "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm",
         (150, 260), {"GND": "GND", "D+": "DBG_C_DP", "D-": "DBG_C_DM", "VIO": "+3V3", "VDD": "+3V3", "VREGIN": "+3V3",
                      "VBUS": "CP_VBUS", "~{RST}": "CP_RST", "RXD": "FC0_TXD", "TXD": "FC0_RXD",
                      **{p: NC for p in ("NC", "~{RI}/CLK", "~{WAKEUP}/GPIO.3", "RS485/GPIO.2", "~{RXT}/GPIO.1",
                                         "~{TXT}/GPIO.0", "~{SUSPEND}", "SUSPEND", "~{CTS}", "~{RTS}", "~{DSR}",
                                         "~{DTR}", "~{DCD}")}},
         fields={"Manufacturer": "Silicon Labs", "MPN": "CP2102N-A02-GQFN24R",
                 "Description": f"USB-UART bridge on FLEXCOMM0, from the board's 3.3 V, own regulator unused ({CP} Figure 2.3)"}),
    cap("C7", "4.7u", "+3V3", "GND", (195, 235), f"Capacitor 4.7 uF 10 V X5R 0603 (CP2102N VREGIN/VDD, {CP} Figure 2.3)", C0603, mpn=C4U7),
    cap("C8", "100n", "+3V3", "GND", (210, 235), f"Capacitor 100 nF X7R 0402 (CP2102N VREGIN pin 7, beside the pin, {CP} Figure 2.3)", mpn=C100N),
    cap("C9", "4.7u", "+3V3", "GND", (225, 235), f"Capacitor 4.7 uF 10 V X5R 0603 (CP2102N VIO, {CP} section 2.1)", C0603, mpn=C4U7),
    cap("C10", "100n", "+3V3", "GND", (240, 235), f"Capacitor 100 nF X7R 0402 (CP2102N VIO/VDD pins 5 and 6, beside the pins, {CP} Figure 2.3)", mpn=C100N),
    res("R17", "1k", "CP_RST", "+3V3", (195, 280), f"Resistor 1 kohm 1% 0402 (CP2102N RSTb pull-up, {CP} section 2.1)"),
    res("R9", "22.1k", "VBUS_DBG", "CP_VBUS", (100, 245), f"Resistor 22.1 kohm 1% 0402 (CP2102N VBUS divider: 5 V reads 3.41 V, {CP} Figure 2.6)", rot=90),
    res("R10", "47.5k", "CP_VBUS", "GND", (100, 265), f"Resistor 47.5 kohm 1% 0402 (CP2102N VBUS divider, {CP} Figure 2.6)", rot=90),

    # ---- LPC55S69 ------------------------------------------------------------------------------------------
    Part("U6", "EoS_MCU:LPC55S69JBD100", "LPC55S69JBD100", "EoS_Packages:HLQFP-100-1EP_14x14mm_P0.5mm_EP3.21x3.21mm",
         (420, 230), MCU_NETS,
         fields={"Manufacturer": "NXP", "MPN": "LPC55S69JBD100K",
                 "Description": f"Dual Cortex-M33 MCU, 640 KB flash, 320 KB SRAM, HLQFP-100, exposed pad = VSS ({DS} Table 3)"}),
    *[cap(f"C{11 + i}", "100n", "+3V3", "GND", (330 + 12.7 * i, 160), f"Capacitor 100 nF X7R 0402 (VDD pin {pin}, {AN} Table 6)", mpn=C100N)
      for i, pin in enumerate((15, 25, 44, 63, 69, 75, 84, 95, 100))],
    cap("C20", "10u", "+3V3", "GND", (450, 160), f"Capacitor 10 uF 10 V X5R 0603 (VDD domain bulk, {AN} Table 6)", C0603, mpn=C10U_0603),
    cap("C21", "100n", "+3V3", "GND", (465, 160), f"Capacitor 100 nF X7R 0402 (USB0_3V3 pin 96, {AN} Table 6)", mpn=C100N),
    cap("C22", "10u", "+3V3", "GND", (480, 160), f"Capacitor 10 uF 10 V X5R 0603 (USB0_3V3 bulk, {AN} Table 6)", C0603, mpn=C10U_0603),
    cap("C23", "100n", "+3V3", "GND", (495, 160), f"Capacitor 100 nF X7R 0402 (USB1_3V3 pin 38, {AN} Table 6)", mpn=C100N),
    cap("C24", "10u", "+3V3", "GND", (510, 160), f"Capacitor 10 uF 10 V X5R 0603 (USB1_3V3 bulk, {AN} Table 6)", C0603, mpn=C10U_0603),
    Part("FB1", "Device:FerriteBead_Small", "220R", "Inductor_SMD:L_0603_1608Metric", (330, 300), {"1": "+3V3", "2": "VDDA"},
         fields={"Manufacturer": "Bourns", "MPN": "MH1608-221Y",
                 "Description": "Ferrite bead 220 ohm at 100 MHz, 100 mohm, 2 A, 0603: VDDA/VREFP filter (Bourns MH1608)"}),
    cap("C25", "100n", "VDDA", "GND", (350, 315), f"Capacitor 100 nF X7R 0402 (VDDA pin 16, {AN} Table 6)", mpn=C100N),
    cap("C26", "10u", "VDDA", "GND", (365, 315), f"Capacitor 10 uF 10 V X5R 0603 (VDDA bulk, {AN} Table 6)", C0603, mpn=C10U_0603),
    cap("C27", "100n", "VDDA", "GND", (380, 315), f"Capacitor 100 nF X7R 0402 (VREFP pin 17, {AN} Table 6 and Figure 2 C20)", mpn=C100N),
    cap("C28", "10u", "VDDA", "GND", (395, 315), f"Capacitor 10 uF 10 V X5R 0603 (VREFP bulk, {AN} Table 6)", C0603, mpn=C10U_0603),
    cap("C29", "22u", "+3V3", "GND", (500, 300), f"Capacitor 22 uF 10 V X5R 0805 (VBAT_DCDC, {DS} Figure 6 C2)", C0805, mpn=C22U),
    cap("C30", "100n", "+3V3", "GND", (515, 300), f"Capacitor 100 nF X7R 0402 (VBAT_DCDC pins 49/50, {DS} Figure 6 C3)", mpn=C100N),
    cap("C31", "47p", "+3V3", "GND", (530, 300), f"Capacitor 47 pF C0G 0402 (VBAT_DCDC, {DS} Figure 6 C4)", mpn=("Murata", "GRM1555C1H470JA01D")),
    cap("C32", "100n", "+3V3", "GND", (545, 300), f"Capacitor 100 nF X7R 0402 (VBAT_PMU pin 51, {AN} Figure 2 C27)", mpn=C100N),
    Part("L1", "Device:L_Small", "4.7u", "Inductor_SMD:L_Bourns-SRN4018", (500, 340), {"1": "DCDC_LX", "2": "VDD_PMU"},
         fields={"Manufacturer": "Bourns", "MPN": "SRN4018-4R7M",
                 "Description": f"Inductor 4.7 uH, 84 mohm, Isat 2.0 A, Irms 1.9 A: DC-DC LX ({DS} Figure 6 L1; Bourns SRN4018)"}),
    cap("C33", "22u", "VDD_PMU", "GND", (520, 355), f"Capacitor 22 uF 10 V X5R 0805 (DC-DC output at FB, {DS} Figure 6 C1)", C0805, mpn=C22U),
    cap("C34", "100n", "VDD_PMU", "GND", (535, 355), f"Capacitor 100 nF X7R 0402 (VDD_PMU pin 39, {AN} Figure 2 C12)", mpn=C100N),
    # 16 MHz and 32.768 kHz crystals: the chip's capacitor banks are the load; the pads stay DNP (AN13033 4.1)
    Part("Y1", "Device:Crystal_GND24", "16MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", (560, 200),
         {"1": "XTAL_P", "3": "XTAL_N", "2": "GND", "4": "GND"},
         fields={"Manufacturer": "ECS Inc.", "MPN": "ECS-160-8-33Q-JES-TR",
                 "Description": f"Crystal 16 MHz, CL 8 pF, ESR 80 ohm max, 3.2 x 2.5 mm (ECS ECX-33Q); CL in the 6-10 pF cap-bank range, {DS} 13.3"}),
    cap("C35", "11p", "XTAL_P", "GND", (545, 225), f"Capacitor 11 pF C0G 0402, DNP (XTAL32M_P: 2 x 8 pF - (3 + 2) pF, {AN} 4.2; internal cap bank used, {AN} 4.1)", dnp=True),
    cap("C36", "11p", "XTAL_N", "GND", (575, 225), f"Capacitor 11 pF C0G 0402, DNP (XTAL32M_N: 2 x 8 pF - (3 + 2) pF, {AN} 4.2; internal cap bank used, {AN} 4.1)", dnp=True),
    Part("Y2", "Device:Crystal", "32.768kHz", "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm", (560, 260), {"1": "X32K_P", "2": "X32K_N"},
         fields={"Manufacturer": "Abracon", "MPN": "ABS07-32.768KHZ-7-T",
                 "Description": f"Crystal 32.768 kHz, CL 7 pF, ESR 70 kohm max, 3.2 x 1.5 mm (Abracon ABS07); CL in the cap-bank range, {DS} 13.4"}),
    cap("C37", "9p", "X32K_P", "GND", (545, 280), f"Capacitor 9 pF C0G 0402, DNP (XTAL32K_P: 2 x 7 pF - (3 + 2) pF, {AN} 4.3; internal cap bank used, {AN} 4.1)", dnp=True),
    cap("C38", "9p", "X32K_N", "GND", (575, 280), f"Capacitor 9 pF C0G 0402, DNP (XTAL32K_N: 2 x 7 pF - (3 + 2) pF, {AN} 4.3; internal cap bank used, {AN} 4.1)", dnp=True),

    # ---- Reset, ISP, SWD, user button ----------------------------------------------------------------------
    Part("J3", "Connector:Conn_ARM_JTAG_SWD_10", "Cortex Debug", "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD",
         (330, 400), {"VTref": "+3V3", "SWDIO/TMS": "SWDIO", "GND": "GND", "SWCLK/TCK": "SWCLK", "SWO/TDO": "SWO",
                      "KEY": NC, "NC/TDI": NC, "GNDDetect": "GND", "~{RESET}": "RESETN"},
         fields={"Manufacturer": "Samtec", "MPN": "FTSH-105-01-L-DV-K",
                 "Description": f"Arm Cortex Debug 10-pin, 1.27 mm: SWD in place of a vendor debug probe ({AN} Figure 8)"}),
    res("R18", "10k", "SWDIO", "+3V3", (290, 375), f"Resistor 10 kohm 1% 0402 (SWDIO pull-up, {AN} Figure 7)", rot=90),
    res("R19", "10k", "SWO", "+3V3", (275, 375), f"Resistor 10 kohm 1% 0402 (SWO pull-up, {AN} Figure 7)", rot=90),
    res("R20", "10k", "RESETN", "+3V3", (260, 375), f"Resistor 10 kohm 1% 0402 (RESETN pull-up, {AN} Figure 7)", rot=90),
    res("R21", "10k", "SWCLK", "GND", (305, 375), f"Resistor 10 kohm 1% 0402 (SWCLK pull-down, {AN} Figure 7)", rot=90),
    button("SW1", "RESET", "RESETN", (240, 400), "reset (RESETN)"),
    button("SW2", "ISP", "ISP_N", (240, 430), "ISP: PIO0_5 low at reset enters ISP boot (NXP UM11126 Table 167)"),
    button("SW3", "USER", "USER_BTN", (240, 460), "user (PIO1_27)"),
    res("R22", "10k", "USER_BTN", "+3V3", (220, 445), "Resistor 10 kohm 1% 0402 (user button pull-up, as AN13033 Figure 7's 10 kohm; internal pull-ups are off at reset)", rot=90),

    # ---- RGB LED: common anode on 5 V, one low-side switch per colour ------------------------------------------
    Part("D2", "Device:LED_RGBA", "RGB", "LED_SMD:LED_LiteOn_LTST-C19HE1WT", (130, 400),
         {"A": "+5V", "RK": "RGB_RK", "GK": "RGB_GK", "BK": "RGB_BK"},
         fields={"Manufacturer": "LiteOn", "MPN": "LTST-C19HE1WT",
                 "Description": "LED RGB 1.6 x 1.6 mm, common anode (pin 4), cathodes R 1, G 2, B 3 (LiteOn DS22-2008-0044)"}),
    res("R25", "560", "RGB_RK", "RGB_RD", (100, 370), "Resistor 560 ohm 1% 0402 (red: (5 V - 2.15 V) / 560 ohm = 5.1 mA, LiteOn DS22-2008-0044 Fig. 2)", rot=90),
    res("R26", "470", "RGB_GK", "RGB_GD", (100, 400), "Resistor 470 ohm 1% 0402 (green: (5 V - 2.75 V) / 470 ohm = 4.8 mA, LiteOn DS22-2008-0044 Fig. 2)", rot=90),
    res("R27", "470", "RGB_BK", "RGB_BD", (100, 430), "Resistor 470 ohm 1% 0402 (blue: (5 V - 2.75 V) / 470 ohm = 4.8 mA, LiteOn DS22-2008-0044 Fig. 2)", rot=90),
    *[Part(f"Q{i + 1}", "Transistor_FET:BSS138", "BSS138BK", "Package_TO_SOT_SMD:SOT-23", (60, 370 + 30 * i),
           {"G": f"LED_{c}", "S": "GND", "D": f"RGB_{c}D"},
           fields={"Manufacturer": "Nexperia", "MPN": "BSS138BK,215",
                   "Description": f"N-MOSFET, {name} cathode switch: RDSon <= 6.5 ohm at VGS 2.5 V (Nexperia BSS138BK Rev. 1)"})
      for i, (c, name) in enumerate((("R", "red"), ("G", "green"), ("B", "blue")))],
    *[res(f"R{28 + i}", "100k", f"LED_{c}", "GND", (35, 370 + 30 * i), f"Resistor 100 kohm 1% 0402 ({c} gate held off while the pin is high-impedance after reset)", rot=90)
      for i, c in enumerate("RGB")],

    # ---- I2C pull-ups, shield headers -------------------------------------------------------------------------
    res("R23", "2.2k", "SDA", "+3V3", (480, 400), "Resistor 2.2 kohm 1% 0402 (SDA pull-up: RP(min) 0.97 kohm, fast mode to 161 pF, TI SLVA689A Eq. 1 and 6)", rot=90),
    res("R24", "2.2k", "SCL", "+3V3", (495, 400), "Resistor 2.2 kohm 1% 0402 (SCL pull-up: RP(min) 0.97 kohm, fast mode to 161 pF, TI SLVA689A Eq. 1 and 6)", rot=90),
    socket("J5", 8, "D0-D7", ["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7"], (560, 330),
           "Socket 1x8 2.54 mm, Uno R3 digital D0-D7 (pin 1 = D0), 3.3 V logic"),
    socket("J4", 10, "D8-SCL", ["D8", "D9", "D10", "D11", "D12", "D13", "GND", NC, "SDA", "SCL"], (560, 390),
           "Socket 1x10 2.54 mm, Uno R3 digital D8-D13, GND, AREF (not connected), SDA, SCL (pin 1 = D8)"),
    socket("J6", 8, "POWER", [NC, "+3V3", "RESETN", "+3V3", "+5V", "GND", "GND", NC], (520, 450),
           "Socket 1x8 2.54 mm, Uno R3 power: NC, IOREF (3.3 V), RESET, 3V3, 5V, GND, GND, VIN (not connected)"),
    socket("J7", 6, "A0-A5", ["A0", "A1", "A2", "A3", "A4", "A5"], (560, 450),
           "Socket 1x6 2.54 mm, Uno R3 analog A0-A5 (pin 1 = A0), 0-3.3 V"),
]
for i, (label, src) in enumerate([("top left", "Arduino A000066 section 5.4"),
                                  ("bottom left", "height from Arduino A000066 section 5.4, x from Beckler's drawing v1.05"),
                                  ("right, upper", "Arduino A000066 section 5.4"),
                                  ("right, lower", "Arduino A000066 section 5.4")]):
    PARTS.append(Part(f"H{i + 1}", "Mechanical:MountingHole", "M3", HOLE, (60 + 20 * i, 470), {},
                      side="B" if i == 0 else "F",
                      fields={"Description": f"Mounting hole 3.2 mm (A000066 section 5.4), unplated, Uno R3 position ({label}: {src})"}))

# Board placement: (x, y, rotation) in mm, origin top-left. The MCU sits in the middle, turned
# 90 degrees so that its PIO0_0..PIO1_26 side faces the digital header, its ADC side faces the
# analog header, its USB0/UART side faces the two USB-C ports on the left edge and its DC-DC and
# crystal side faces the free right-hand side. Decoupling sits 1 mm beyond the chip's courtyard,
# in line with each supply pin.
MX, MY = 36.0, 24.0


def pin_xy(p):
    """Where LPC55S69 pin p lands with the chip at (MX, MY), rotated 90 degrees."""
    if p <= 25:
        return MX - 6.0 + 0.5 * (p - 1), MY + 7.775
    if p <= 50:
        return MX + 7.775, MY + 6.0 - 0.5 * (p - 26)
    if p <= 75:
        return MX + 6.0 - 0.5 * (p - 51), MY - 7.775
    return MX - 7.775, MY - 6.0 + 0.5 * (p - 76)


RING = 10.7     # cap centre from the chip centre: courtyard (8.75) + 1 mm + half a cap
PLACEMENT = {
    "U6": (MX, MY, 90),
    "J5": (D0_PIN[0], D0_PIN[1], 270), "J4": (D8_PIN[0], D8_PIN[1], 270),
    "J6": (POWER_PIN[0], POWER_PIN[1], 90), "J7": (A0_PIN[0], A0_PIN[1], 90),
    **{f"H{i + 1}": (x, y, 0) for i, (x, y) in enumerate(HOLES)},
    # decoupling in line with its pin: top and bottom rows vertical, left and right rows horizontal
    "C14": (pin_xy(63)[0], MY - RING, 90), "C15": (pin_xy(69)[0], MY - RING, 90), "C16": (pin_xy(75)[0], MY - RING, 90),
    # VBAT_PMU's capacitor up and to the right of pin 51, so that XTAL32K_P (pin 52) goes straight up to Y2
    "C32": (43.3, 13.8, 90),
    # VDDA and VREFP: each 100 nF turned so its VDDA pad faces pins 16 and 17, a short line from each pin
    "C11": (pin_xy(15)[0] - 0.6, MY + RING, 90), "C25": (pin_xy(16)[0] + 0.25, MY + RING, 270),
    "C27": (pin_xy(17)[0] + 0.9, MY + RING, 270), "C12": (pin_xy(25)[0], MY + RING, 90),
    "C17": (MX - RING, pin_xy(84)[1], 0), "C18": (MX - RING, pin_xy(95)[1] - 0.1, 0),
    "C19": (MX - RING, pin_xy(100)[1] + 0.3, 0), "C21": (MX - RING, pin_xy(100)[1] + 1.5, 0),
    "C13": (MX + RING, pin_xy(44)[1], 0), "C34": (MX + RING + 0.3, pin_xy(39)[1], 0),
    "C23": (MX + RING, pin_xy(38)[1] + 1.7, 0), "C24": (49.5, 25.7, 0), "C20": (24.6, 14.6, 0),
    "C22": (24.6, 33.6, 0),
    # DC-DC (right of pins 45-51): VBAT_DCDC capacitors at the pins, then the LX inductor and its output capacitor
    "C29": (47.0, 13.8, 90), "C31": (MX + RING, 17.0, 0), "C30": (MX + RING, 18.2, 0),
    "L1": (50.6, 18.6, 0), "C33": (54.6, 18.6, 90),
    # crystals: 16 MHz beside XTAL32M (pins 28/29), 32.768 kHz above XTAL32K (pins 52/53). Y1 is turned
    # 180 degrees so its XTAL_P pad is the upper one and XTAL_N the lower one, as pins 29 and 28 are, and
    # the two lines never cross; each DNP load pad sits beyond its crystal pad, reached last
    "Y1": (50.0, 29.6, 180), "C35": (53.2, 28.4, 90), "C36": (48.9, 32.6, 270), "R20": (MX + RING, 26.9, 0),
    "Y2": (44.2, 9.6, 0), "C37": (47.3, 8.6, 90), "C38": (42.95, 7.4, 0),
    # VDDA / VREFP filter, second row below the chip
    "FB1": (38.0, 37.6, 90), "C26": (39.8, 37.6, 90), "C28": (41.6, 37.6, 90),
    # debug port (J2), its ESD and CC resistors, fuse, CP2102N with its capacitors and VBUS divider and bleed.
    # J2 and U2 sit level with the CP2102N's D+/D- pins, so the pair runs straight from the receptacle
    # through U2 (between its pad rows) to pins 3 and 4
    "J2": (USB_C_EDGE, 9.0, 270), "U2": (11.6, 9.0, 90), "R3": (11.3, 5.4, 0), "R4": (11.3, 12.6, 0),
    # each 0.1 uF beside its pins: C10 at the corner by VIO/VDD (pins 5, 6), C8 under VREGIN (pin 7);
    # under pins 8 and 9 the RST pull-up and the VBUS divider, whose middle node is right under pin 8
    "F2": (11.8, 17.6, 0), "U5": (18.5, 9.0, 0), "R17": (19.1, 12.7, 270),
    "C7": (21.5, 12.6, 0), "C9": (21.5, 14.2, 0), "C8": (16.95, 12.65, 270), "C10": (15.3, 11.75, 270),
    "R9": (16.9, 14.4, 0), "R10": (18.9, 14.4, 0), "R11": (14.6, 13.8, 90),
    # power mux: VIN1 and PR1 leave upwards (to F2, C1 and the PR1 divider), VIN2 downwards (C2,
    # then F1), and the two VOUT pins face each other across the package (see PRIORITY). MODE goes
    # round the left end to R12's VBUS end, so the PR1 node sits inside that loop, with room in it
    # for R13's ground via (above R13, clear of R12 and of U3's pins).
    "U3": (13.0, 22.5, 270), "C1": (14.2, 20.0, 0), "C2": (12.75, 25.0, 270),
    "R12": (9.6, 20.2, 0), "R13": (11.15, 21.6, 90), "C3": (16.6, 24.6, 0),
    # LDO in the clear space below the USB0 lines: IN and NR/EN to the right, OUT and FB to the left
    "U4": (19.5, 37.0, 0), "C4": (21.3, 33.6, 90), "C5": (16.4, 34.6, 90), "C6": (22.6, 37.0, 0),
    "R14": (15.6, 37.0, 0), "R15": (16.11, 38.5, 270), "D1": (17.0, 16.8, 180), "R16": (20.5, 16.8, 0),
    # USB0 port (J1), ESD, CC resistors, fuse; series resistors and VBUS divider near the chip's pins.
    # J1 and U1 sit level with R5/R6 and pins 97/98, so the pair runs straight across: receptacle,
    # U1 (between its pad rows), R5/R6, chip. CC1's resistor is above the pair and CC2's below it.
    "J1": (USB_C_EDGE, 29.0, 270), "U1": (11.6, 29.0, 90), "R1": (9.75, 25.75, 90), "R2": (11.3, 32.6, 0),
    "F1": (11.8, 35.8, 0),
    "R5": (22.6, 28.4, 0), "R6": (22.6, 29.5, 0), "R7": (22.6, 18.6, 0), "R8": (22.6, 17.4, 0),
    # buttons, RGB LED with its switches, SWD header and pull-ups
    "SW1": (4.0, 42.6, 0), "SW2": (4.0, 47.2, 0), "SW3": (10.0, 44.6, 0), "R22": (10.0, 41.9, 0),
    "D2": (15.2, 42.2, 0), "R25": (15.2, 44.5, 0), "R26": (15.2, 45.7, 0), "R27": (15.2, 46.9, 0),
    "Q1": (19.4, 42.4, 0), "Q2": (19.4, 46.2, 0), "Q3": (23.8, 46.2, 0),
    "R28": (22.5, 42.0, 90), "R29": (23.8, 42.0, 90), "R30": (25.1, 42.0, 90),
    "J3": (31.0, 41.0, 0), "R18": (29.0, 46.5, 0), "R19": (31.2, 46.5, 0), "R21": (33.4, 46.5, 0),
    # I2C pull-ups by the SDA/SCL header pins
    "R23": (23.5, 6.5, 90), "R24": (24.6, 6.5, 90),
}
# Laid before the autorouter, in this order, and locked (pcb_build.py), before the plane fan-out
# puts vias beside the pins these lines use.
# * Both USB pairs, whole, on the top layer: receptacle contact, ESD pad, then on to the chip, so
#   each line runs through its ESD pad with no stub, and nothing is left to the autorouter (which
#   sent the debug D+ 30 mm round J2's shell). D+ is the upper line at every part of both pairs
#   (receptacle A6 above A7, ESD pad 3 above pad 2, CP2102N pin 3 above pin 4, R5 above R6, pin 97
#   above pin 98), so the two never cross. D- goes first each time: at each ESD part the lines part
#   (D+ up to pad 3, D- down to pad 2) and the lower one laid first leaves the upper one its way.
#   The maze lays a line straight from its first end and turns near its second, so each leg is
#   laid from its closely spaced end (the receptacle's 0.5 mm contacts, the CP2102N's and the
#   LPC55S69's 0.5 mm pins, R5/R6) towards the ESD part, whose pads are 2 mm apart: the pair stays
#   together and parts only at the ESD part.
# * Then the receptacle's second contacts. The HRO pads run B7 (D-), A6 (D+), A7 (D-), B6 (D+): with
#   A6 and A7 carrying the pair, B7 sits above D+ and B6 below D-, so one of the two ties has to
#   cross the pair. B7 joins D- first, behind A6 (the short way round A6's back end, 0.3 mm behind
#   the pad row, as EoS TM4C123's A6 tie does), which leaves B6 the only way left: a via pair in
#   front of the pads, under both lines on the bottom layer, up onto D+.
# * VOUT to VOUT through the TPS2116's body; MODE round its left end to R12's VBUS end, then on to
#   the fuse; the LDO's FB line, and its EN to its IN pins, before NR/SS's capacitor is reached from
#   inside that loop.
# * The crystals: each lower line first (XTAL_N, then XTAL_P over Y1's GND pad; XTAL32K_N, then
#   XTAL32K_P beside it), chip to crystal pad, then crystal pad to its DNP load pad, so the load pad
#   is last on the line (AN13033 4.2.1, 4.3.1: short, and not crossing other lines).
# * VDDA and VREFP to their 100 nF (C25's line laid from the capacitor, so it rises at C25's x and
#   leaves pin 15 room for its plane via), VDD_PMU (pin 39) to its 100 nF, VDD pin 44 to its 100 nF,
#   and FB (pin 45) to the DC-DC output capacitor C33 (DS Figure 6), past pin 44's line. The GND pins
#   these lines shut in (18 behind VREFP's line, 46 behind FB's) join their GND neighbours.
# * The CP2102N: VIO/VDD pin 6 and VREGIN pin 7 straight to their own 0.1 uF, and GND pin 2 to the
#   exposed pad, since D+ now passes in front of it.
PRIORITY = [(("J2", "A7"), ("U2", "2")), (("J2", "A6"), ("U2", "3")),
            (("U5", "4"), ("U2", "2")), (("U5", "3"), ("U2", "3")),
            (("J2", "B7"), ("J2", "A7"), "join"), (("J2", "B6"), ("J2", "A6"), "join"),
            (("J1", "A7"), ("U1", "2")), (("J1", "A6"), ("U1", "3")),
            (("R6", "1"), ("U1", "2")), (("R5", "1"), ("U1", "3")),
            (("U6", "98"), ("R6", "2")), (("U6", "97"), ("R5", "2")),
            (("J1", "B7"), ("J1", "A7"), "join"), (("J1", "B6"), ("J1", "A6"), "join"),
            (("U4", "3"), ("R14", "2")),
            (("U3", "2"), ("U3", "7")), (("U3", "5"), ("R12", "1")), (("R12", "1"), ("F2", "2")),
            # The PR1 divider node: the autorouter left it open twice once no via may sit in a pad
            # (2026-10-20 rebuilds), so PR1 goes to R13 and R13 to R12 here.
            (("U3", "4"), ("R13", "1")), (("R13", "1"), ("R12", "2")),
            (("U4", "7"), ("U4", "9"), "join"),
            (("U6", "28"), ("Y1", "3")), (("U6", "29"), ("Y1", "1")),
            (("Y1", "3"), ("C36", "1")), (("Y1", "1"), ("C35", "1")),
            (("U6", "53"), ("Y2", "2")), (("U6", "52"), ("Y2", "1")),
            (("Y2", "2"), ("C38", "1")), (("Y2", "1"), ("C37", "1")),
            (("C25", "1"), ("U6", "16")), (("U6", "17"), ("C27", "1")),
            (("U6", "39"), ("C34", "1")), (("U6", "44"), ("C13", "1")), (("U6", "45"), ("C33", "1")),
            (("U6", "18"), ("U6", "19"), "join"), (("U6", "46"), ("U6", "47"), "join"),
            (("U5", "6"), ("C10", "1")), (("U5", "7"), ("C8", "1")), (("U5", "2"), ("U5", "25"))]

_unplaced = sorted({p.ref for p in PARTS} - set(PLACEMENT))
assert not _unplaced, f"parts without a board position: {_unplaced}"
for _p in PARTS:
    _p.pcb = PLACEMENT[_p.ref]

TEXTS = [
    {"text": "EoS LPC55S69 Board  rev A", "x": 36.0, "y": 40.0, "size": 1.0, "layer": "B_SilkS", "bold": True, "mirror": True},
    {"text": "(c) 2026 Kartikeydheer Srivastava", "x": 36.0, "y": 42.0, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    {"text": "All rights reserved", "x": 36.0, "y": 43.4, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    # front, 1.0 mm text: which USB-C is which (between the two receptacles) and what each button does
    {"text": "DEBUG", "x": 3.6, "y": 15.4, "size": 1.0},
    {"text": "USB", "x": 3.6, "y": 22.6, "size": 1.0},
    {"text": "RESET", "x": 4.0, "y": 39.9, "size": 1.0},
    {"text": "ISP", "x": 4.0, "y": 50.0, "size": 1.0},
    {"text": "USER", "x": 9.6, "y": 47.3, "size": 1.0},
]

BOARD = Board(
    name="eos-lpc55s69-board",
    title="EoS LPC55S69 Board",
    revision="A",
    date="2026-10-12",
    company=OWNER,
    licence=LICENCE,
    contact=CONTACT,
    licence_terms=LICENCE_TERMS,
    credits=["Uno R3 outline (2700 x 2100 mil) and shield header positions: Matthew Beckler, \"Arduino Uno R3\" dimension "
             "drawing v1.05, Wayne and Layne, public domain (wayneandlayne.com/files/common/arduino_uno_drawing.svg); "
             "facts only, no file copied",
             "Uno R3 mounting holes, 3.20 mm, centres (x, y) in mm from the top-left corner: (15.24, 2.54), (66.04, 17.78), "
             "(66.04, 45.72) and the bottom-left hole's y of 50.80 from Arduino's UNO R3 product reference manual (SKU A000066), "
             "section 5.4 (docs.arduino.cc/resources/datasheets/A000066-datasheet.pdf); the bottom-left hole's x of 13.97 "
             "(550 mil) from Beckler's drawing above; facts only"],
    width=W,
    height=H,
    corner_radius=1.0,
    thickness=1.6,
    layers=4,
    planes=[("GND", "In1.Cu"), ("+3V3", "In2.Cu")],
    fanout_avoid=[(MX, MY)],
    local_footprints=["EoS_Packages"],
    parts=PARTS,
    priority_routes=PRIORITY,
    # R13's ground end sits inside the PR1 divider's lines, and no via may sit in a pad:
    # its plane via goes in first (the 2026-10-20 rebuild left it a pour island with no via).
    fanout_first=["R13"],
    power_nets={"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V"},
    flagged_nets=["GND", "VBUS_USB_F", "VBUS_DBG_F", "VDD_PMU", "VDDA"],
    headings=[((30, 70), "USB0 port (J1) and debug port (J2): USB-C, ESD, fuses"),
              ((160, 70), "Power mux (debug port first) and 3.3 V LDO with soft start"),
              ((330, 70), "Power LED"), ((90, 215), "Debug UART: CP2102N on FLEXCOMM0"),
              ((320, 145), "LPC55S69 decoupling (AN13033 Table 6)"), ((380, 195), "LPC55S69JBD100"),
              ((480, 285), "DC-DC converter (DS Figure 6)"), ((535, 185), "Crystals (load capacitors DNP)"),
              ((320, 285), "VDDA / VREFP filter"), ((220, 355), "Reset, ISP, SWD (AN13033 section 6), user button"),
              ((30, 355), "RGB LED"), ((470, 375), "Uno R3 shield headers, I2C pull-ups"),
              ((40, 455), "Mounting holes"), ((35, 300), "Power nets")],
    power_block=(40.64, 315.0),
    notes=[((300, 490), "EoS LPC55S69 Board, rev A. Designed by Kartikeydheer Srivastava. Fits Uno R3 shields (3.3 V logic).\n"
                       "Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved; see LICENSE.txt.\n"
                       "Values from NXP LPC55S6x data sheet Rev. 2.5, AN13033 Rev. 2.1 and UM11126, TI SBVS282A (TPS7A91),\n"
                       "TI SLVSFG1A (TPS2116), Silicon Labs CP2102N Rev. 1.5, and the part data sheets named in each part.")],
    netclasses={"Power": {"track": 0.4, "clearance": 0.15}, "Supply": {"track": 0.3, "clearance": 0.15},
                "USB": {"track": 0.2, "clearance": 0.15}},
    # after the 0.5 A fuses, 0.3 mm: a 0.4 mm line cannot enter the TPS2116's and TPS7A91's 0.3 and
    # 0.25 mm pads at 0.5 mm pitch (the router needs 0.39 mm from a pad's centre line to the next pad)
    net_to_class={"VBUS_USB": "Power", "VBUS_USB_F": "Supply", "VBUS_DBG": "Power", "VBUS_DBG_F": "Supply",
                  "+5V": "Supply", "+3V3": "Supply", "DCDC_LX": "Supply", "VDD_PMU": "Supply", "VDDA": "Supply",
                  "USB_C_DP": "USB", "USB_C_DM": "USB", "USB0_DP": "USB", "USB0_DM": "USB",
                  "DBG_C_DP": "USB", "DBG_C_DM": "USB"},
)
