"""EoS CM4 Base: a carrier board for the Raspberry Pi Compute Module 4, designed by Kartikeydheer Srivastava.

Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved: this design file is not under
the repository's MIT licence; see boards/eos/eos-cm4-base/LICENSE.txt.

The CM4 plugs in through two 100-pin Hirose DF40C-100DS-0.4V connectors (1.5 mm stacking, CM4
datasheet section 3.1). Figure 4 of the CM4 and CM5 datasheets gives the two modules the same
outline, hole inset, connector offsets and wireless cut-out, and the CM5 datasheet (section 1.2)
says CM5 fits CM4 carriers; so the connectors and the four M2.5 holes sit where
reference/cm5_carrier.json puts them, and the tests check them there. Every pin's net follows
the CM4 datasheet's pinout (section 4, reference/cm4_pins.json).

The board is EoS CM5 Base's layout with the CM4's differences:

* Power in on USB-C, 5 V. VBUS feeds the module's six +5V pins (4.75-5.25 V). The CM4 does not
  negotiate USB-C power, so CC1 and CC2 each have 5.1 kohm to ground (a USB-C sink) and also go
  to AnalogIP1 and AnalogIP0 (pins 94, 96), which the datasheet says are "typically connected to
  CC pin of Type C power connector".
  - Use a 5 V / 3 A supply. The CM4 draws about 1.4 A when running (section 5.3), plus the
    USB-A port (0.5 A), the 3.3 V loads and the fan.
  - A computer's USB port may not power the board.
  - The header's 5 V pins share this rail with no diode, so a HAT must not feed 5 V while the
    board is unpowered.
* One USB 2.0 port, two connectors. The CM4 has a single USB 2.0 port (USB_P/USB_N, pins 105,
  103). A jumper (J9 5-6) chooses where it goes. A TI TS3USB30E switch routes it to the USB-C
  connector with the jumper open (device: rpiboot flashing, gadget mode) and to the USB-A
  connector with it fitted (host). The truth table: S low, D = D1; S high, D = D2; OE low
  enables. The same line is USB_OTG_ID (pin 101: "Internally pulled up. When grounded the CM4
  becomes a USB host but the correct OS driver also needs to be used").
  - The OS sets the role. Section 2.4: USB is off until otg_mode=1 enables it, and the ID pin
    is only read in OTG mode.
  - So set the jumper to match the OS: fitted for host, open for device. rpiboot always needs
    it open.
* The USB-A port sits on the top edge, next to the module's USB pins, so the host path is short:
  TI asks for equal-length lines no longer than 4 in (TS3USB30E section 8.4.1). The lengths
  are not matched; the generator does not match lengths.
* The USB-A port's 5 V comes through a TPS2051C (0.5 A, enable active high). A 2N7002 drives the
  enable: low while USB_OTG_ID is high, high (through 10 kohm to the CM4's 3.3 V) when the jumper
  grounds it. So the port is powered only in host mode and only while the CM4's 3.3 V rail is up.
  An enable tied straight to USB_OTG_ID would turn an active-low switch on whenever that rail is
  down. TI's application circuit: 0.1 uF and 10 uF at the input; 0.1 uF ceramic and 150 uF at the
  output (USB asks 120 uF per port).
* Gigabit Ethernet, microSD (CM4 Lite) and the 40-pin header exactly as on EoS CM5 Base: the
  CM4 uses the same pins for them.
* RUN_PG (pin 92) can be "driven low (via a 220 ohm resistor) to reset the CM4 CPU": a reset
  button through 220 ohm. PI_LED_nPWR (pin 95) "needs to be buffered": a BSS84 P-MOSFET drives
  the power LED. Pi_nLED_Activity (pin 21) sinks its LED directly (20 mA max).
* Jumpers: nRPIBOOT (USB boot), EEPROM write protect, USB host mode.
* No copper on any layer under the module's PCB antenna: the CM4 datasheet (section 3.1) wants
  no metal there and a ground-plane cut-out of at least 6.5 x 11 mm, ideally 8 x 15 mm. Figure 4
  puts it at the module's pin-99 edge, 18.5 mm up from the pin-200 edge.

Not on this board: HDMI, PCIe, camera and display (MIPI CSI/DSI). Each needs controlled-
impedance, length-matched differential pairs, which this generator does not route or verify.
The CM4 has no RTC battery input and no fan controller pins, so there is no coin cell and the
fan connector is a plain 5 V supply.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..design import NC, Board, Part, USB_C_EDGE
from .owner import CONTACT, LICENCE, LICENCE_TERMS, OWNER

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
REFERENCE = Path(__file__).resolve().parents[1] / "reference"
CM4 = json.loads((REFERENCE / "cm4_pins.json").read_text())
GEOMETRY = json.loads((REFERENCE / "cm5_carrier.json").read_text())


def res(ref, value, a, b, sch, desc):
    return Part(ref, "Device:R_Small", value, R0402, sch, {"1": a, "2": b}, fields={"Description": desc})


def cap(ref, value, a, b, sch, desc, fp=C0402):
    return Part(ref, "Device:C_Small", value, fp, sch, {"1": a, "2": b}, fields={"Description": desc})


# CM4 pin -> net. Pins not listed are left unconnected (the interfaces this board does not carry,
# and the inputs the datasheet says may float).
CM4_NETS = {pin: "GND" for pin, name in CM4["pins"].items() if name == "GND"}
CM4_NETS.update({pin: "+5V" for pin, name in CM4["pins"].items() if name == "+5V"})
CM4_NETS.update({pin: "+3V3" for pin, name in CM4["pins"].items() if name == "CM4_3.3V"})
CM4_NETS.update({pin: name for pin, name in CM4["pins"].items()
                 if name.startswith("GPIO") and name[4:].isdigit()})            # GPIO2-27 to the header
SPECIAL = {   # pin: (net, the datasheet's name for the pin), checked below
    "78": ("+3V3", "GPIO_VREF"),
    "3": ("ETH_D_P", "Ethernet_Pair3_P"), "5": ("ETH_D_N", "Ethernet_Pair3_N"),
    "4": ("ETH_B_P", "Ethernet_Pair1_P"), "6": ("ETH_B_N", "Ethernet_Pair1_N"),
    "9": ("ETH_C_N", "Ethernet_Pair2_N"), "11": ("ETH_C_P", "Ethernet_Pair2_P"),
    "10": ("ETH_A_N", "Ethernet_Pair0_N"), "12": ("ETH_A_P", "Ethernet_Pair0_P"),
    "15": ("ETH_NLED_ACT", "Ethernet_nLED3"), "17": ("ETH_NLED_SPD", "Ethernet_nLED2"),
    "20": ("EEPROM_NWP", "EEPROM_nWP"), "21": ("LED_NACT", "Pi_nLED_Activity"),
    "35": ("ID_SC", "ID_SC"), "36": ("ID_SD", "ID_SD"),
    "57": ("SD_CLK", "SD_CLK"), "62": ("SD_CMD", "SD_CMD"), "63": ("SD_DAT0", "SD_DAT0"),
    "67": ("SD_DAT1", "SD_DAT1"), "69": ("SD_DAT2", "SD_DAT2"), "61": ("SD_DAT3", "SD_DAT3"),
    "75": ("SD_PWR_ON", "SD_PWR_ON"),
    "92": ("RUN_PG", "RUN_PG"), "93": ("NRPIBOOT", "nRPIBOOT"),
    "94": ("CC1", "AnalogIP1"), "95": ("PI_LED_NPWR", "PI_LED_nPWR"), "96": ("CC2", "AnalogIP0"),
    "101": ("OTG_ID", "USB_OTG_ID"), "103": ("USB_N", "USB_N"), "105": ("USB_P", "USB_P"),
}
_wrong = {pin: (name, CM4["pins"][pin]) for pin, (_, name) in SPECIAL.items() if CM4["pins"][pin] != name}
assert not _wrong, f"pins whose datasheet name differs: {_wrong}"
CM4_NETS.update({pin: net for pin, (net, _) in SPECIAL.items()})
assert all(CM4["pins"][p] == "GND" for p, n in CM4_NETS.items() if n == "GND")


def cm4_connector(ref, first, sch):
    nets = {str(n): CM4_NETS.get(str(first + n - 1), NC) for n in range(1, 101)}
    return Part(ref, "EoS_Connectors:Conn_02x50_Odd_Even", f"CM4 {first}-{first + 99}",
                "Connector_Hirose_DF40:Hirose_DF40C-100DS-0.4V_2x50_P0.4mm", sch, nets,
                fields={"Manufacturer": "Hirose", "MPN": "DF40C-100DS-0.4V(51)",
                        "Description": f"CM4 connector, pins {first}-{first + 99}, 1.5 mm stacking (CM4 datasheet 3.1)"})


# Raspberry Pi 40-pin header
HEADER = ["+3V3", "+5V", "GPIO2", "+5V", "GPIO3", "GND", "GPIO4", "GPIO14", "GND", "GPIO15", "GPIO17", "GPIO18",
          "GPIO27", "GND", "GPIO22", "GPIO23", "+3V3", "GPIO24", "GPIO10", "GND", "GPIO9", "GPIO25", "GPIO11", "GPIO8",
          "GND", "GPIO7", "ID_SD", "ID_SC", "GPIO5", "GND", "GPIO6", "GPIO12", "GPIO13", "GND", "GPIO19", "GPIO16",
          "GPIO26", "GPIO20", "GND", "GPIO21"]

PARTS = [
    cm4_connector("J1", 1, (60, 120)),
    cm4_connector("J2", 101, (60, 260)),

    # ---- USB-C: power in, USB device side ---------------------------------------------------------
    Part("J3", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
         (160, 100), {"VBUS": "+5V", "GND": "GND", "CC1": "CC1", "CC2": "CC2", "D+": "USBC_DP", "D-": "USBC_DM",
                      "SBU1": NC, "SBU2": NC, "SHIELD": "GND"},
         fields={"Manufacturer": "Korean Hroparts", "MPN": "TYPE-C-31-M-12", "Description": "USB-C 2.0 receptacle (power in, USB device)"}),
    res("R6", "5.1k", "CC1", "GND", (140, 130), "Resistor 5.1 kohm 1% 0402 (USB-C sink, CC1; also to AnalogIP1)"),
    res("R7", "5.1k", "CC2", "GND", (155, 130), "Resistor 5.1 kohm 1% 0402 (USB-C sink, CC2; also to AnalogIP0)"),
    Part("U1", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", (200, 100),
         {"I/O1": "USBC_DP", "I/O2": "USBC_DM", "GND": "GND", "VBUS": "+5V"},
         fields={"Manufacturer": "STMicroelectronics", "MPN": "USBLC6-2SC6", "Description": "USB ESD protection (USB-C)"}),
    cap("C1", "10u", "+5V", "GND", (225, 95), "Capacitor 10 uF 10 V X5R 0805 (5 V at the module)", C0805),
    cap("C2", "10u", "+5V", "GND", (240, 95), "Capacitor 10 uF 10 V X5R 0805 (5 V at the module)", C0805),
    cap("C3", "100n", "+5V", "GND", (255, 95), "Capacitor 100 nF X7R 0402 (5 V at the module)"),

    # ---- USB 2.0 switch: device (USB-C) or host (USB-A), chosen by USB_OTG_ID ------------------------
    Part("U7", "Interface_USB:TS3USB30EDGSR", "TS3USB30E", "Package_SO:TSSOP-10_3x3mm_P0.5mm", (230, 160),
         {"S": "OTG_ID", "~{OE}": "GND", "VCC": "+3V3", "GND": "GND", "D+": "USB_P", "D-": "USB_N",
          "D1+": "USBH_DP", "D1-": "USBH_DM", "D2+": "USBC_DP", "D2-": "USBC_DM"},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TS3USB30EDGSR",
                 "Description": "USB 2.0 2:1 switch: S low (host) to USB-A, S high (device) to USB-C"}),
    cap("C9", "100n", "+3V3", "GND", (255, 155), "Capacitor 100 nF X7R 0402 (TS3USB30E VCC bypass, TI 8.3)"),
    res("R10", "10k", "OTG_ID", "+3V3", (205, 155), "Resistor 10 kohm 1% 0402 (USB_OTG_ID high: device mode by default)"),

    # ---- USB-A host -----------------------------------------------------------------------------------
    Part("U2", "Power_Management:TPS2051CDBV", "TPS2051C", "Package_TO_SOT_SMD:SOT-23-5", (300, 100),
         {"IN": "+5V", "OUT": "USBH_VBUS", "GND": "GND", "EN": "USBH_EN", "~{FLT}": NC},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPS2051CDBVR",
                 "Description": "USB power switch 0.5 A, enable active high: on in host mode, with the CM4's 3.3 V up"}),
    Part("Q2", "Transistor_FET:2N7002", "2N7002", "Package_TO_SOT_SMD:SOT-23", (300, 140),
         {"G": "OTG_ID", "S": "GND", "D": "USBH_EN"},
         fields={"Manufacturer": "Nexperia", "MPN": "2N7002,215",
                 "Description": "N-MOSFET inverter: USB_OTG_ID high (device) holds the USB-A switch off"}),
    res("R11", "10k", "USBH_EN", "+3V3", (285, 140), "Resistor 10 kohm 1% 0402 (USB-A switch enable pull-up, from the CM4's 3.3 V)"),
    cap("C4", "100n", "+5V", "GND", (280, 95), "Capacitor 100 nF X7R 0402 (TPS2051C input, TI application circuit)"),
    cap("C5", "10u", "+5V", "GND", (280, 115), "Capacitor 10 uF 10 V X5R 0805 (TPS2051C input bulk)", C0805),
    cap("C10", "100n", "USBH_VBUS", "GND", (320, 125), "Capacitor 100 nF X7R 0402 (TPS2051C output ceramic, TI application circuit)"),
    Part("C6", "Device:C_Polarized_Small", "150u", "Capacitor_SMD:CP_Elec_6.3x5.8", (325, 105), {"1": "USBH_VBUS", "2": "GND"},
         fields={"Manufacturer": "Panasonic", "MPN": "EEE-FK1A151P",
                 "Description": "Capacitor 150 uF 10 V aluminium, 6.3 x 5.8 mm (USB host port: 120 uF per TI)"}),
    Part("J4", "Connector:USB_A", "USB-A", "Connector_USB:USB_A_Molex_105057_Vertical", (360, 100),
         {"VBUS": "USBH_VBUS", "D-": "USBH_DM", "D+": "USBH_DP", "GND": "GND", "Shield": "GND"},
         fields={"Manufacturer": "Molex", "MPN": "105057-0001",
                 "Description": "USB-A receptacle, vertical, USB 2.0 host (on the top edge, by the module's USB pins)"}),
    Part("U3", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", (340, 130),
         {"I/O1": "USBH_DP", "I/O2": "USBH_DM", "GND": "GND", "VBUS": "USBH_VBUS"},
         fields={"Manufacturer": "STMicroelectronics", "MPN": "USBLC6-2SC6", "Description": "USB ESD protection (host port)"}),

    # ---- Gigabit Ethernet (as EoS CM5 Base) --------------------------------------------------------------
    Part("J5", "Connector_Generic:Conn_01x20", "TRJG0926HENL", "EoS_Connectors:TRXCOM_TRJG0926HENL", (420, 120),
         {"1": "ETH_A_P", "2": "ETH_A_N", "3": "ETH_B_P", "6": "ETH_B_N", "7": "ETH_C_P", "8": "ETH_C_N",
          "9": "ETH_D_P", "10": "ETH_D_N", "4": "ETH_CT", "5": "ETH_CT",
          "11": NC, "12": NC, "13": NC, "14": NC,
          "15": "+3V3", "16": "ETH_LEDY_K", "17": "+3V3", "18": "ETH_LEDG_K", "19": "GND", "20": "GND"},
         fields={"Manufacturer": "TRXCOM", "MPN": "TRJG0926HENL", "Description": "RJ45 MagJack 10/100/1000, LEDs"}),
    cap("C7", "100n", "ETH_CT", "GND", (450, 110), "Capacitor 100 nF X7R 0402 (MagJack centre tap)"),
    res("R1", "470", "ETH_LEDY_K", "ETH_NLED_SPD", (450, 130), "Resistor 470 ohm 1% 0402 (yellow LED, speed)"),
    res("R2", "470", "ETH_LEDG_K", "ETH_NLED_ACT", (465, 130), "Resistor 470 ohm 1% 0402 (green LED, activity)"),
    Part("U4", "EoS_Parts:TPD4EUSB30_FlowThrough", "TPD4EUSB30", "Package_SON:USON-10_2.5x1.0mm_P0.5mm", (420, 180),
         {"1": "ETH_A_P", "10": "ETH_A_P", "2": "ETH_A_N", "9": "ETH_A_N", "4": "ETH_B_P", "7": "ETH_B_P",
          "5": "ETH_B_N", "6": "ETH_B_N", "3": "GND", "8": "GND"},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPD4EUSB30DQAR",
                 "Description": "ESD protection, Ethernet pairs A and B, flow-through as TI lays it out"}),
    Part("U5", "EoS_Parts:TPD4EUSB30_FlowThrough", "TPD4EUSB30", "Package_SON:USON-10_2.5x1.0mm_P0.5mm", (480, 180),
         {"1": "ETH_C_P", "10": "ETH_C_P", "2": "ETH_C_N", "9": "ETH_C_N", "4": "ETH_D_P", "7": "ETH_D_P",
          "5": "ETH_D_N", "6": "ETH_D_N", "3": "GND", "8": "GND"},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPD4EUSB30DQAR",
                 "Description": "ESD protection, Ethernet pairs C and D, flow-through as TI lays it out"}),

    # ---- microSD (CM4 Lite, as EoS CM5 Base) ---------------------------------------------------------------
    Part("J6", "Connector:Micro_SD_Card", "microSD", "Connector_Card:microSD_HC_Molex_104031-0811", (520, 120),
         {"DAT2": "SD_DAT2", "DAT3/CD": "SD_DAT3", "CMD": "SD_CMD", "VDD": "SD_VDD", "CLK": "SD_CLK", "VSS": "GND",
          "DAT0": "SD_DAT0", "DAT1": "SD_DAT1", "SHIELD": "GND"},
         fields={"Manufacturer": "Molex", "MPN": "104031-0811", "Description": "microSD socket (CM4 Lite)"}),
    Part("U6", "Power_Management:RT9742AGJ5F", "RT9742GGJ5", "Package_TO_SOT_SMD:TSOT-23-5", (520, 180),
         {"VIN": "+3V3", "GND": "GND", "~{FLG}": NC, "EN": "SD_PWR_ON", "VOUT": "SD_VDD"},
         fields={"Manufacturer": "Richtek", "MPN": "RT9742GGJ5", "Description": "Load switch for the microSD supply, enable high"}),
    res("R3", "10k", "SD_PWR_ON", "+3V3", (500, 170), "Resistor 10 kohm 1% 0402 (SD_PWR_ON pull-up)"),
    cap("C8", "10u", "SD_VDD", "GND", (545, 175), "Capacitor 10 uF 10 V X5R 0805 (microSD supply)", C0805),

    # ---- 40-pin header, fan, controls, LEDs ----------------------------------------------------------------
    Part("J7", "Connector_Generic:Conn_02x20_Odd_Even", "GPIO", "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical",
         (420, 260), {str(i + 1): n for i, n in enumerate(HEADER)}, fields={"Description": "Raspberry Pi 40-pin GPIO header"}),
    Part("J8", "Connector:Conn_01x02_Pin", "FAN", "Connector_JST:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical",
         (520, 250), {"1": "+5V", "2": "GND"},
         fields={"Manufacturer": "JST", "MPN": "BM02B-SRSS-TB", "Description": "Fan: 1 5 V, 2 GND (the CM4 has no fan pins)"}),
    Part("SW1", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", (570, 250),
         {"1": "RUN_RST", "2": "GND"}, fields={"Manufacturer": "C&K", "MPN": "KMR221G LFS", "Description": "Reset button (RUN_PG through 220 ohm)"}),
    res("R8", "220", "RUN_PG", "RUN_RST", (550, 240), "Resistor 220 ohm 1% 0402 (RUN_PG reset, CM4 datasheet pin 92)"),
    Part("J9", "Connector_Generic:Conn_02x03_Odd_Even", "BOOT", "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical",
         (570, 300), {"1": "NRPIBOOT", "2": "GND", "3": "EEPROM_NWP", "4": "GND", "5": "OTG_ID", "6": "GND"},
         fields={"Description": "Jumpers: 1-2 nRPIBOOT (USB boot), 3-4 EEPROM write protect, 5-6 USB host mode"}),
    Part("Q1", "Transistor_FET:BSS84", "BSS84", "Package_TO_SOT_SMD:SOT-23", (285, 300),
         {"G": "PI_LED_NPWR", "S": "+3V3", "D": "LED_PWR_D"},
         fields={"Manufacturer": "Nexperia", "MPN": "BSS84,215", "Description": "P-MOSFET, power LED buffer (PI_LED_nPWR needs buffering)"}),
    res("R9", "100k", "PI_LED_NPWR", "+3V3", (265, 295), "Resistor 100 kohm 1% 0402 (keeps the LED buffer off while PI_LED_nPWR floats)"),
    res("R4", "1k", "LED_PWR_D", "LED_PWR_A", (300, 300), "Resistor 1 kohm 1% 0402 (power LED)"),
    Part("D1", "Device:LED_Small", "PWR", "LED_SMD:LED_0603_1608Metric", (315, 300), {"A": "LED_PWR_A", "K": "GND"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LSURCK", "Description": "LED red 0603, power (PI_LED_nPWR)"}),
    res("R5", "1k", "+3V3", "LED_ACT_A", (300, 330), "Resistor 1 kohm 1% 0402 (activity LED)"),
    Part("D2", "Device:LED_Small", "ACT", "LED_SMD:LED_0603_1608Metric", (315, 330), {"A": "LED_ACT_A", "K": "LED_NACT"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LCGCK", "Description": "LED green 570 nm 0603, activity (Pi_nLED_Activity)"}),
]
for i in range(4):
    PARTS.append(Part(f"H{i + 1}", "Mechanical:MountingHole", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5",
                      (60 + 20 * i, 360), {}, fields={"Description": "CM4 mounting hole, M2.5"}))

# Board placement: (x, y, rotation) in mm, origin top-left, as EoS CM5 Base: the module's long
# side along x, Raspberry Pi's footprint frame (origin mounting hole MH1) turned 90 degrees, MH1
# at MODULE. Nothing is placed under the module on the top side (1.5 mm stacking leaves no room).
W, H = 90.0, 80.0
MODULE = (58.0, 46.0)


def from_cm5(fx, fy):
    """A point in Raspberry Pi's CM5 footprint frame (shared by the CM4), on this board."""
    return MODULE[0] + fy, MODULE[1] - fx


