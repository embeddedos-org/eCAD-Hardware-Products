"""EoS Feather RP2040: an RP2040 board in the Feather form factor, designed by Kartikeydheer Srivastava.

Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved: this design file is not under
the repository's MIT licence; see boards/eos/eos-feather-rp2040/LICENSE.txt.

A 50.8 x 22.86 mm four-layer board with a Raspberry Pi RP2040, 16 MB of QSPI flash, USB-C, a
single-cell LiPo charger with a JST PH battery connector, a 3.3 V regulator with the Feather EN
pin, RESET, BOOTSEL and user buttons, a red user LED on D13, a yellow charge LED, a Raspberry Pi
3-pin SWD connector and a STEMMA QT / Qwiic I2C connector. It does the job of Adafruit's Feather
RP2040 (product 4884): FeatherWings and CircuitPython or Arduino code written for that board's
pinout find the same signals on the same header pins. "Feather" is used only to say what it
fits; this is not an Adafruit product. No design file of Adafruit's (schematic, layout, CAD,
Gerbers, BOM) was opened.

Facts used, and where they come from (published specifications and pinouts only):

* Adafruit's Feather Specification (learn.adafruit.com/adafruit-feather/feather-specification):
  the 0.9 x 2.0 in outline with 0.1 in holes at each corner, their centres 0.1 in from each edge
  (the page's dimension drawing: 1.8 in and 0.7 in apart); a 16-pin strip along the bottom edge
  centred 1.0 in from the left edge and a 12-pin strip along the top edge 1.2 in from the left,
  0.8 in apart; the pin order from the USB end; USB at the centre of the left edge; a JST PH
  battery connector; on-board LiPo charging at 100-500 mA; an active-low RST pin and a reset
  button; an EN pin that turns the 3.3 V regulator off; a user LED on D13; I2C pull-ups on the
  wings, not on the mainboard. As EoS Motion Wing uses them: pin 1 of the 16-pin strip at
  (6.35, 21.59) mm, pin 1 of the 12-pin strip at (16.51, 1.27) mm.
* Adafruit's Feather RP2040 pinout (learn.adafruit.com/adafruit-feather-rp2040-pico/pinouts and
  its pinout diagram, product 4884): TX GPIO0, RX GPIO1, SDA GPIO2, SCL GPIO3, D4 GPIO6, D5
  GPIO7, D6 GPIO8, D9 GPIO9, D10 GPIO10, D11 GPIO11, D12 GPIO12, D13 GPIO13 (the red LED), SCK
  GPIO18, MO GPIO19, MI GPIO20, D24 GPIO24, D25 GPIO25, A0-A3 GPIO26-29; 3.3 V on the 16-pin
  strip's second and third pins (the third is AREF in the spec; the RP2040 has no separate ADC
  reference); STEMMA QT on SDA/SCL (I2C1); "the BOOTSEL button is connected to GPIO4 for use in
  your code" (rev D and later), so this board's user button is on GPIO4. The product page gives
  8 MB of flash, a 12 MHz crystal, a 200 mA+ charger and a 500 mA peak regulator. The pinout
  diagram marks the battery connector's polarity (- toward the USB end, + away from it, on a
  connector facing the 12-pin edge), which this board keeps: looking into the connector from
  outside the board, top side up, + is on the left. J4 faces the right-hand edge, so + (pin 1)
  is its pin nearer the 16-pin edge.
* STEMMA QT / Qwiic (learn.adafruit.com/introducing-adafruit-stemma-qt, technical specs): JST SH
  4-pin, 1 GND, 2 V+, 3 SDA, 4 SCL; the I2C device carries the pull-ups.
* Raspberry Pi 3-pin Debug Connector Specification (RP-003139-SP-4): JST SH 3-pin, 1 SC (SWCLK),
  2 GND, 3 SD (SWDIO), marked "SWD". The specification recommends 100 ohm in series at the
  target's pins "unless the platform is very low cost and/or space constrained"; this board is
  space constrained there (pins 20-26 carry XIN, XOUT, DVDD, SWCLK, SWDIO and RUN at 0.4 mm
  pitch, with R5 and C20 in front of them), so the lines run straight to the connector.

Every value follows a data sheet:

* RP2040 (Raspberry Pi RP2040 datasheet, build 2025-02-20 3184e62, "the datasheet") and
  Raspberry Pi's "Hardware design with RP2040" (release 2, build 20/08/2026, "the guide"):
  100 nF at each IOVDD and DVDD pin and at USB_VDD and ADC_AVDD (datasheet 2.9.1-2.9.5), 1 uF at
  VREG_VIN and at VREG_VOUT, which feeds the DVDD pins (datasheet 2.10.1, guide 2.1.3, 0402);
  27 ohm in series with USB_DP and USB_DM, close to the chip (datasheet Table 1, guide 2.4.1);
  TESTEN to ground (datasheet Table 1); RUN has an internal pull-up (datasheet Table 619), so
  the RESET button pulls it low with no resistor. Crystal: Abracon ABM8-272-T3, 12 MHz, CL
  10 pF, ESR 50 ohm (guide Table 1, the crystal the guide recommends), 15 pF C0G loads and a
  1 kohm series resistor on XOUT (guide 2.3, tuned for IOVDD = 3.3 V). Flash: Winbond
  W25Q128JVPIQ, the guide's W25Q128JV (2.2) in its 6 x 5 mm WSON package (W25Q128JV data sheet
  Rev. F, package code P); 16 MB, so firmware built for an 8 MB board uses its first half. Its
  exposed pad is left unconnected and has no via under it (data sheet 10.3: "Avoid placement of
  exposed PCB vias under the pad"). 100 nF at its VCC (guide Figure 11). BOOTSEL: 1 kohm from
  QSPI_SS to the button; the 10 kohm QSPI_SS pull-up is not fitted, as the guide does for this
  flash (2.2). The RP2040's single ground is its exposed pad (datasheet Table 1).
* Charger: Microchip MCP73831T-2ACI/OT (DS20001984H), 4.20 V. RPROG = 4.7 kohm sets
  IREG = 1000 V / RPROG = 213 mA (equation 5-1), inside the Feather spec's 100-500 mA and the
  product's "200mA+". VDD and VBAT each need at least 4.7 uF (sections 3.1, 3.2 and 6.1.1.4);
  10 uF 16 V X5R 0805 parts are fitted, to leave room for an X5R part's loss of capacitance at
  5 V (not checked against a capacitor data sheet). STAT (Table 5-1) is low while charging, high
  when charging is complete and high-impedance with no battery: the yellow CHG LED runs from VBUS
  through 1 kohm into STAT, so it lights only while charging.
* Load sharing: Microchip AN1149 (DS01149C), Figures 5-7: a P-channel MOSFET from the battery to
  the system rail with its gate on the USB supply and a 100 kohm pull-down ("A 100 kohm RPULL
  resistor is recommended"), and a Schottky diode from the USB supply to the system rail. With
  USB present the gate sits above the source and the MOSFET is off; the charger then charges the
  battery while USB powers the board. Without USB the pull-down turns it on. AOS AO3401A (Rev 3.1,
  December 2023): VGS(th) -0.5 to -1.3 V, RDS(on) at most 85 mohm at VGS = -2.5 V. On battery,
  D1 is reverse-biased by VSYS and its leakage flows into the gate node, whose only path to ground
  is RPULL: the gate rises by I_R x RPULL. AN1149's 100 kohm with a very-low-VF Schottky (an
  MBR120VL is allowed 0.6 mA at 25 C) could lift the gate to VSYS and turn Q1 off. So D1 is a
  Nexperia PMEG6010CEH (v.4, 1 July 2023: 60 V, 1 A, VF at most 530 mV at 500 mA; IR 0.8 uA
  typical at 5 V and at most 50 uA at 60 V, 25 C; its Fig. 2 shows about 65 uA at 5 V and 85 C,
  typical) and RPULL is 10 kohm: the gate rises at most 0.5 V at 25 C (taking the 60 V maximum,
  since the current falls with the voltage) and about 0.65 V at 85 C typical, so VGS stays below
  -2.3 V down to a 3.0 V cell. USB pays 0.5 mA for it.
* Regulator: Diodes AP2112K-3.3TRG1 (DS39724 Rev. 2-2), the part the Feather spec names: 600 mA,
  dropout at most 400 mV at 600 mA, stable with 1.0 uF ceramic capacitors (X5R/X7R, Note 4);
  10 uF X5R is fitted on both sides. EN is high above 1.5 V and has an internal 3 Mohm
  pull-down; 100 kohm to VSYS holds it at 97 % of VSYS, and the Feather EN pin pulls it low.
* USB-C: HRO TYPE-C-31-M-12, origin USB_C_EDGE from the edge (design.USB_C_EDGE). 5.1 kohm Rd on
  CC1 and CC2 make it a 5 V sink (USB Type-C specification). Littelfuse SP0503BAHTG (SP05xxBA
  data sheet): diodes to ground only on D+, D- and VBUS. Littelfuse 0805L050WR (0805L data sheet,
  revised 10/29/21): 0.50 A hold, 1.00 A trip, 6 V, R1max 0.85 ohm, between the receptacle's VBUS
  and the board (the Feather USB pin, the charger and the Schottky).
* Buttons: Omron B3U-1000P (A162-E1-07): 1-50 mA at 3-12 V, minimum load 10 uA at 1 V; the
  GPIO4 button needs the RP2040's internal pull-up on in firmware (pins reset with pull-downs,
  datasheet Table 615). LEDs: Kingbright APTD1608LSURCK (DSAO7433, VF 1.75 V typical at 2 mA)
  through 1 kohm from GPIO13 (1.5 mA, under the 4 mA default drive) and APTD1608LSYCK (DSAO7434,
  VF 1.85 V) through 1 kohm from VBUS (2.8 mA, under STAT's 25 mA sink).

Four layers (signal / ground / 3.3 V / signal). The Feather pinout reverses the RP2040's GPIO
order on the 16-pin strip (A0-A3 are GPIO26-29, left of D24/D25, left of SCK/MO/MI on
GPIO18-20), the chip's USB pins face away from the USB-C receptacle at the left edge whatever way
the chip is turned so that the GPIOs face their strips, and the RP2040's only ground is its 3.2
mm centre pad. On two layers every one of those crossings would cut the bottom ground pour under
a 0.4 mm-pitch QFN; with a solid ground plane under the top layer they do not, the USB pair has a
reference plane, and the supply pins reach their plane through vias placed inward of the pad ring.
"""

