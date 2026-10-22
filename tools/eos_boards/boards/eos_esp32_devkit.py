"""EoS ESP32 DevKit: an ESP32-WROOM-32E development board, designed by Kartikeydheer Srivastava.

Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved: this design file is not under
the repository's MIT licence; see boards/eos/eos-esp32-devkit/LICENSE.txt.

A breadboard development board for the ESP32-WROOM-32E module: USB-C, a CP2102N USB-UART
bridge with esptool's automatic reset into the bootloader, a 1 A 3.3 V regulator, EN and BOOT
buttons, a power LED and a user LED, and every usable GPIO on two 1x19 2.54 mm headers. It does
the job of Espressif's ESP32-DevKitC V4. None of that board's design files (schematic, layout,
CAD) was opened. The only things taken from it are facts Espressif publishes for users: the
header pinout (the user guide's J2/J3 tables) and the header grid and board width (its
dimension drawing).

Every value follows a datasheet:

* ESP32-WROOM-32E (Espressif datasheet v2.1). Section 9 "Peripheral Schematics": 22 uF and
  0.1 uF on 3V3 (C1, C2 there) and an RC delay on EN, "usually R = 10 kohm and C = 1 uF".
  Table 14: the supply must deliver at least 0.5 A at 3.0-3.6 V. Table 16: Wi-Fi TX draws
  239 mA on average and 379 mA at peak (802.11b, 19.5 dBm). Table 3 note 2: GPIO6-GPIO11 are
  wired to the module's own SPI flash and are not led out; pins 17-22 are NC. So the six header
  positions where the DevKitC V4 tables put D0-D3, CMD and CLK are left unconnected here. The
  module already has a 499 ohm resistor on U0TXD (Figure 7, R3), which is what the hardware
  design guidelines ask for, so none is added. The -N4 variant has no PSRAM, so IO16 is free
  (Table 3 note 3).
* ESP32 Hardware Design Guidelines (Espressif, "Schematic Checklist"): a 3.3 V supply of at
  least 500 mA; a pull-up on GPIO0 is recommended and no large capacitor may sit on it, so IO0
  has 10 kohm and no capacitor. The internal pull-ups are 45 kohm (module Table 15), so 10 kohm
  holds IO0 high firmly. GPIO12 must be low at reset for the module's 3.3 V flash, GPIO2 low
  or floating for download mode: both go to the headers only, with nothing on board that
  pulls them. "PCB Layout Design > Positioning a Module on a Base Board" (module datasheet
  section 11.2 points to it): the PCB antenna goes outside the base board. Here the whole
  6.19 mm antenna area (land pattern, Figure 13) overhangs the top edge, 0.31 mm clear of it,
  so the footprint's antenna keep-out lies entirely off the board.
* Automatic bootloader (esptool documentation, "Boot Mode Selection > Automatic Bootloader"):
  RTS drives EN and DTR drives GPIO0 through two transistors, so that asserting both together
  resets nothing, with 1-10 uF on EN. Q1 has its base on DTR (through R10) and its emitter on
  RTS; Q2 the reverse; their collectors pull EN and IO0. RTS alone (low) resets the chip, DTR
  alone holds IO0 low, both or neither change nothing. Base resistors of 10 kohm: the CP2102N
  drives at least VIO - 0.7 V high and at most 0.6 V low (CP2102N Table 3.7), and the
  MMBT3904's VBE(sat) is at most 0.85 V (onsemi MMBT3904LT1/D Rev. 14), so the base gets at
  least 0.115 mA against a 0.33 mA collector load (10 kohm pull-up): a forced gain of about 3,
  far below the transistor's minimum hFE of 40 at 0.1 mA, so it saturates (VCE(sat) <= 0.2 V)
  and EN stays under the 0.6 V reset threshold (module Table 15). Discharging the 1 uF EN
  capacitor, Q1 passes at most hFE(max) 300 x 0.26 mA = 78 mA into the RTS pin, under the
  CP2102N's 100 mA absolute maximum (Table 3.10). The reverse-biased base-emitter junction sees
  3.3 V, under the 6 V VEBO.
* CP2102N-A02-GQFN24 (Silicon Labs data sheet Rev. 1.5). QFN-24 rather than QFN-28: it has all
  eight UART and modem lines (DTR and RTS are the ones needed), in a 4 x 4 mm package instead of
  5 x 5 mm; the QFN-28's extra pins (battery-charger detection CHR0/CHR1/CHREN and GPIO.4-6)
  have no use here. It runs from the board's 3.3 V rail with its own regulator unused
  (Figure 2.3: VREGIN tied to VDD, 3.0-3.6 V in), so it is powered whenever the ESP32 is and
  the ESP32's TX line can never back-power it. VIO is tied to VDD. "4.7 uF and 0.1 uF bypass
  capacitors required for each power pin": one pair on VREGIN/VDD (drawn as one node in
  Figure 2.3) and one on VIO. A 1 kohm pull-up from RSTb to VDD ("in all cases ... recommended",
  section 2.1). VBUS sense through the 22.1 kohm / 47.5 kohm divider of Figures 2.5 and 2.6,
  which section 2.3 requires in both bus- and self-powered designs: 5 V reads as 3.41 V, above
  VIH = VIO - 0.6 V = 2.7 V and below the VIO + 2.5 V limit. Unused inputs (CTS, DSR, DCD, RI)
  and GPIO.0-3 are left open; GPIO pins idle as inputs with a weak pull-up (section 4.3.1).
* AP7361C-33E (Diodes Inc. DS37274 Rev. 5-2): 1.0 A output, input 2.2-6.0 V, dropout 140 mV
  max at 300 mA and 340 mV typical at 1 A, so 1 A covers the module's 0.5 A requirement twice
  over. 4.7 uF on input and output, as its typical application circuit shows (at least 1 uF in
  and 2.2 uF out). At the module's 239 mA average TX current (100% duty, the worst case) plus
  the CP2102N's 9.5 mA and the two LEDs, about 253 mA, from 4.1-4.8 V (USB's 4.75-5.25 V less
  the fuse and Schottky drops) it dissipates 0.20-0.39 W: 22-43 C above ambient at the 110 C/W
  the datasheet gives for SOT-223 on its minimum pad; the board's ground pour only lowers that.
* USB-C as a 5 V sink, as on the EoS Probe S3: 5.1 kohm Rd on CC1 and CC2 (the Type-C sink
  termination, TI SLVSFJ9 section 10.3.14.2), USB 2.0 data only, SP0503BAHTG ESD
  protection on D+/D- and VBUS (diodes to ground only, CP2102N data sheet Figure 2.5), a 500 mA polyfuse (Littelfuse 1206L050:
  0.50 A hold, 1.00 A trip, 6 V, R1max 0.70 ohm). Then a PMEG6010CEH Schottky (Nexperia product
  data sheet v.4, 1 July 2023: 60 V, 1 A, VF 460 mV typical and 530 mV maximum at 500 mA) to the
  5 V rail, so 5 V fed into the header's 5V pin cannot reach the USB host. It is chosen for its
  low leakage (next point); its forward drop is higher than a 20 V part's, but from a 4.75 V port
  at a 400 mA peak the regulator still gets at least 4.75 - 0.28 - 0.53 = 3.94 V, above 3.3 V
  plus its dropout.
* VBUS bleed, R12 = 5.1 kohm from VBUS (the connector side of D1) to ground. Fed from the 5V
  pin with no host, D1 is reverse-biased by about 5 V and its leakage flows into VBUS, whose
  only other load is the CP2102N's 69.6 kohm divider. Enough leakage would lift VBUS until the
  CP2102N saw a bus that is not there. The bound: the CP2102N is guaranteed to read its VBUS pin
  as low at or below VIL = 0.6 V (data sheet Rev. 1.5 Table 3.7; it detects a bus above
  VIH = VIO - 0.6 V = 2.7 V, section 2.3). The divider puts 47.5/69.6 of VBUS on the pin, so
  VBUS may rise to 0.88 V. R12 in parallel with the divider is 4.75 kohm, so up to 185 uA of
  leakage is harmless. D1's leakage (PMEG6010CEH Table 7 and Fig. 2): 0.8 uA typical at 5 V and
  25 C, and at most 50 uA at 25 C (the maximum is given at 60 V; Fig. 2 shows the current only
  falling as the voltage falls). That is under a third of the 185 uA bound. Fig. 2 (typical
  values) gives about 65 uA at 5 V and 85 C and about 600 uA at 125 C, so the typical part
  reaches 185 uA only at roughly 100 C. The data sheet
  gives no maximum above 25 C. Scaling Fig. 2 by its 25 C max/typ ratio (50/11) is an estimate,
  not a data sheet figure; on that estimate the bound holds to about 75 C. A host attached
  costs 1.0 mA through R12 (5 mW). R12 is the same 5.1 kohm part as R1 and R2.
* LEDs at about 2 mA, the current Kingbright characterises them at: power LED APTD1608LSURCK
  (red, VF 1.75 V typ at 2 mA, DSAO7433) through 750 ohm from 3.3 V; user LED APTD1608LCGCK
  (green, VF 1.9 V typ at 2 mA, DSAO7432) through 680 ohm on IO4. IO4 is not a strapping pin, a
  JTAG pin, a flash pin or a UART0 pin, and its ADC2 channel cannot be used while Wi-Fi is on
  (guidelines, "ADC"), so the LED costs no ADC input that Wi-Fi leaves usable. IO4 is pulled
  down at reset, so the LED starts off.

Headers: two 1x19 rows on Espressif's published DevKitC V4 grid (rows 25.40 mm apart, 2.54 mm
pitch, the right row 1.30 mm from the right edge, the last pin 1.29 mm from the bottom edge, on
a 27.94 mm-wide board), with the same pin order as the user guide's J2 and J3 tables, so the
board drops into the same breadboard rows and carrier sockets. The board is 0.50 mm longer than
the DevKitC's 48.26 mm: this module footprint's antenna keep-out courtyard reaches 6.31 mm
below the antenna edge, and the header courtyards must clear it, so the pin rows start 1.75 mm
below the top edge instead of 1.25 mm. Header pin labels are on the back silkscreen.

Schematic symbol: KiCad's own ESP32-WROOM-32E. Its four ground pins are one stacked pin,
[1,15,38,39], which the build expands to the four pads; pins 17-22 and 32 are NC, as the
-32E datasheet marks them.
"""