def from_module(x, y):
    """A point in the datasheets' Figure 4 (top view, mm from the module's top-left corner, pins
    99/100 at the top left) on this board: MH1 sits 3.5 mm in from that corner."""
    return from_cm5(y - 3.5, 3.5 - x)


# Antenna cut-out (CM4 datasheet section 3.1 and Figure 4): 6.5 mm in from the pin-99 edge, 11 mm
# tall, its lower side 18.5 mm up from the 40 mm module's bottom edge. The board keeps the
# datasheet's ideal 8 x 15 mm clear around it.
ANTENNA_CUTOUT = (0.0, 10.5, 6.5, 21.5)
_a, _b = from_module(-1.5, 8.5), from_module(6.5, 23.5)
ANTENNA_KEEPOUT = (min(_a[0], _b[0]), min(_a[1], _b[1]), max(_a[0], _b[0]), max(_a[1], _b[1]))

HOLES = [from_cm5(h[0] / 1e6, h[1] / 1e6) for h in GEOMETRY["holes"]]
PLACEMENT = {
    "J1": (*from_cm5(-0.5, -21.5), 0), "J2": (*from_cm5(33.5, -21.5), 0),
    **{f"H{i + 1}": (x, y, 0) for i, (x, y) in enumerate(HOLES)},
    # top edge, between the board edge and the module: USB-C near the left corner, its CC resistors
    # and ESD beside it, clear of the USB pair that leaves the module's USB pins (CM4 pins 103/105,
    # J2's left end) for the USB switch next to them; the
    # USB-A port's ESD and the vertical USB-A port to its right, so the host path stays short
    "J3": (12.0, USB_C_EDGE, 180), "R6": (20.5, 1.4, 0), "R7": (20.5, 3.0, 0), "U1": (20.5, 6.6, 0),
    "U7": (32.6, 4.6, 0), "C9": (34.2, 7.8, 0), "R10": (31.0, 7.8, 0),
    "U3": (37.9, 4.5, 90), "J4": (45.0, 6.8, 0),
    "C1": (40.0, 51.6, 0), "C2": (43.6, 51.6, 0), "C3": (46.6, 51.6, 0),
    # right of the module, at least 10 mm from the antenna: the USB-A power switch, its inverter
    # and capacitors; LEDs, reset button, jumpers, fan
    "U2": (68.0, 8.0, 0), "C4": (64.6, 6.0, 90), "C5": (64.6, 10.4, 90), "C10": (71.4, 8.0, 90),
    "Q2": (68.0, 12.6, 0), "R11": (71.4, 12.6, 90), "C6": (78.4, 15.6, 0),
    "R4": (65.0, 43.5, 0), "D1": (68.6, 43.5, 180), "R5": (65.0, 45.5, 0), "D2": (68.6, 45.5, 180),
    "Q1": (72.6, 43.6, 0), "R9": (72.6, 46.4, 0),
    "SW1": (84.0, 42.5, 90), "R8": (80.4, 42.5, 90), "J9": (84.5, 22.0, 0), "J8": (78.0, 4.0, 0),
    # right edge, lower: microSD and its supply switch
    "J6": (82.0, 62.0, 90), "U6": (72.0, 56.0, 0), "R3": (72.0, 52.6, 0), "C8": (72.0, 59.4, 0),
    # bottom left: the MagJack by the Ethernet pins, its ESD, centre-tap capacitor, LED resistors
    "J5": (10.75, 60.0, 270), "U4": (23.0, 55.4, 0), "U5": (23.0, 62.4, 0), "C7": (29.0, 53.0, 90),
    "R1": (25.5, 59.0, 0), "R2": (25.5, 61.0, 0),
    # bottom edge: the 40-pin header
    "J7": (24.5, 76.5, 90),
}
_unplaced = sorted({p.ref for p in PARTS} - set(PLACEMENT))
assert not _unplaced, f"parts without a board position: {_unplaced}"
for _p in PARTS:
    _p.pcb = PLACEMENT[_p.ref]