from __future__ import annotations

from ..design import NC, Board, BringUp, BringUpTest, Part, Rail, USB_C_EDGE, bench_pad
from .owner import CONTACT, LICENCE, LICENCE_TERMS, OWNER

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
LED0603 = "LED_SMD:LED_0603_1608Metric"
B3U = "Button_Switch_SMD:SW_SPST_B3U-1000P"

RP_DS = "Raspberry Pi RP2040 datasheet build 2025-02-20"
RP_HW = "Raspberry Pi Hardware design with RP2040 release 2"
MCP = "Microchip MCP73831/2 DS20001984H"
AP = "Diodes AP2112 DS39724 Rev. 2-2"


def res(ref, value, a, b, sch, desc, dnp=False):
    return Part(ref, "Device:R_Small", value, R0402, sch, {"1": a, "2": b},
                fields={"Description": f"Resistor {value} 1% 0402 ({desc})"}, dnp=dnp)


def cap(ref, value, a, b, sch, desc, fp=C0402):
    return Part(ref, "Device:C_Small", value, fp, sch, {"1": a, "2": b}, fields={"Description": desc})


def bulk(ref, a, sch, what):
    return cap(ref, "10u", a, "GND", sch, f"Capacitor 10 uF 16 V X5R 0805 ({what})", C0805)


def button(ref, value, net, sch, what):
    return Part(ref, "Switch:SW_Push", value, B3U, sch, {"1": net, "2": "GND"},
                fields={"Manufacturer": "Omron", "MPN": "B3U-1000P",
                        "Description": f"Tactile switch 3.0 x 2.5 mm, top-actuated, {what} (Omron A162-E1-07)"})


# The Feather strips, pin 1 at the USB end (Feather Specification; Feather RP2040 pinout).
J2_PINS = ["RUN", "+3V3", "+3V3", "GND", "GP26_A0", "GP27_A1", "GP28_A2", "GP29_A3", "GP24_D24",
           "GP25_D25", "GP18_SCK", "GP19_MO", "GP20_MI", "GP1_RX", "GP0_TX", "GP6_D4"]
J3_PINS = ["VBAT", "EN", "VBUS_F", "GP13_D13", "GP12_D12", "GP11_D11", "GP10_D10", "GP9_D9", "GP8_D6",
           "GP7_D5", "GP3_SCL", "GP2_SDA"]

GPIO = {"GPIO0": "GP0_TX", "GPIO1": "GP1_RX", "GPIO2": "GP2_SDA", "GPIO3": "GP3_SCL", "GPIO4": "GP4_USER",
        "GPIO5": NC, "GPIO6": "GP6_D4", "GPIO7": "GP7_D5", "GPIO8": "GP8_D6", "GPIO9": "GP9_D9",
        "GPIO10": "GP10_D10", "GPIO11": "GP11_D11", "GPIO12": "GP12_D12", "GPIO13": "GP13_D13",
        "GPIO14": NC, "GPIO15": NC, "GPIO16": NC, "GPIO17": NC, "GPIO18": "GP18_SCK", "GPIO19": "GP19_MO",
        "GPIO20": "GP20_MI", "GPIO21": NC, "GPIO22": NC, "GPIO23": NC, "GPIO24": "GP24_D24",
        "GPIO25": "GP25_D25", "GPIO26/ADC0": "GP26_A0", "GPIO27/ADC1": "GP27_A1", "GPIO28/ADC2": "GP28_A2",
        "GPIO29/ADC3": "GP29_A3"}