from __future__ import annotations

from ..design import NC, Board, Part, USB_C_EDGE
from .owner import CONTACT, LICENCE, LICENCE_TERMS, OWNER

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
WROOM = "Espressif ESP32-WROOM-32E datasheet v2.1"
CP2102N = "Silicon Labs CP2102N data sheet Rev. 1.5"


def res(ref, value, a, b, sch, desc):
    return Part(ref, "Device:R_Small", value, R0402, sch, {"1": a, "2": b}, fields={"Description": desc})


def cap(ref, value, a, b, sch, desc, fp=C0402):
    return Part(ref, "Device:C_Small", value, fp, sch, {"1": a, "2": b}, fields={"Description": desc})


# Header pinout: Espressif's ESP32-DevKitC V4 user guide, tables J2 and J3 (pin 1 at the antenna
# end). Its D2, D3, CMD (J2 16-18) and D1, D0, CLK (J3 17-19) are GPIO6-GPIO11, which the
# ESP32-WROOM-32E does not lead out: unconnected here.
J2_PINS = ["+3V3", "EN", "IO36", "IO39", "IO34", "IO35", "IO32", "IO33", "IO25", "IO26", "IO27", "IO14",
           "IO12", "GND", "IO13", NC, NC, NC, "+5V"]
J3_PINS = ["GND", "IO23", "IO22", "U0TXD", "U0RXD", "IO21", "GND", "IO19", "IO18", "IO5", "IO17", "IO16",
           "IO4", "IO0", "IO2", "IO15", NC, NC, NC]