# The Ethernet pairs are routed first, as on EoS CM5 Base: outer row first, connector pin order,
# each line through its ESD part flow-through.
_ETH = [("3", "9"), ("5", "10"), ("9", "8"), ("11", "7"), ("4", "3"), ("6", "6"), ("10", "2"), ("12", "1")]
_FLOW = {"9": ("U5", "7", "4"), "10": ("U5", "6", "5"), "8": ("U5", "9", "2"), "7": ("U5", "10", "1"),
         "3": ("U4", "7", "4"), "6": ("U4", "6", "5"), "2": ("U4", "9", "2"), "1": ("U4", "10", "1")}
PRIORITY = [r for cm, jack in _ETH for esd, inner, outer in [_FLOW[jack]]
            for r in ((("J1", cm), (esd, inner)), ((esd, inner), (esd, outer)), ((esd, outer), ("J5", jack)))]
# The USB pair from the module to the switch. Both leave the connector's inner row next to its
# pin-101 end and wrap round that end, so the line nearer the end goes first, as with Ethernet.
# Then the host pair from the switch through its ESD part (in on one pad, out on the other of the
# same line) to the USB-A port. The ESD part's VBUS pin 5 sits between the pair's two outer-row
# pads and goes first, through the channel between the pad rows to the port's VBUS pin: laid
# after the pair, it is walled in on the top layer, and no via may sit in its pad.
PRIORITY += [(("J2", "3"), ("U7", "6")),       # USB_N (CM4 pin 103) to D-
             (("J2", "5"), ("U7", "4")),       # USB_P (CM4 pin 105) to D+
             # ~OE (pin 9, tied low) sits between signal pads with no room for a ground via: join it
             # under the package to the switch's own GND pin 5
             (("U7", "9"), ("U7", "5"), "join"),
             (("U7", "10"), ("C9", "1")),      # VCC to its capacitor, before D+ can wrap round the pin
             (("U3", "5"), ("J4", "1")),       # USBH_VBUS to the ESD part's reference pin
             (("U7", "8"), ("U3", "3")), (("U3", "4"), ("J4", "2")),     # USBH_DM: D1- through I/O2
             (("U7", "2"), ("U3", "1")), (("U3", "6"), ("J4", "3"))]     # USBH_DP: D1+ through I/O1