W, H = 50.8, 22.86                         # 2.0 x 0.9 in
HEADER_16_PIN1 = (6.35, 21.59)             # centred 1.0 in from the left edge, 0.05 in from the bottom edge
HEADER_12_PIN1 = (16.51, 1.27)             # centred 1.2 in from the left edge, 0.8 in above the 16-pin strip
HOLES = [(2.54, 2.54), (48.26, 2.54), (2.54, 20.32), (48.26, 20.32)]   # 0.1 in in from each edge
MCU = (30.0, 11.2)

PARTS = [
    # ---- USB-C, ESD, CC, fuse -------------------------------------------------------------
    Part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
         (40, 60), {"VBUS": "VBUS", "GND": "GND", "CC1": "CC1", "CC2": "CC2", "D+": "USB_D+", "D-": "USB_D-",
                    "SBU1": NC, "SBU2": NC, "SHIELD": "GND"},
         fields={"Manufacturer": "Korean Hroparts", "MPN": "TYPE-C-31-M-12",
                 "Description": "USB-C 2.0 receptacle, 16 pins, 5 V sink"}),
    res("R1", "5.1k", "CC1", "GND", (75, 50), "CC1 Rd: a USB Type-C sink"),
    res("R2", "5.1k", "CC2", "GND", (88, 50), "CC2 Rd: a USB Type-C sink"),
    Part("U3", "Power_Protection:SP0503BAHT", "SP0503BAHTG", "Package_TO_SOT_SMD:SOT-143", (110, 60),
         {"1": "GND", "2": "USB_D+", "3": "USB_D-", "4": "VBUS"},
         fields={"Manufacturer": "Littelfuse", "MPN": "SP0503BAHTG",
                 "Description": "USB ESD protection: three diodes to GND on D+, D- and VBUS, none to VBUS "
                                "(Littelfuse SP05xxBA: pins 2-4 to the common anode, pin 1)"}),
    Part("F1", "Device:Polyfuse_Small", "500mA", "Fuse:Fuse_0805_2012Metric", (75, 80), {"1": "VBUS", "2": "VBUS_F"},
         fields={"Manufacturer": "Littelfuse", "MPN": "0805L050WR",
                 "Description": "PTC resettable fuse 0.50 A hold, 1.00 A trip, 6 V, 0805 (Littelfuse 0805L, revised 10/29/21)"}),

    # ---- LiPo charger and load sharing (MCP73831, AN1149) -----------------------------------------
    Part("U4", "Battery_Management:MCP73831-2-OT", "MCP73831-2", "Package_TO_SOT_SMD:SOT-23-5", (150, 75),
         {"STAT": "CHG_STAT", "V_{SS}": "GND", "V_{BAT}": "VBAT", "V_{DD}": "VBUS_F", "PROG": "PROG"},
         fields={"Manufacturer": "Microchip", "MPN": "MCP73831T-2ACI/OT",
                 "Description": f"Single-cell LiPo charger, 4.20 V, 213 mA ({MCP})"}),
    res("R10", "4.7k", "PROG", "GND", (175, 70), f"RPROG: IREG = 1000 V / 4.7 kohm = 213 mA, {MCP} equation 5-1"),
    bulk("C30", "VBUS_F", (130, 95), f"charger VDD, at least 4.7 uF: {MCP} 3.1"),
    bulk("C31", "VBAT", (185, 95), f"charger VBAT, at least 4.7 uF: {MCP} 3.2 and 6.1.1.4"),
    res("R11", "1k", "VBUS_F", "CHG_A", (150, 105), "CHG LED: (5 - 1.85 - 0.4) V / 1 kohm = 2.8 mA into STAT"),
    Part("D2", "Device:LED_Small", "CHG", LED0603, (165, 105), {"A": "CHG_A", "K": "CHG_STAT"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LSYCK",
                 "Description": "LED yellow 590 nm 0603, VF 1.85 V at 2 mA (DSAO7434): lit while charging"}),
    Part("J4", "Connector:Conn_01x02_Pin", "LiPo", "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
         (210, 70), {"1": "VBAT", "2": "GND"},
         fields={"Manufacturer": "JST", "MPN": "S2B-PH-SM4-TB",
                 "Description": "JST PH 2-pin side entry: 1 battery +, 2 battery - (polarity of Adafruit's LiPo cells)"}),
    # the battery rail's test pad; the battery line from J4 to the BAT pin passes it. A bench pad like the
    # others (stage-2 review n2): no BOM line, as it has no placement row
    bench_pad("TP1", "VBAT", "VBAT", (43.2, 3.3), (225, 50)),
    Part("D1", "Device:D_Schottky", "PMEG6010CEH", "Diode_SMD:D_SOD-123F", (240, 60), {"A": "VBUS_F", "K": "VSYS"},
         fields={"Manufacturer": "Nexperia", "MPN": "PMEG6010CEH",
                 "Description": "Schottky 60 V 1 A SOD-123F, VF <= 530 mV at 500 mA, IR 0.8 uA typ at 5 V (PMEG6010CEH v.4): "
                                "USB to VSYS (AN1149 D1); chosen for low leakage into Q1's gate"}),
    Part("Q1", "Transistor_FET:AO3401A", "AO3401A", "Package_TO_SOT_SMD:SOT-23", (240, 85),
         {"G": "VBUS_F", "S": "VSYS", "D": "VBAT"},
         fields={"Manufacturer": "Alpha & Omega", "MPN": "AO3401A",
                 "Description": "P-MOSFET -30 V, RDS(on) <= 85 mohm at -2.5 V (AO3401A Rev 3.1): battery to VSYS when USB is absent (AN1149 Q1)"}),
    res("R13", "10k", "VBUS_F", "GND", (260, 95), "AN1149 RPULL: holds Q1's gate low without USB, against D1's reverse leakage"),

    # ---- 3.3 V regulator ---------------------------------------------------------------------------
    Part("U5", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5", (290, 70),
         {"VIN": "VSYS", "GND": "GND", "EN": "EN", "VOUT": "+3V3", "4": NC},
         fields={"Manufacturer": "Diodes Incorporated", "MPN": "AP2112K-3.3TRG1",
                 "Description": f"LDO 3.3 V 600 mA with enable, SOT-25 ({AP})"}),
    bulk("C32", "VSYS", (270, 85), f"LDO input, at least 1.0 uF: {AP} Note 4"),
    bulk("C33", "+3V3", (315, 85), f"LDO output, at least 1.0 uF: {AP} Note 4"),
    res("R14", "100k", "VSYS", "EN", (290, 50), f"EN pull-up: EN high above 1.5 V, 3 Mohm internal pull-down ({AP}); the Feather EN pin pulls it low"),

    # ---- RP2040 -------------------------------------------------------------------------------------
    Part("U1", "MCU_RaspberryPi:RP2040", "RP2040", "Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm", (140, 230),
         {"IOVDD": "+3V3", "DVDD": "+1V1", "VREG_VIN": "+3V3", "VREG_VOUT": "+1V1", "USB_VDD": "+3V3",
          "ADC_AVDD": "+3V3", "GND": "GND", "TESTEN": "GND", "XIN": "XIN", "XOUT": "XOUT", "SWCLK": "SWCLK",
          "SWDIO": "SWDIO", "RUN": "RUN", "USB_DM": "RP_USB_DM", "USB_DP": "RP_USB_DP",
          "QSPI_SD0": "QSPI_SD0", "QSPI_SD1": "QSPI_SD1", "QSPI_SD2": "QSPI_SD2", "QSPI_SD3": "QSPI_SD3",
          "QSPI_SCLK": "QSPI_SCLK", "~{QSPI_SS}": "QSPI_SS", **GPIO},
         fields={"Manufacturer": "Raspberry Pi", "MPN": "RP2040",
                 "Description": "Dual Cortex-M0+ microcontroller, 264 kB SRAM, QFN-56 7 x 7 mm"}),
    cap("C10", "1u", "+3V3", "GND", (205, 200), f"Capacitor 1 uF X5R 0402 (VREG_VIN, pin 44: {RP_DS} 2.9.3, 2.10.1)"),
    cap("C11", "1u", "+1V1", "GND", (220, 200), f"Capacitor 1 uF X5R 0402 (VREG_VOUT, pin 45: {RP_DS} 2.10.1)"),
]