J2_LABELS = ["3V3", "EN", "36", "39", "34", "35", "32", "33", "25", "26", "27", "14", "12", "GND", "13",
             "NC", "NC", "NC", "5V"]
J3_LABELS = ["GND", "23", "22", "TX", "RX", "21", "GND", "19", "18", "5", "17", "16", "4", "0", "2", "15",
             "NC", "NC", "NC"]

# Board and header grid. DevKitC V4 dimension drawing: 27.94 mm wide, rows 25.40 mm apart, right
# row 1.30 mm from the right edge, last pin 1.29 mm from the bottom edge. Pin rows start 1.75 mm
# below the top edge (see the docstring), so the board is 1.75 + 18 x 2.54 + 1.29 = 48.76 mm long.
W = 27.94
ROW_R = round(W - 1.30, 2)       # 26.64
ROW_L = round(ROW_R - 25.40, 2)  # 1.24
PIN1_Y = 1.75
H = round(PIN1_Y + 18 * 2.54 + 1.29, 2)   # 48.76
# Module centred between the rows. Its 6.19 mm antenna area begins 6.56 mm above the footprint
# origin, so it lies wholly past the top edge with 0.31 mm to spare; pin 1's pad keeps 0.54 mm
# from that edge.
MODULE = (round((ROW_L + ROW_R) / 2, 2), 6.25)