# Three microSD lines run first, shortest first, so they nest inside one another on the top layer:
# DAT1, DAT0 and CLK leave the connector's outer row in the order they reach the socket. CMD (from
# the inner row), DAT3 and DAT2 must cross them; the autorouter, which plans crossings for the
# whole board at once, takes those. Routed one by one, the crossing lines box each other in.
SD_BUS = [(("J1", "67"), ("J6", "8")), (("J1", "63"), ("J6", "7")), (("J1", "57"), ("J6", "5"))]
PRIORITY += SD_BUS
TEXTS = [
    {"text": "EoS CM4 Base  rev A", "x": 45.0, "y": 66.0, "size": 1.2, "bold": True},
    {"text": "EoS CM4 Base  rev A", "x": 62.0, "y": 60.0, "size": 1.0, "layer": "B_SilkS", "bold": True, "mirror": True},
    {"text": "(c) 2026 Kartikeydheer Srivastava", "x": 62.0, "y": 62.0, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    {"text": "All rights reserved", "x": 62.0, "y": 63.4, "size": 0.8, "layer": "B_SilkS", "mirror": True},
]

BOARD = Board(
    name="eos-cm4-base",
    title="EoS CM4 Base",
    revision="A",
    date="2026-10-12",
    company=OWNER,
    licence=LICENCE,
    contact=CONTACT,
    licence_terms=LICENCE_TERMS,
    credits=["CM4 pinout: Raspberry Pi Compute Module 4 datasheet, section 4 (facts only)",
             "Connector and mounting-hole positions: the CM5 footprint in Raspberry Pi's CM5 IO Board files, "
             "which Figure 4 of the CM4 and CM5 datasheets shows the CM4 shares (facts only)"],
    width=W,
    height=H,
    corner_radius=3.0,
    rules={"via": 0.45, "drill": 0.2, "min_via": 0.45, "min_drill": 0.2},
    thickness=1.6,
    layers=4,
    planes=[("GND", "In1.Cu"), ("+5V", "In2.Cu")],
    local_footprints=["EoS_Connectors"],
    copper_keepouts=[ANTENNA_KEEPOUT],
    priority_routes=PRIORITY,
    fanout_first=["U3"],          # the ESD part's ground via goes in before D- passes below the package
    escape_footprints=["J1", "J2"],
    maze_via_cost_mm=8.0,
    parts=PARTS,
    power_nets={"GND": "power:GND", "+5V": "power:+5V", "+3V3": "power:+3V3"},
    flagged_nets=["GND", "+5V", "+3V3"],
    headings=[((40, 75), "CM4 connectors (pins 1-100, 101-200)"), ((150, 75), "USB-C: power in, USB device"),
              ((200, 145), "USB 2.0 switch: device (USB-C) or host (USB-A)"), ((270, 75), "USB-A host"),
              ((400, 75), "Gigabit Ethernet"), ((500, 75), "microSD (CM4 Lite)"), ((400, 235), "40-pin GPIO header"),
              ((500, 230), "Fan, reset, jumpers"), ((260, 280), "LEDs"),
              ((40, 345), "CM4 mounting holes"), ((35, 300), "Power nets")],
    power_block=(40.64, 315.0),
    notes=[((150, 385), "EoS CM4 Base, rev A. Designed by Kartikeydheer Srivastava.\n"
                       "Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved; see LICENSE.txt.\n"
                       "Pin nets per the CM4 datasheet (section 4). USB_OTG_ID selects host (USB-A) or device (USB-C).\n"
                       "No HDMI, PCIe or MIPI: they need impedance-controlled, length-matched pairs.")],
    netclasses={"Power": {"track": 0.5, "clearance": 0.15}, "USB": {"track": 0.2, "clearance": 0.15},
                "Ethernet": {"track": 0.2, "clearance": 0.15}},
    net_to_class={"+5V": "Power", "USBH_VBUS": "Power", "USB_P": "USB", "USB_N": "USB", "USBH_DP": "USB", "USBH_DM": "USB",
                  "USBC_DP": "USB", "USBC_DM": "USB", **{f"ETH_{p}_{s}": "Ethernet" for p in "ABCD" for s in "PN"}},
)