# 100 nF at each supply pin it serves (datasheet 2.9.1-2.9.5).
DECOUPLING = [
    ("C12", "+3V3", "IOVDD pin 1"), ("C13", "+3V3", "IOVDD pin 10"), ("C14", "+3V3", "IOVDD pin 22"),
    ("C15", "+3V3", "IOVDD pin 33"), ("C16", "+3V3", "IOVDD pin 42"), ("C17", "+3V3", "IOVDD pin 49"),
    ("C18", "+3V3", "USB_VDD pin 48"), ("C19", "+3V3", "ADC_AVDD pin 43"),
    ("C20", "+1V1", "DVDD pin 23"), ("C21", "+1V1", "DVDD pin 50"),
]
for i, (ref, net, what) in enumerate(DECOUPLING):
    PARTS.append(cap(ref, "100n", net, "GND", (205 + 14 * i, 260),
                     f"Capacitor 100 nF X7R 0402 ({what}: {RP_DS} 2.9)"))

PARTS += [
    # ---- USB series termination, at the chip -----------------------------------------------------
    res("R3", "27", "USB_D+", "RP_USB_DP", (300, 170), f"USB_DP series termination, at the chip: {RP_DS} Table 1"),
    res("R4", "27", "USB_D-", "RP_USB_DM", (315, 170), f"USB_DM series termination, at the chip: {RP_DS} Table 1"),

    # ---- QSPI flash and BOOTSEL ----------------------------------------------------------------------
    Part("U2", "Memory_Flash:W25Q128JVP", "W25Q128JVP", "Package_SON:WSON-8-1EP_6x5mm_P1.27mm_EP3.4x4.3mm", (360, 70),
         {"~{CS}": "QSPI_SS", "DO/IO_{1}": "QSPI_SD1", "~{WP}/IO_{2}": "QSPI_SD2", "GND": "GND",
          "DI/IO_{0}": "QSPI_SD0", "CLK": "QSPI_SCLK", "~{HOLD}/~{RESET}/IO_{3}": "QSPI_SD3", "VCC": "+3V3",
          "EP": NC},
         fields={"Manufacturer": "Winbond", "MPN": "W25Q128JVPIQ",
                 "Description": "128 Mbit QSPI NOR flash, WSON-8 6 x 5 mm; exposed pad unconnected, no via under it "
                                "(W25Q128JV Rev. F section 10.3)"}),
    cap("C22", "100n", "+3V3", "GND", (385, 65), f"Capacitor 100 nF X7R 0402 (flash VCC: {RP_HW} Figure 11)"),
    res("R6", "1k", "QSPI_SS", "BOOTSEL", (405, 50), f"BOOTSEL: lets QSPI_SS over-drive the button ({RP_HW} 2.2)"),
    res("R7", "10k", "QSPI_SS", "+3V3", (420, 50), f"QSPI_SS pull-up, not fitted for this flash ({RP_HW} 2.2)", dnp=True),
    button("SW2", "BOOT", "BOOTSEL", (440, 65), "BOOTSEL (hold at reset for the USB bootloader)"),

    # ---- Crystal -------------------------------------------------------------------------------------
    Part("Y1", "Device:Crystal_GND24_Small", "12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", (360, 160),
         {"1": "XIN", "3": "XTAL_OUT", "G": "GND"},
         fields={"Manufacturer": "Abracon", "MPN": "ABM8-272-T3",
                 "Description": f"Crystal 12 MHz, CL 10 pF, ESR 50 ohm, +-30 ppm, 3225 ({RP_HW} 2.3.1 Table 1)"}),
    cap("C23", "15p", "XIN", "GND", (380, 155), f"Capacitor 15 pF C0G 0402 (crystal load: {RP_HW} 2.3)"),
    cap("C24", "15p", "XTAL_OUT", "GND", (395, 155), f"Capacitor 15 pF C0G 0402 (crystal load: {RP_HW} 2.3)"),
    res("R5", "1k", "XOUT", "XTAL_OUT", (335, 155), f"crystal series resistor for IOVDD = 3.3 V: {RP_HW} 2.3"),

    # ---- Reset, user button, LED -------------------------------------------------------------------------
    button("SW1", "RESET", "RUN", (440, 160), "RESET (RUN; internal pull-up, RP2040 datasheet Table 619)"),
    button("SW3", "USER", "GP4_USER", (440, 200), "user button on GPIO4 (Feather RP2040 pinout)"),
    res("R12", "1k", "GP13_D13", "LED13_A", (360, 230), "D13 LED: (3.3 - 1.75) V / 1 kohm = 1.55 mA"),
    Part("D3", "Device:LED_Small", "D13", LED0603, (375, 230), {"A": "LED13_A", "K": "GND"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LSURCK",
                 "Description": "LED red 630 nm 0603, VF 1.75 V at 2 mA (DSAO7433): the Feather user LED on D13"}),

    # ---- SWD and STEMMA QT ----------------------------------------------------------------------------
    Part("J6", "Connector:Conn_01x03_Pin", "SWD", "Connector_JST:JST_SH_BM03B-SRSS-TB_1x03-1MP_P1.00mm_Vertical",
         (500, 270), {"1": "SWCLK", "2": "GND", "3": "SWDIO"},
         fields={"Manufacturer": "JST", "MPN": "BM03B-SRSS-TB",
                 "Description": "SWD: Raspberry Pi 3-pin debug connector, 1 SC, 2 GND, 3 SD (RP-003139-SP-4)"}),
    Part("J5", "Connector:Conn_01x04_Pin", "STEMMA QT", "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal",
         (530, 270), {"1": "GND", "2": "+3V3", "3": "GP2_SDA", "4": "GP3_SCL"},
         fields={"Manufacturer": "JST", "MPN": "SM04B-SRSS-TB",
                 "Description": "STEMMA QT / Qwiic I2C1: 1 GND, 2 3.3 V, 3 SDA GPIO2, 4 SCL GPIO3; pull-ups on the device"}),

    # ---- Feather headers (male, on the back) --------------------------------------------------------
    Part("J2", "Connector_Generic:Conn_01x16", "Feather 16-pin", "Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical",
         (480, 140), {str(i + 1): n for i, n in enumerate(J2_PINS)}, side="B",
         fields={"Manufacturer": "Wurth Elektronik", "MPN": "61301611121",
                 "Description": "Pin header 1x16 2.54 mm, Feather 16-pin strip: RST, 3V, 3V, GND, A0-A3, D24, D25, SCK, MO, "
                                "MI, RX, TX, D4 (Feather Specification; Feather RP2040 pinout)"}),
    Part("J3", "Connector_Generic:Conn_01x12", "Feather 12-pin", "Connector_PinHeader_2.54mm:PinHeader_1x12_P2.54mm_Vertical",
         (530, 140), {str(i + 1): n for i, n in enumerate(J3_PINS)}, side="B",
         fields={"Manufacturer": "Wurth Elektronik", "MPN": "61301211121",
                 "Description": "Pin header 1x12 2.54 mm, Feather 12-pin strip: BAT, EN, USB, D13, D12, D11, D10, D9, D6, "
                                "D5, SCL, SDA (Feather Specification; Feather RP2040 pinout)"}),
]
# ---- Bench test pads (BENCH-READY C1): every rail of the power tree and a GND pad; TP1 (VBAT)
# was already there. The bench-ready audit (g2, 24 Oct 2026) found the spots with the pad's centre clear;
# each is nudged (0.2-0.4 mm) so the pad's 1 mm courtyard clears its neighbours' courtyards too, and +3V3
# moved from beside C14 (17.7, 13.6) to (14.4, 10.7) beside the other power pads, because at C14 it took
# the only bottom-left room for a fiducial and the board fell back to two (stage 2 probe, 30 Oct 2026).
# GND (TP7) sits beside TP1 (VBAT) at the top-right corner: by the chip, at the audit's spot, it stood in
# the way of RUN, which three stage-2 routing runs then left open or cut off (30 Oct 2026).
PARTS += [
    bench_pad("TP2", "VBUS", "VBUS", (13.1, 12.9), (300, 400)),
    bench_pad("TP3", "VBUS_F", "VUSB", (16.5, 10.2), (315, 400)),
    bench_pad("TP4", "VSYS", "VSYS", (16.6, 4.8), (330, 400)),
    bench_pad("TP5", "+3V3", "3V3", (14.4, 10.7), (345, 400)),
    bench_pad("TP6", "+1V1", "1V1", (24.8, 9.7), (360, 400)),
    bench_pad("TP7", "GND", "GND", (46.0, 5.8), (375, 400)),
]
for i, _ in enumerate(HOLES):
    PARTS.append(Part(f"H{i + 1}", "Mechanical:MountingHole", "2.5mm", "MountingHole:MountingHole_2.5mm",
                      (60 + 20 * i, 360), {},
                      fields={"Description": "Mounting hole 2.5 mm, unplated (Feather Specification: 0.1 in holes at each corner)"}))