GPIO = ["IO34", "IO35", "IO32", "IO33", "IO25", "IO26", "IO27", "IO14", "IO12", "IO13", "IO15", "IO2",
        "IO4", "IO16", "IO17", "IO5", "IO18", "IO19", "IO21", "IO22", "IO23"]

PARTS = [
    # ---- USB-C, protection, 5 V rail ---------------------------------------------------------------
    Part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
         (40, 110), {"VBUS": "VBUS", "GND": "GND", "CC1": "CC1", "CC2": "CC2", "D+": "USB_D+", "D-": "USB_D-",
                     "SBU1": NC, "SBU2": NC, "SHIELD": "GND"},
         fields={"Manufacturer": "Korean Hroparts", "MPN": "TYPE-C-31-M-12",
                 "Description": "USB-C 2.0 receptacle, 16 pins (USB 2.0 only)"}),
    res("R1", "5.1k", "CC1", "GND", (80, 95), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC1, 5.1 kohm per TI SLVSFJ9 section 10.3.14.2)"),
    res("R2", "5.1k", "CC2", "GND", (95, 95), "Resistor 5.1 kohm 1% 0402 (USB-C sink Rd on CC2, 5.1 kohm per TI SLVSFJ9 section 10.3.14.2)"),
    # Diodes to ground only, as Silicon Labs shows on the CP2102N's USB pins (data sheet Figure 2.5).
    # A USBLC6-style part steers D+ into its VBUS pin: after a host unplugs, the CP2102N's live D+
    # pull-up would then hold VBUS near 2 V, between the VBUS pin's low and high thresholds, and
    # the bridge might never see the unplug when the board runs from its 5V pin.
    Part("U2", "Power_Protection:SP0503BAHT", "SP0503BAHTG", "Package_TO_SOT_SMD:SOT-143", (130, 110),
         {"1": "GND", "2": "USB_D-", "3": "USB_D+", "4": "VBUS"},       # the diodes are alike: D- on the pad nearer the
                                                                        # connector, so the pair reaches U4 (D+ above D-) uncrossed
         fields={"Manufacturer": "Littelfuse", "MPN": "SP0503BAHTG",
                 "Description": "USB ESD protection, three diodes to GND on D+, D- and VBUS, no path between them "
                                "(CP2102N data sheet Figure 2.5)"}),
    Part("F1", "Device:Polyfuse_Small", "500mA", "Fuse:Fuse_1206_3216Metric", (165, 95), {"1": "VBUS", "2": "VBUS_F"},
         fields={"Manufacturer": "Littelfuse", "MPN": "1206L050YR",
                 "Description": "PTC resettable fuse 0.50 A hold, 1.00 A trip, 6 V, 1206 (Littelfuse 1206L datasheet)"}),
    Part("D1", "Device:D_Schottky", "PMEG6010CEH", "Diode_SMD:D_SOD-123F", (185, 110), {"A": "VBUS_F", "K": "+5V"},
         fields={"Manufacturer": "Nexperia", "MPN": "PMEG6010CEH",
                 "Description": "Schottky 60 V 1 A, VF <= 530 mV at 500 mA, IR 0.8 uA typ at 5 V, <= 50 uA at 25 C (Nexperia PMEG6010CEH v.4): the 5V pin cannot feed the USB host"}),

    # ---- 3.3 V regulator ----------------------------------------------------------------------------
    Part("U3", "Regulator_Linear:AP7361C-33E", "AP7361C-33", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", (215, 110),
         {"VI": "+5V", "VO": "+3V3", "GND": "GND"},
         fields={"Manufacturer": "Diodes Incorporated", "MPN": "AP7361C-33E-13",
                 "Description": "LDO 3.3 V 1.0 A, SOT-223 (Diodes DS37274 Rev. 5-2); module needs >= 0.5 A"}),
    cap("C1", "4.7u", "+5V", "GND", (240, 105), "Capacitor 4.7 uF 10 V X5R 0603 (LDO input; DS37274 typical application)", C0603),
    cap("C2", "4.7u", "+3V3", "GND", (255, 105), "Capacitor 4.7 uF 10 V X5R 0603 (LDO output; DS37274 typical application)", C0603),
    res("R3", "750", "+3V3", "LED_PWR_A", (275, 105), "Resistor 750 ohm 1% 0402 (power LED, 2.1 mA at VF 1.75 V; Kingbright DSAO7433)"),
    Part("D2", "Device:LED_Small", "PWR", "LED_SMD:LED_0603_1608Metric", (290, 105), {"A": "LED_PWR_A", "K": "GND"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LSURCK",
                 "Description": "LED red 0603, power (VF 1.75 V typ at 2 mA, DSAO7433)"}),

    # ---- ESP32-WROOM-32E -------------------------------------------------------------------------------
    Part("U1", "RF_Module:ESP32-WROOM-32E", "ESP32-WROOM-32E-N4", "RF_Module:ESP32-WROOM-32E", (150, 235),
         {"GND": "GND", "VDD": "+3V3", "EN": "EN", "SENSOR_VP": "IO36", "SENSOR_VN": "IO39",
          "IO0": "IO0", "RXD0/IO3": "U0RXD", "TXD0/IO1": "U0TXD", **{g: g for g in GPIO}, "NC": NC},
         fields={"Manufacturer": "Espressif", "MPN": "ESP32-WROOM-32E-N4",
                 "Description": "ESP32 module, 4 MB flash, no PSRAM, PCB antenna (pins 17-22 and 32 NC, datasheet v2.1 Table 3)"}),
    cap("C3", "100n", "+3V3", "GND", (205, 205), f"Capacitor 100 nF X7R 0402 (module 3V3, C2 in {WROOM} section 9)"),
    cap("C4", "22u", "+3V3", "GND", (220, 205), f"Capacitor 22 uF 10 V X5R 0805 (module 3V3, C1 in {WROOM} section 9)", C0805),
    res("R4", "10k", "EN", "+3V3", (205, 245), f"Resistor 10 kohm 1% 0402 (EN RC delay, {WROOM} section 9)"),
    cap("C5", "1u", "GND", "EN", (220, 245), f"Capacitor 1 uF X7R 0402 (EN RC delay, {WROOM} section 9; "
                                            "esptool needs 1-10 uF on EN for auto-reset)"),
    res("R5", "10k", "IO0", "+3V3", (205, 275), "Resistor 10 kohm 1% 0402 (IO0 pull-up, Espressif guidelines "
                                                "'Strapping Pins'; internal pull-up 45 kohm)"),
    Part("SW1", "Switch:SW_Push", "EN", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", (240, 255),
         {"1": "EN", "2": "GND"}, fields={"Manufacturer": "C&K", "MPN": "KMR221G LFS", "Description": "Tactile switch, EN (reset)"}),
    Part("SW2", "Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", (240, 285),
         {"1": "IO0", "2": "GND"}, fields={"Manufacturer": "C&K", "MPN": "KMR221G LFS",
                                          "Description": "Tactile switch, BOOT (IO0 low: download mode)"}),
    res("R6", "680", "IO4", "LED_USR_A", (275, 285), "Resistor 680 ohm 1% 0402 (user LED, 2.1 mA at VF 1.9 V; Kingbright DSAO7432)"),
    Part("D3", "Device:LED_Small", "IO4", "LED_SMD:LED_0603_1608Metric", (290, 285), {"A": "LED_USR_A", "K": "GND"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LCGCK",
                 "Description": "LED green 0603, user LED on IO4 (VF 1.9 V typ at 2 mA, DSAO7432)"}),

    # ---- CP2102N USB-UART bridge ------------------------------------------------------------------------
    Part("U4", "Interface_USB:CP2102N-Axx-xQFN24", "CP2102N-A02-GQFN24", "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm",
         (370, 120), {"GND": "GND", "D+": "USB_D+", "D-": "USB_D-", "VIO": "+3V3", "VDD": "+3V3", "VREGIN": "+3V3",
                      "VBUS": "VBUS_SENSE", "~{RST}": "CP_RST", "RXD": "U0TXD", "TXD": "U0RXD",
                      "~{RTS}": "RTS", "~{DTR}": "DTR",
                      **{p: NC for p in ("NC", "~{RI}/CLK", "~{WAKEUP}/GPIO.3", "RS485/GPIO.2", "~{RXT}/GPIO.1",
                                         "~{TXT}/GPIO.0", "~{SUSPEND}", "SUSPEND", "~{CTS}", "~{DSR}", "~{DCD}")}},
         fields={"Manufacturer": "Silicon Labs", "MPN": "CP2102N-A02-GQFN24R",
                 "Description": f"USB-UART bridge, QFN-24, own regulator unused ({CP2102N} Figure 2.3)"}),
    cap("C6", "4.7u", "+3V3", "GND", (410, 95), f"Capacitor 4.7 uF 10 V X5R 0603 (CP2102N VREGIN/VDD, {CP2102N} Figure 2.3)", C0603),
    cap("C7", "100n", "+3V3", "GND", (425, 95), f"Capacitor 100 nF X7R 0402 (CP2102N VREGIN/VDD, {CP2102N} Figure 2.3)"),
    cap("C8", "4.7u", "+3V3", "GND", (440, 95), f"Capacitor 4.7 uF 10 V X5R 0603 (CP2102N VIO, {CP2102N} section 2.1)", C0603),
    cap("C9", "100n", "+3V3", "GND", (455, 95), f"Capacitor 100 nF X7R 0402 (CP2102N VIO, {CP2102N} section 2.1)"),
    res("R7", "1k", "CP_RST", "+3V3", (410, 140), f"Resistor 1 kohm 1% 0402 (CP2102N RSTb pull-up, {CP2102N} section 2.1)"),
    res("R8", "22.1k", "VBUS", "VBUS_SENSE", (425, 140), f"Resistor 22.1 kohm 1% 0402 (CP2102N VBUS divider, {CP2102N} Figure 2.5)"),
    res("R9", "47.5k", "VBUS_SENSE", "GND", (440, 140), f"Resistor 47.5 kohm 1% 0402 (CP2102N VBUS divider, {CP2102N} Figure 2.5)"),
    res("R12", "5.1k", "VBUS", "GND", (100, 140), "Resistor 5.1 kohm 1% 0402 (VBUS bleed: with the divider, 4.75 kohm, so up to 185 uA of D1 leakage keeps the CP2102N VBUS pin under VIL 0.6 V, "
        f"{CP2102N} Table 3.7; PMEG6010CEH leaks <= 50 uA at 25 C; 1.0 mA from a host)"),

    # ---- Automatic bootloader: RTS -> EN, DTR -> IO0, both together do nothing -------------------------------
    Part("Q1", "Transistor_BJT:MMBT3904", "MMBT3904", "Package_TO_SOT_SMD:SOT-23", (370, 230),
         {"B": "QB1", "E": "RTS", "C": "EN"},
         fields={"Manufacturer": "onsemi", "MPN": "MMBT3904LT1G", "Description": "NPN, auto-reset: RTS low (DTR high) pulls EN low"}),
    Part("Q2", "Transistor_BJT:MMBT3904", "MMBT3904", "Package_TO_SOT_SMD:SOT-23", (370, 275),
         {"B": "QB2", "E": "DTR", "C": "IO0"},
         fields={"Manufacturer": "onsemi", "MPN": "MMBT3904LT1G", "Description": "NPN, auto-boot: DTR low (RTS high) pulls IO0 low"}),
    res("R10", "10k", "DTR", "QB1", (345, 225), "Resistor 10 kohm 1% 0402 (Q1 base; >= 0.115 mA, MMBT3904LT1/D and CP2102N Table 3.7)"),
    res("R11", "10k", "RTS", "QB2", (345, 270), "Resistor 10 kohm 1% 0402 (Q2 base; >= 0.115 mA, MMBT3904LT1/D and CP2102N Table 3.7)"),

    # ---- Headers (Espressif DevKitC V4 user guide, J2 and J3) ---------------------------------------------------
    Part("J2", "Connector:Conn_01x19_Pin", "J2", "Connector_PinHeader_2.54mm:PinHeader_1x19_P2.54mm_Vertical",
         (480, 200), {str(i + 1): n for i, n in enumerate(J2_PINS)},
         fields={"Description": "Pin header 1x19 2.54 mm, left row (DevKitC V4 J2 pinout; 16-18 unconnected)"}),
    Part("J3", "Connector:Conn_01x19_Pin", "J3", "Connector_PinHeader_2.54mm:PinHeader_1x19_P2.54mm_Vertical",
         (530, 200), {str(i + 1): n for i, n in enumerate(J3_PINS)},
         fields={"Description": "Pin header 1x19 2.54 mm, right row (DevKitC V4 J3 pinout; 17-19 unconnected)"}),
]

# Board placement: (x, y, rotation) in mm, origin top-left, all parts on the top side. The module
# sits at the top between the header rows, antenna past the top edge. Below it, from the top: the
# EN button, the two auto-reset transistors and the 22 uF bulk capacitor; the regulator (left)
# and the CP2102N (right); the ESD part and CC resistors over the USB-C connector, which is on the
# bottom edge with the fuse, Schottky and VBUS bleed resistor to its left and the two LEDs and
# their resistors to its right; the BOOT button on the right, by IO0's header pin. Two 0402 capacitors sit in the gap
# beside the module's 3V3 and EN pins: 100 nF on 3V3 and the 1 uF EN delay capacitor.
PLACEMENT = {
    "U1": (MODULE[0], MODULE[1], 0),
    "J2": (ROW_L, PIN1_Y, 0), "J3": (ROW_R, PIN1_Y, 0),
    # beside the module's pins 1-3 (GND, 3V3, EN), in the gap to J2
    "C3": (3.60, 1.78, 90), "C5": (3.60, 4.01, 90),
    # below the module: bulk 3V3, EN button, auto-reset transistors, IO0 pull-up
    "C4": (5.60, 22.30, 90), "SW1": (9.60, 22.30, 0), "Q1": (14.60, 22.40, 0), "Q2": (18.90, 22.40, 0),
    "R5": (22.20, 22.40, 90), "R4": (13.50, 25.30, 0), "R10": (15.60, 25.30, 0), "R11": (18.90, 25.30, 0),
    # regulator (left) and CP2102N (right)
    "U3": (8.40, 29.70, 90), "C1": (6.00, 35.00, 0), "C2": (9.90, 35.00, 0),
    # the CP2102N's USB pins face left: D+/D- come up from the ESD part at x 12.5-14.5 and turn in;
    # its 3.3 V pins (VIO, VDD, VREGIN) meet at the lower-left corner, where the capacitors sit
    "U4": (18.40, 30.00, 0), "C9": (15.25, 31.75, 90), "C7": (17.10, 33.40, 0),
    "C6": (17.10, 34.80, 0), "C8": (17.10, 36.40, 0),
    "R7": (19.75, 33.40, 0), "R8": (19.75, 34.60, 0), "R9": (19.75, 35.80, 0),
    "SW2": (22.70, 36.50, 90),
    # USB-C on the bottom edge, ESD and CC resistors above it
    "J1": (15.00, H - USB_C_EDGE, 0), "U2": (13.50, 37.40, 90), "R1": (11.00, 38.50, 90), "R2": (16.40, 38.50, 90),
    # fuse and Schottky left of the connector, LEDs right of it
    "F1": (5.70, 43.60, 270), "D1": (8.20, 43.60, 270), "R12": (7.00, 38.20, 0),
    "R3": (20.95, 41.60, 90), "D2": (22.40, 41.60, 90), "R6": (20.95, 45.00, 90), "D3": (22.40, 45.00, 90),
}
_unplaced = sorted({p.ref for p in PARTS} - set(PLACEMENT))
assert not _unplaced, f"parts without a board position: {_unplaced}"
for _p in PARTS:
    _p.pcb = PLACEMENT[_p.ref]