# Board placement: (x, y, rotation) in mm, origin top-left, USB end on the left, all parts but the
# headers on the top side. The RP2040 is turned so that its GPIO0-11 side faces the 12-pin strip
# and its GPIO18-29 side the 16-pin strip (KiCad 270 degrees: pin 1 at the top right); its QSPI
# and USB side then faces right, where the flash sits, and its crystal, SWD and RUN side faces
# left.
PLACEMENT = {
    "J2": (HEADER_16_PIN1[0], HEADER_16_PIN1[1], 270), "J3": (HEADER_12_PIN1[0], HEADER_12_PIN1[1], 270),
    **{f"H{i + 1}": (x, y, 0) for i, (x, y) in enumerate(HOLES)},
    # USB-C on the left edge, centred at y 11.90: 0.47 mm below the edge's centre (y 11.43), where the
    # Feather Specification puts USB (the README says so). The ESD part's D+ and D- pads (2, 3) face the receptacle;
    # the pair touches them and runs on together through the gap between pins 1 (GND) and 4 (VBUS).
    # CC pull-downs above and below; fuse below
    "J1": (USB_C_EDGE, 11.9, 270), "U3": (10.35, 11.9, 270), "R1": (9.4, 9.5, 0), "R2": (9.6, 14.0, 0),
    "F1": (9.45, 16.2, 90),
    # STEMMA QT facing the top edge, left of the 12-pin strip; D13 LED above the USB-C, CHG LED below
    # it (Feather Specification: user LED above, CHG LED below the USB connector)
    "J5": (11.5, 3.15, 180), "D3": (6.45, 3.1, 270), "R12": (6.45, 5.6, 90),
    "D2": (6.9, 18.1, 0), "R11": (6.9, 19.6, 0),
    # charger below the USB pair, VBAT capacitor beside it
    "U4": (12.55, 18.45, 180), "C30": (12.3, 15.6, 0), "R10": (9.9, 19.6, 90), "C31": (15.6, 17.6, 90),
    # power path and regulator under the BAT, EN and USB pins of the 12-pin strip
    "U5": (21.9, 4.0, 0), "C32": (18.7, 3.95, 270), "C33": (22.1, 6.7, 180), "R14": (19.3, 6.3, 0),
    "D1": (16.8, 7.95, 0), "Q1": (12.6, 8.4, 0), "R13": (10.1, 7.6, 90),
    # RP2040. Every part a fixed route joins to one of its pins sits outside the 1 mm corridor that
    # each of the chip's pads keeps (escape_footprints): 1.0 mm out from the pad ends, plus clearance.
    "U1": (MCU[0], MCU[1], 270),
    # crystal left of XIN/XOUT (pins 20, 21): XIN over the top to pin 1, XOUT through R5 to pin 3
    "Y1": (20.8, 9.9, 270), "R5": (23.5, 11.15, 180), "C23": (18.5, 10.2, 270), "C24": (21.65, 12.95, 270),
    # left side: DVDD (pin 23) capacitor, IOVDD (pin 22) capacitor, the SWD connector. C20's pad
    # stops 1.2 mm short of the chip's pad corridors, so SWCLK, SWDIO and RUN can turn down past it
    "C20": (23.15, 12.5, 180), "C14": (19.9, 13.6, 0),
    "J6": (20.2, 17.9, 0),
    # top and bottom decoupling: C12 (pin 1) and C13 (pin 10) at the chip's top-left corner, through
    # the 3.3 V plane, so that the top-right corner is free for GPIO0, GPIO1, GPIO4 and GPIO6, which
    # cross to the bottom right; C15 and C16 below the unused pins (GPIO21-23) and pin 42. C15 is
    # turned so that its 3.3 V pad faces pin 33, for a short straight link (see PRIORITY)
    "C12": (25.3, 5.15, 0), "C13": (25.3, 6.2, 0), "C15": (29.0, 16.3, 270), "C16": (33.6, 15.9, 0),
    # right side, top to bottom: DVDD (pin 50) capacitor, USB resistors, VREG_VOUT (pin 45) capacitor,
    # then the 3.3 V capacitors of pins 49, 48, 44 and 43
    "C21": (36.4, 11.2, 0), "R3": (37.8, 12.25, 180), "R4": (37.8, 13.3, 180), "C11": (35.55, 14.1, 270),
    "C17": (39.6, 12.85, 90), "C10": (36.95, 14.75, 0), "C19": (38.9, 14.75, 0), "C18": (36.95, 15.75, 0),
    # flash right of the chip's QSPI pins; the BOOTSEL resistors right of the flash, in the strip
    # beside the battery connector, so the lane between the chip and the flash is the QSPI lines'
    "U2": (38.0, 6.45, 270), "C22": (39.6, 10.75, 90), "R6": (41.35, 4.6, 90), "R7": (41.75, 6.3, 0),
    # RESET, user and BOOTSEL buttons along the bottom right. BOOTSEL at the right end, under R6: its
    # line runs straight down the right edge, clear of the GPIO lines that cross to the bottom right
    "SW1": (33.2, 18.45, 0), "SW3": (38.1, 18.45, 0), "SW2": (43.1, 18.45, 0),
    # battery connector at the right end, facing right; VBAT test pad in the free top-right corner
    "J4": (45.85, 11.43, 90), "TP1": (43.2, 3.3, 0),
    # bench test pads on each rail (audit g2 spots)
    "TP2": (13.1, 12.9, 0), "TP3": (16.5, 10.2, 0), "TP4": (16.6, 4.8, 0), "TP5": (14.4, 10.7, 0), "TP6": (24.8, 9.7, 0),
    "TP7": (46.0, 5.8, 0),
}
_unplaced = sorted({p.ref for p in PARTS} - set(PLACEMENT))
assert not _unplaced, f"parts without a board position: {_unplaced}"
for _p in PARTS:
    _p.pcb = PLACEMENT[_p.ref]