# Back silkscreen: header pin labels beside each pin (mirrored, read from the back), then the
# name and copyright block below the module. The copyright line is the widest: it sits halfway
# between two pin rows, clear of the labels above and below it and inside the header pads.
_ROW = [round(PIN1_Y + 2.54 * i, 2) for i in range(19)]
TEXTS = [
    *[{"text": t, "x": ROW_L + 2.35, "y": _ROW[i], "size": 0.8, "layer": "B_SilkS", "mirror": True}
      for i, t in enumerate(J2_LABELS)],
    *[{"text": t, "x": ROW_R - 2.35, "y": _ROW[i], "size": 0.8, "layer": "B_SilkS", "mirror": True}
      for i, t in enumerate(J3_LABELS)],
    {"text": "EoS ESP32 DevKit  rev A", "x": W / 2, "y": round(_ROW[9] + 1.27, 2), "size": 1.0, "layer": "B_SilkS",
     "bold": True, "mirror": True},
    {"text": "(c) 2026 Kartikeydheer Srivastava", "x": W / 2, "y": round(_ROW[10] + 1.27, 2), "size": 0.8,
     "layer": "B_SilkS", "mirror": True},
    {"text": "All rights reserved", "x": W / 2, "y": round(_ROW[10] + 1.27 + 1.4, 2), "size": 0.8, "layer": "B_SilkS",
     "mirror": True},
    # front: what the buttons and LEDs are
    {"text": "EN", "x": 9.60, "y": 24.70, "size": 0.8},          # below SW1, above the regulator
    {"text": "BOOT", "x": 22.90, "y": 33.10, "size": 0.8},       # above SW2, below the CP2102N's corner
    {"text": "PWR", "x": 22.40, "y": 39.60, "size": 0.8},
    {"text": "IO4", "x": 22.40, "y": 47.30, "size": 0.8},
]