# Laid before the autorouter, in this order, and locked (pcb_build.py place). The maze router lays
# each line the shortest way the lines before it leave free, so the order sets how they nest.
# * The core supply (+1V1): VREG_VOUT (pin 45), DVDD (pins 50 and 23) to their capacitors; IOVDD
#   pin 33 to C15 (left to the autorouter, they stayed apart in build 9).
# * The chip-side USB lines to their 27 ohm resistors.
# * QSPI, the flash's near row: IO0, CLK, IO3.
# * The crystal: XOUT through R5 to pin 3 and its load capacitor, then XIN to pin 1 and its
#   load capacitor, top layer.
# * USB from the receptacle: each line to its ESD pad (D- first, the lower line), the B-row contacts
#   joined to the A-row ones, then on to the 27 ohm resistors, under the chip.
# * +1V1 from C11 (pin 45) to C20 (pin 23). D+ from the receptacle runs under the chip to R3 and on
#   to pin 47, so it parts pin 45 from pins 50 and 23 on both layers; this link goes round the end
#   of D+ (its via beside R3) and under the chip on the bottom layer. Left to the autorouter, the
#   +1V1 pins stayed apart in builds 9 and 10. Pin 50 and C21 join it through the build's repair
#   step (a via beside C21; build 13).
# * QSPI, the flash's far row, in the order the lines nest between the chip and the flash: IO1
#   (pin 55) up the outer side of that lane and over the far row to pin 2, then IO2 (pin 54) up the
#   inner side and through the gap under the far row to pin 3, then CS (pin 56) outermost and over
#   the far row to pin 1. Three of the router keep-outs below hold IO1 to that path; with IO1 left
#   to the autorouter it stayed open in builds 6, 8 and 9.
# * GPIO4, GPIO0, GPIO1 and GPIO6, which leave the chip's top edge and cross under the flash on the
#   bottom layer to the user button and to TX, RX and D4 at the bottom right: GPIO4, whose end lies
#   furthest left, first, so that the others nest outside it. GPIO1 changes layer near the 16-pin
#   strip to cross GPIO0. The autorouter left one or more of them open in each of builds 6 to 9.
# * The battery line (VBAT, 0.3 mm) from J4 at the right end up to the test pad TP1 in the top-right
#   corner and on along the top edge, just under the 12-pin strip, to its BAT pin. Left to the
#   autorouter it ran under the bottom escapes and the buttons (build 3); routed straight from J4 to
#   the BAT pin it crossed under the middle of the chip (build 5). TP1 sets its way along the top.
# * BOOTSEL from R6 down the right edge to its button.
# * GPIO20 (MI), GPIO25 (D25), GPIO24 (D24) and GPIO27 (A1), each of which the autorouter left open
#   in at least one of builds 3, 7, 8 and 9 (the bottom edge is crowded by the buttons and the lines
#   to the 16-pin strip).
# * GPIO9 (D9) up to the 12-pin strip and GPIO19 (MO) down to the 16-pin strip: with the bench test pads
#   and the fiducials (P3) on the board, the autorouter left GPIO9 open in all three runs of the stage-2
#   build (30 Oct 2026) and GPIO19 in two; the top-right fiducial's copper-free square sits in front of
#   D9's pin. Laid first, the fiducials go round them.
# SWCLK, SWDIO and RUN are the autorouter's: past the chip's 1 mm pad corridors (which bind only
# the maze router) the column left of them beside C20 is 0.66 mm, room for two fixed lines, not
# three; the autorouter may use the corridors and has about 2 mm.
PRIORITY = [
    (("U1", "45"), ("C11", "1")), (("U1", "50"), ("C21", "1")), (("U1", "23"), ("C20", "1")),
    (("U1", "33"), ("C15", "1")),
    (("U1", "47"), ("R3", "2")), (("U1", "46"), ("R4", "2")),
    (("U1", "53"), ("U2", "5")), (("U1", "52"), ("U2", "6")), (("U1", "51"), ("U2", "7")),
    (("U1", "21"), ("R5", "1")), (("R5", "2"), ("Y1", "3")), (("C24", "1"), ("Y1", "3"), "join"),
    (("U1", "20"), ("Y1", "1")), (("C23", "1"), ("Y1", "1"), "join"),
    (("J1", "A7"), ("U3", "3")), (("J1", "A6"), ("U3", "2")),
    (("J1", "B7"), ("J1", "A7"), "join"), (("J1", "B6"), ("J1", "A6"), "join"),
    (("U3", "3"), ("R4", "1")), (("U3", "2"), ("R3", "1")),
    (("C11", "1"), ("C20", "1")),
    (("U1", "55"), ("U2", "2")), (("U1", "54"), ("U2", "3")), (("U1", "56"), ("U2", "1")),
    (("U1", "6"), ("SW3", "1")), (("U1", "2"), ("J2", "15")), (("U1", "3"), ("J2", "14")), (("U1", "8"), ("J2", "16")),
    (("J4", "1"), ("TP1", "1")), (("TP1", "1"), ("J3", "1")),
    (("R6", "2"), ("SW2", "1")),
    (("U1", "31"), ("J2", "13")), (("U1", "37"), ("J2", "10")), (("U1", "36"), ("J2", "9")),
    (("U1", "39"), ("J2", "6")),
    (("U1", "12"), ("J3", "8")), (("U1", "30"), ("J2", "12")),
]