# Laid before the autorouter: the CP2102N's VBUS-sense divider (R8) to the receptacle's VBUS. With no
# via allowed in a pad, the autorouter left this link open twice (2026-10-20 rebuilds).
PRIORITY = [(("R8", "1"), ("J1", "A9"))]

BOARD = Board(
    name="eos-esp32-devkit",
    title="EoS ESP32 DevKit",
    revision="A",
    date="2026-10-12",
    company=OWNER,
    licence=LICENCE,
    contact=CONTACT,
    licence_terms=LICENCE_TERMS,
    credits=["Header grid (two 1x19 rows 25.40 mm apart, 2.54 mm pitch, right row 1.30 mm from the right edge, last "
             "pin 1.29 mm from the bottom edge), 27.94 mm board width and J2/J3 pin order from Espressif's "
             "ESP32-DevKitC V4 user guide and its dimension drawing (docs.espressif.com/projects/esp-dev-kits, "
             "dl.espressif.com/dl/schematics/esp32_devkitc_v4_dimensions.pdf); used as positions and pin names only"],
    width=W,
    height=H,
    corner_radius=1.0,
    rules={"min_drill": 0.2},     # the ESP32-WROOM-32E footprint's thermal vias under the module are 0.2 mm
    thickness=1.6,
    layers=2,
    # A via beside the CP2102N VIO capacitor's ground pad: the 2026-10-20 rebuild left it on a via-less
    # sliver, 13 mm of track from the nearest ground anchor.
    ground_vias=["C9"],
    parts=PARTS,
    priority_routes=PRIORITY,
    power_nets={"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V", "VBUS": "power:VBUS"},
    flagged_nets=["GND", "VBUS", "+5V"],
    headings=[((25, 75), "USB-C, ESD, fuse, Schottky, VBUS bleed"), ((200, 75), "3.3 V LDO (1 A)"), ((265, 75), "Power LED"),
              ((95, 180), "ESP32-WROOM-32E"), ((195, 180), "3V3 decoupling, EN delay, buttons (Espressif)"),
              ((265, 265), "User LED (IO4)"), ((340, 75), "CP2102N USB-UART (QFN-24)"),
              ((330, 200), "Auto-reset: RTS -> EN, DTR -> IO0 (esptool)"), ((465, 170), "Headers J2, J3 (DevKitC V4 pinout)"),
              ((35, 300), "Power nets")],
    power_block=(40.64, 315.0),
    notes=[((330, 330), "EoS ESP32 DevKit, rev A. Designed by Kartikeydheer Srivastava.\n"
                       "Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved; see LICENSE.txt.\n"
                       "Values from Espressif's ESP32-WROOM-32E datasheet v2.1 (sections 6 and 9) and ESP32 Hardware\n"
                       "Design Guidelines, the esptool docs (automatic bootloader), Silicon Labs CP2102N Rev. 1.5,\n"
                       "Diodes AP7361C DS37274, onsemi MMBT3904, Nexperia PMEG6010CEH, Littelfuse SP0503BAHTG, Littelfuse 1206L, Kingbright.\n"
                       "U1: KiCad's ESP32-WROOM-32E symbol; its stacked GND pin [1,15,38,39] is expanded to the four pads.\n"
                       "R12 (5.1 kohm) bleeds D1's reverse leakage off VBUS, so a 5V-pin supply does not fake a USB host.\n"
                       "GPIO6-11 are the module's internal flash pins and are not led out: J2 16-18, J3 17-19 are NC.\n"
                       "Header grid and pinout from Espressif's DevKitC V4 user guide (positions and names only).")],
    netclasses={"Power": {"track": 0.4, "clearance": 0.15}, "USB": {"track": 0.2, "clearance": 0.15}},
    net_to_class={"VBUS": "Power", "VBUS_F": "Power", "+5V": "Power", "+3V3": "Power",
                  "USB_D+": "USB", "USB_D-": "USB"},
)