TEXTS = [
    # front: what each button and connector is (the debug specification asks for "SWD")
    {"text": "RST", "x": 31.5, "y": 16.25, "size": 0.8}, {"text": "USR", "x": 39.3, "y": 16.4, "size": 0.8},
    {"text": "BOOT", "x": 43.1, "y": 16.35, "size": 0.8}, {"text": "SWD", "x": 20.2, "y": 14.8, "size": 0.8},
    {"text": "+", "x": 40.55, "y": 12.43, "size": 0.8}, {"text": "-", "x": 40.55, "y": 10.43, "size": 0.8},
    # back: designer and rights
    {"text": "EoS Feather RP2040  rev A", "x": 25.4, "y": 9.0, "size": 1.0, "layer": "B_SilkS", "bold": True, "mirror": True},
    {"text": "(c) 2026 Kartikeydheer Srivastava", "x": 25.4, "y": 11.0, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    {"text": "All rights reserved", "x": 25.4, "y": 12.4, "size": 0.8, "layer": "B_SilkS", "mirror": True},
]

BOARD = Board(
    name="eos-feather-rp2040",
    title="EoS Feather RP2040",
    revision="A",
    date="2026-10-22",
    company=OWNER,
    licence=LICENCE,
    contact=CONTACT,
    licence_terms=LICENCE_TERMS,
    credits=["Feather outline, corner holes, header positions and pin order: facts from Adafruit's Feather "
             "Specification (learn.adafruit.com/adafruit-feather/feather-specification), used as dimensions only",
             "Header signal assignment, user button on GPIO4 and battery polarity: facts from Adafruit's published "
             "Feather RP2040 pinout (product 4884), used as a pinout only",
             "SWD connector pinout: Raspberry Pi 3-pin Debug Connector Specification RP-003139-SP-4, used as facts only"],
    width=W,
    height=H,
    corner_radius=2.54,
    thickness=1.6,
    layers=4,
    planes=[("GND", "In1.Cu"), ("+3V3", "In2.Cu")],
    fanout_avoid=[MCU],
    # 0.45 mm vias with a 0.2 mm drill, as EoS CM4 Base and CM5 Base use on four layers, and 0.127 mm
    # (5 mil) tracks and clearance, a standard four-layer capability: with 0.15 mm rules full builds
    # 3, 6 and 7 ended with 6 to 10 unconnected items around the 0.4 mm-pitch QFN
    rules={"via": 0.45, "drill": 0.2, "min_via": 0.45, "min_drill": 0.2,
           "track": 0.127, "clearance": 0.127, "min_clearance": 0.127},
    # the QFN's supply pins take their plane vias inward, between the pad ring and the centre pad,
    # which leaves every pad's way out to its signal (escape_footprints, pcb_build.fanout)
    escape_footprints=["U1"],
    # the flash's ground and supply vias go in before the QSPI lines, which then go round them; C14's
    # too (build 6 left its 3.3 V pad without a via once the USB lines were in), C19's (build 12: the
    # GPIO lines that cross under it left its 3.3 V pad no via spot) and C15's ground pad (build 11:
    # boxed in by GPIO20, GPIO24 and GPIO25, it was a ground island without a via). C15's 3.3 V pad
    # takes no via of its own (one there boxes GPIO20 in): it shares pin 33's inward via, over their
    # 1.2 mm track.
    fanout_first=["U2", "C14", "C15", "C19"],
    no_fanout=["C15"],
    fanout_pads={"C15": ["2"]},
    # the bottom layer stays clear of other signals under the crystal and C23, under C24, and under
    # R5 and the XIN/XOUT lines from the chip. The top-layer keep-outs steer the maze router (they
    # reach the routers' input only, not the board): the gap under the flash's far row is closed just
    # right of pin 3, the flash's top-left corner and a strip up the lane between the chip and the
    # flash keep QSPI IO1 on the lane's outer side (IO2 then has the inner side and the gap), and a
    # strip between pins 5 and 6 makes GPIO4 change layer above its own pin instead of crossing the
    # escapes of GPIO0 to GPIO3 on the top layer
    router_keepouts=[(17.9, 7.6, 22.7, 12.1, "B.Cu"), (21.0, 12.0, 22.3, 14.0, "B.Cu"), (22.5, 7.6, 26.0, 11.5, "B.Cu"),
                     (37.65, 4.15, 37.95, 4.72, "F.Cu"), (35.45, 3.3, 35.85, 4.2, "F.Cu"), (35.27, 3.3, 35.45, 9.2, "F.Cu"),
                     (30.78, 4.0, 30.92, 6.25, "F.Cu")],
    priority_routes=PRIORITY,
    # vias cost the maze router as much as 3 mm of track (default 1.2): QSPI IO1 then keeps to the
    # top layer over the flash instead of a bottom-layer short cut across the GPIO lines' way
    maze_via_cost_mm=3.0,
    parts=PARTS,
    power_nets={"GND": "power:GND", "+3V3": "power:+3V3", "+1V1": "power:+1V1", "VBUS": "power:VBUS"},
    flagged_nets=["GND", "VBUS", "VBUS_F", "VSYS"],
    headings=[((30, 35), "USB-C, ESD, CC, fuse"), ((120, 35), "LiPo charger (MCP73831) and load sharing (AN1149)"),
              ((270, 35), "3.3 V regulator, Feather EN"), ((100, 185), "RP2040"),
              ((200, 185), "Core regulator and decoupling"), ((285, 150), "USB termination"),
              ((340, 35), "QSPI flash, BOOTSEL"), ((330, 135), "12 MHz crystal (ABM8-272-T3)"),
              ((425, 135), "Buttons"), ((345, 210), "D13 LED"), ((460, 220), "SWD and STEMMA QT"),
              ((465, 115), "Feather headers (male, on the back)"), ((40, 345), "Mounting holes"),
              ((35, 300), "Power nets")],
    power_block=(40.64, 315.0),
    notes=[((260, 320), "EoS Feather RP2040, rev A. Designed by Kartikeydheer Srivastava.\n"
                       "Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved; see LICENSE.txt.\n"
                       "Outline, holes and headers from Adafruit's Feather Specification; signals from the Feather RP2040 pinout.\n"
                       "Values: RP2040 datasheet and Hardware design with RP2040; MCP73831 DS20001984H; AN1149;\n"
                       "AP2112 DS39724; W25Q128JV Rev. F; SP05xxBA; 0805L; AO3401A; PMEG6010CEH; Kingbright; Omron B3U.\n"
                       "R7 (QSPI_SS pull-up) is not fitted. GPIO4 (user button) needs its internal pull-up in firmware.")],
    netclasses={
        "Power": {"track": 0.3, "clearance": 0.15},      # VBUS, the battery and the system rail (500 mA at most)
        "Fine": {"track": 0.2, "clearance": 0.15},       # supplies that enter the 0.4 mm-pitch QFN
        "USB": {"track": 0.2, "clearance": 0.15},
    },
    net_to_class={"VBUS": "Power", "VBUS_F": "Power", "VSYS": "Power", "VBAT": "Power",
                  "+3V3": "Fine", "+1V1": "Fine",
                  "USB_D+": "USB", "USB_D-": "USB", "RP_USB_DP": "USB", "RP_USB_DM": "USB"},
    # Bench data (BENCH-READY C): from the bench-ready audit g2 (24 Oct 2026), section 10
    rails=[
        Rail("VBUS", "USB-C J1", "5.0 V", "4.75-5.25 V (USB 2.0 VBUS at the connector)", ["TP2"],
             "about 10 kohm (R13 through F1)", link_note="Measure the board's whole current at the USB input."),
        Rail("VBUS_F", "F1 from VBUS; also the Feather USB pin (J3.3)", "5.0 V",
             "VBUS less F1's drop (0805L050: 0.85 ohm maximum)", ["TP3", "J3.3"], "about 10 kohm (R13)",
             link_note="No link: F1 already sits in series; measure its drop to get the current."),
        Rail("VSYS", "D1 from VBUS_F, Q1 from VBAT", "4.6 V from USB",
             "VBUS_F less up to 0.40 V at 0.1 A (PMEG6010CEH); VBAT less Q1's drop on battery", ["TP4"],
             "about 3.1 Mohm (R14 100 kohm into EN's internal pull-down; inferred)",
             link_note="No link: no room on this 50.8 x 22.86 mm board; measure at the USB input."),
        Rail("VBAT", "the cell on J4, charged by U4 MCP73831", "3.7 V",
             "a cell reads 3.0-4.2 V; the charger regulates 4.168-4.232 V (MCP73831-2: DS20001984H, DC "
             "Characteristics, page 3, VREG)",
             ["TP1", "J3.1"], "open (the charger and Q1 only)",
             link_note="No link: measure the cell's current in series with J4."),
        Rail("+3V3", "U5 AP2112K-3.3", "3.3 V", "3.25-3.35 V (AP2112K-3.3, 3.3 V +-1.5 %: Diodes DS39724 Rev. 2-2, "
             "AP2112-3.3 Electrical Characteristics, page 8)", ["TP5", "J2.2"],
             "open (ICs only)",
             link_note="No link between U5 and the 3.3 V plane: no room on this board (audit g2 fix 6); measure "
                       "the board's current at the USB input instead."),
        Rail("+1V1", "the RP2040's own regulator (VREG_VOUT)", "1.1 V",
             "1.067-1.133 V (1.1 V +-3 %: RP2040 datasheet, build 2025-02-20, section 2.10.7, Table 192, output "
             "voltage variation)", ["TP6"], "open",
             link_note="The RP2040's internal regulator: no link possible."),
        Rail("GND", "J1", "0 V", "-", ["TP7", "J2.4"], "-"),
    ],
    bringup=BringUp(
        supply="5.00 V into the USB-C socket J1, with no cell on J4",
        current_limit_ma=100,
        idle_current="about 10-25 mA",
        idle_source="estimate: the RP2040 in USB boot from a blank flash, AP2112K quiescent 55 uA, R13 0.5 mA (audit g2)",
        clock="USB enumeration in BOOTSEL shows the 12 MHz crystal working (it clocks USB through PLL_USB). With "
              "firmware, clock_gpio_init on GPIO24 or GPIO25 (D24 and D25, J2.9 and J2.10) puts a clock out to measure.",
        programming="UF2 in BOOTSEL (hold BOOT, tap RST, copy the UF2 file to the drive), or SWD on J6 with a "
                    "Raspberry Pi Debug Probe.",
        before_power=["Before fitting a cell, check its polarity with a meter: + must reach J4 pin 1 (README, Battery "
                      "polarity). A reversed cell puts about -3.7 V on VBAT, the charger and Q1."],
        tests=[
            BringUpTest("USB", "Hold BOOT, tap RST, connect to a computer", "an RPI-RP2 drive appears"),
            BringUpTest("User LED", "Blink GPIO13 (D13)", "D3 blinks"),
            BringUpTest("USER button", "Read GPIO4 with its internal pull-up, press SW3", "reads 1, then 0 while pressed"),
            BringUpTest("STEMMA QT", "I2C1 scan (GPIO2/3) with a known sensor on J5", "the sensor's address is found"),
            BringUpTest("UART", "Loop TX to RX on the header at 115200 Bd", "every byte sent comes back"),
            BringUpTest("ADC", "A0-A3 each read a divider of two equal 1 % resistors across 3V3 and GND",
                        "half of full scale within +-2 % (estimate: the resistors' 1 % plus the ADC's own error, "
                        "8.7 ENOB, RP2040 datasheet section 4.9.3; ratiometric, so the 3.3 V rail's tolerance "
                        "cancels)"),
            BringUpTest("EN", "Pull the EN pin (J3.2) to GND", "+3V3 at TP5 falls to 0 V"),
            BringUpTest("Charger", "Fit a checked cell (below 4.0 V) with USB connected",
                        "CHG LED on; 192-234 mA into the cell: 213 mA (1000 V / RPROG 4.7 kohm, DS20001984H "
                        "equation 5-1) +-10 %, the band DS20001984H's DC Characteristics (page 3, fast charge "
                        "current regulation) give at PROG 10 kohm and 2.0 kohm (inferred for 4.7 kohm)"),
            BringUpTest("Battery", "Unplug USB with the cell fitted", "+3V3 at TP5 stays 3.25-3.35 V"),
        ],
    ),
    temperature_range=(-25, 70, "SW1", "SW1-SW3 Omron B3U-1000P, rated -25 to +70 C (Omron catalogue A162-E1-07); "
                                       "the JST SH connectors J5 and J6 also stop at -25 C (JST eSH.pdf), while J4 "
                                       "(JST PH) is rated -40 to +105 C (JST ePH.pdf; parts review, 29 Oct 2026)"),
    pin_labels={
        "J2": {"1": "RST", "2": "3V", "3": "3V", "4": "GND", "5": "A0", "6": "A1", "7": "A2", "8": "A3", "9": "D24",
               "10": "D25", "11": "SCK", "12": "MO", "13": "MI", "14": "RX", "15": "TX", "16": "D4"},
        "J3": {"1": "BAT", "2": "EN", "3": "USB", "4": "D13", "5": "D12", "6": "D11", "7": "D10", "8": "D9", "9": "D6",
               "10": "D5", "11": "SCL", "12": "SDA"},
    },
)
