"""EoS CM5 Base: a carrier board for the Raspberry Pi Compute Module 5, designed by Kartikeydheer Srivastava.

Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved: this design file is not under
the repository's MIT licence; see boards/eos/eos-cm5-base/LICENSE.txt.

The CM5 plugs in through two 100-pin connectors (Amphenol 10164227-1001A1RLF, 1.5 mm stacking,
on KiCad's Hirose DF40C-100DS footprint, which has the same land pattern). Their pads and the
module's four M2.5 holes sit exactly where Raspberry Pi's CM5 footprint puts them; the
connectors and holes are checked against reference/cm5_carrier.json in the tests. Every pin's
net follows the CM5 datasheet (table 4). Where the datasheet leaves a choice, the circuit
follows Raspberry Pi's own CM5 IO Board (CM5IO) design files.

What is on it, and why:

* Power and USB 2.0 on one USB-C connector. VBUS feeds the module's six 5 V pins (4.75-5.25 V).
  CC1 and CC2 go straight to the module (pins 94, 96), which negotiates 5 A at 5 V itself, so
  the carrier has no CC resistors. USB_P/USB_N (pins 105, 103) go to the same connector, with
  USBLC6-2SC6 ESD protection, for rpiboot flashing and USB gadget use. USB_OTG_ID is left
  floating, so the CM5 is a USB device on this port.
* A USB 2.0 host port (USB-A) on the USB 2.0 pair of the module's first USB 3.0 port (pins 134,
  136). Its 5 V comes through a TPS2051C (0.5 A, enable active high), switched by VBUS_EN (pin
  111). Following TI: 0.1 uF plus 10 uF ceramic on the input and 150 uF on the output (USB needs
  at least 120 uF).
* Gigabit Ethernet through a TRXCOM TRJG0926HENL MagJack, wired as on CM5IO: pairs 0-3 to the
  jack's TRD0-TRD3, its common centre tap through 100 nF to ground, and the line-side taps
  left open (CM5IO takes them only to a PoE header). The green LED shows activity
  (Ethernet_nLED3, pin 15) and the yellow LED shows speed (nLED2, pin 17), each through 470 ohm
  from 3.3 V. Two TPD4EUSB30 protect the pairs. The jack sits next to the module's Ethernet
  pins, so the pairs stay short.
* microSD, for the CM5 Lite: SD_CLK, SD_CMD and SD_DAT0-3 go direct; the card's 3.3 V comes
  through an RT9742GGJ5 switch enabled by SD_PWR_ON (pin 75, 10 kohm pull-up to 3.3 V), with
  10 uF on its output, as on CM5IO. SD_VDD_OVERRIDE (pin 73) is left open.
* The standard 40-pin GPIO header, GPIO_VREF (pin 78) tied to CM5_3.3V (pins 84, 86) for
  3.3 V GPIO, as the datasheet requires. Header 3.3 V comes from CM5_3.3V (600 mA in total).
* Fan connector (pin 1 5 V, 2 PWM, 3 GND, 4 tacho), RTC coin cell on VBAT (pin 76), power
  button (PWR_Button, pin 92), nRPIBOOT and EEPROM_nWP on a jumper header (both left floating
  unless jumpered, as the datasheet allows). Power LED (LED_nPWR, pin 95) and activity LED
  (LED_nACT, pin 21) each through 1 kohm from 3.3 V, as on CM5IO.

* No copper on any layer under the module's PCB antenna. The CM5 datasheet (section 4.1.2) says
  "Don't place any metal, including ground planes, directly beneath the antenna" and asks for a
  ground-plane cut-out of at least 6.5 x 11 mm, ideally 8 x 15 mm. Its Figure 4 puts the
  6.5 x 11 mm cut-out at the module's pin-99 edge, 18.5 mm up from the pin-200 edge. The board
  keeps the larger 8 x 15 mm clear, on every layer, around that spot.

Not on this board: HDMI, PCIe, USB 3.0 SuperSpeed, and the camera and display (MIPI)
interfaces. Each needs controlled-impedance, length-matched differential pairs, which this
generator does not route or verify.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..design import NC, Board, Part, USB_C_EDGE
from .owner import CONTACT, LICENCE, LICENCE_TERMS, OWNER

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
CM5 = json.loads((Path(__file__).resolve().parents[1] / "reference" / "cm5_carrier.json").read_text())


def res(ref, value, a, b, sch, desc):
    return Part(ref, "Device:R_Small", value, R0402, sch, {"1": a, "2": b}, fields={"Description": desc})


def cap(ref, value, a, b, sch, desc, fp=C0402):
    return Part(ref, "Device:C_Small", value, fp, sch, {"1": a, "2": b}, fields={"Description": desc})


# CM5 pin -> net. Pins not listed are left unconnected (the interfaces this board does not carry,
# and the inputs the datasheet says may float).
CM5_NETS = {pin: "GND" for pin, name in CM5["pins"].items() if name == "GND"}
CM5_NETS.update({pin: "+5V" for pin, name in CM5["pins"].items() if name == "5V"})
CM5_NETS.update({pin: "+3V3" for pin, name in CM5["pins"].items() if name == "CM5_3.3V"})
CM5_NETS.update({pin: name for pin, name in CM5["pins"].items()
                 if name.startswith("GPIO") and name[4:].isdigit()})            # GPIO2-27 to the header
CM5_NETS.update({
    "78": "+3V3",                                       # GPIO_VREF: 3.3 V GPIO
    "3": "ETH_D_P", "5": "ETH_D_N", "4": "ETH_B_P", "6": "ETH_B_N",          # Pair3 / Pair1
    "9": "ETH_C_N", "11": "ETH_C_P", "10": "ETH_A_N", "12": "ETH_A_P",       # Pair2 / Pair0
    "15": "ETH_NLED_ACT", "17": "ETH_NLED_SPD",
    "16": "FAN_TACHO", "19": "FAN_PWM", "20": "EEPROM_NWP", "21": "LED_NACT",
    "35": "ID_SC", "36": "ID_SD",
    "57": "SD_CLK", "62": "SD_CMD", "63": "SD_DAT0", "67": "SD_DAT1", "69": "SD_DAT2", "61": "SD_DAT3",
    "75": "SD_PWR_ON", "76": "VBAT",
    "92": "PWR_BUTTON", "93": "NRPIBOOT", "94": "CC1", "95": "LED_NPWR", "96": "CC2",
    "103": "USB_N", "105": "USB_P", "111": "VBUS_EN",
    "134": "USBH_DP", "136": "USBH_DM",
})
assert all(CM5["pins"][p] == "GND" for p, n in CM5_NETS.items() if n == "GND")


def cm5_connector(ref, first, sch):
    nets = {str(n): CM5_NETS.get(str(first + n - 1), NC) for n in range(1, 101)}
    return Part(ref, "EoS_Connectors:Conn_02x50_Odd_Even", f"CM5 {first}-{first + 99}",
                "Connector_Hirose_DF40:Hirose_DF40C-100DS-0.4V_2x50_P0.4mm", sch, nets,
                fields={"Manufacturer": "Amphenol", "MPN": "10164227-1001A1RLF",
                        "Description": f"CM5 connector, pins {first}-{first + 99}, 1.5 mm stacking"})


# Raspberry Pi 40-pin header, as on CM5IO
HEADER = ["+3V3", "+5V", "GPIO2", "+5V", "GPIO3", "GND", "GPIO4", "GPIO14", "GND", "GPIO15", "GPIO17", "GPIO18",
          "GPIO27", "GND", "GPIO22", "GPIO23", "+3V3", "GPIO24", "GPIO10", "GND", "GPIO9", "GPIO25", "GPIO11", "GPIO8",
          "GND", "GPIO7", "ID_SD", "ID_SC", "GPIO5", "GND", "GPIO6", "GPIO12", "GPIO13", "GND", "GPIO19", "GPIO16",
          "GPIO26", "GPIO20", "GND", "GPIO21"]

PARTS = [
    cm5_connector("J1", 1, (60, 120)),
    cm5_connector("J2", 101, (60, 260)),

    # ---- USB-C: power in, USB 2.0 device --------------------------------------------------------
    Part("J3", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
         (160, 100), {"VBUS": "+5V", "GND": "GND", "CC1": "CC1", "CC2": "CC2", "D+": "USB_P", "D-": "USB_N",
                      "SBU1": NC, "SBU2": NC, "SHIELD": "GND"},
         fields={"Manufacturer": "Korean Hroparts", "MPN": "TYPE-C-31-M-12", "Description": "USB-C 2.0 receptacle (power in, USB device)"}),
    Part("U1", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", (200, 100),
         {"I/O1": "USB_P", "I/O2": "USB_N", "GND": "GND", "VBUS": "+5V"},
         fields={"Manufacturer": "STMicroelectronics", "MPN": "USBLC6-2SC6", "Description": "USB ESD protection"}),
    cap("C1", "10u", "+5V", "GND", (225, 95), "Capacitor 10 uF 10 V X5R 0805 (5 V at the module)", C0805),
    cap("C2", "10u", "+5V", "GND", (240, 95), "Capacitor 10 uF 10 V X5R 0805 (5 V at the module)", C0805),
    cap("C3", "100n", "+5V", "GND", (255, 95), "Capacitor 100 nF X7R 0402 (5 V at the module)"),

    # ---- USB-A host -----------------------------------------------------------------------------------
    Part("U2", "Power_Management:TPS2051CDBV", "TPS2051C", "Package_TO_SOT_SMD:SOT-23-5", (300, 100),
         {"IN": "+5V", "OUT": "USBH_VBUS", "GND": "GND", "EN": "VBUS_EN", "~{FLT}": NC},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPS2051CDBVR", "Description": "USB power switch 0.5 A, enable high"}),
    cap("C4", "100n", "+5V", "GND", (280, 95), "Capacitor 100 nF X7R 0402 (TPS2051C input, as TI specifies)"),
    cap("C5", "10u", "+5V", "GND", (280, 115), "Capacitor 10 uF 10 V X5R 0805 (TPS2051C input, 1-22 uF per TI)", C0805),
    Part("C6", "Device:C_Polarized_Small", "150u", "Capacitor_SMD:CP_Elec_6.3x5.8", (325, 105), {"1": "USBH_VBUS", "2": "GND"},
         fields={"Manufacturer": "Panasonic", "MPN": "EEE-FK1A151P",
                 "Description": "Capacitor 150 uF 10 V aluminium, 6.3 x 5.8 mm (USB host port: 120 uF minimum per TI)"}),
    Part("J4", "Connector:USB_A", "USB-A", "Connector_USB:USB_A_Molex_67643_Horizontal", (360, 100),
         {"VBUS": "USBH_VBUS", "D-": "USBH_DM", "D+": "USBH_DP", "GND": "GND", "Shield": "GND"},
         fields={"Manufacturer": "Molex", "MPN": "67643-0910", "Description": "USB-A receptacle, USB 2.0 host"}),
    Part("U3", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", (340, 130),
         {"I/O1": "USBH_DP", "I/O2": "USBH_DM", "GND": "GND", "VBUS": "USBH_VBUS"},
         fields={"Manufacturer": "STMicroelectronics", "MPN": "USBLC6-2SC6", "Description": "USB ESD protection (host port)"}),

    # ---- Gigabit Ethernet ---------------------------------------------------------------------------
    Part("J5", "Connector_Generic:Conn_01x20", "TRJG0926HENL", "EoS_Connectors:TRXCOM_TRJG0926HENL", (420, 120),
         {"1": "ETH_A_P", "2": "ETH_A_N", "3": "ETH_B_P", "6": "ETH_B_N", "7": "ETH_C_P", "8": "ETH_C_N",
          "9": "ETH_D_P", "10": "ETH_D_N", "4": "ETH_CT", "5": "ETH_CT",
          "11": NC, "12": NC, "13": NC, "14": NC,
          "15": "+3V3", "16": "ETH_LEDY_K", "17": "+3V3", "18": "ETH_LEDG_K", "19": "GND", "20": "GND"},
         fields={"Manufacturer": "TRXCOM", "MPN": "TRJG0926HENL",
                 "Description": "RJ45 MagJack 10/100/1000, LEDs (pins as on Raspberry Pi's CM5IO)"}),
    cap("C7", "100n", "ETH_CT", "GND", (450, 110), "Capacitor 100 nF X7R 0402 (MagJack centre tap, as CM5IO)"),
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

    # ---- microSD (CM5 Lite) -----------------------------------------------------------------------------
    Part("J6", "Connector:Micro_SD_Card", "microSD", "Connector_Card:microSD_HC_Molex_104031-0811", (520, 120),
         {"DAT2": "SD_DAT2", "DAT3/CD": "SD_DAT3", "CMD": "SD_CMD", "VDD": "SD_VDD", "CLK": "SD_CLK", "VSS": "GND",
          "DAT0": "SD_DAT0", "DAT1": "SD_DAT1", "SHIELD": "GND"},
         fields={"Manufacturer": "Molex", "MPN": "104031-0811", "Description": "microSD socket (CM5 Lite)"}),
    Part("U6", "Power_Management:RT9742AGJ5F", "RT9742GGJ5", "Package_TO_SOT_SMD:TSOT-23-5", (520, 180),
         {"VIN": "+3V3", "GND": "GND", "~{FLG}": NC, "EN": "SD_PWR_ON", "VOUT": "SD_VDD"},
         fields={"Manufacturer": "Richtek", "MPN": "RT9742GGJ5", "Description": "Load switch for the microSD supply, enable high (as CM5IO)"}),
    res("R3", "10k", "SD_PWR_ON", "+3V3", (500, 170), "Resistor 10 kohm 1% 0402 (SD_PWR_ON pull-up, as CM5IO)"),
    cap("C8", "10u", "SD_VDD", "GND", (545, 175), "Capacitor 10 uF 10 V X5R 0805 (microSD supply, as CM5IO)", C0805),

    # ---- 40-pin header, fan, RTC, controls, LEDs ------------------------------------------------------
    Part("J7", "Connector_Generic:Conn_02x20_Odd_Even", "GPIO", "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical",
         (420, 260), {str(i + 1): n for i, n in enumerate(HEADER)}, fields={"Description": "Raspberry Pi 40-pin GPIO header"}),
    Part("J8", "Connector:Conn_01x04_Pin", "FAN", "Connector_JST:JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical",
         (520, 250), {"1": "+5V", "2": "FAN_PWM", "3": "GND", "4": "FAN_TACHO"},
         fields={"Manufacturer": "JST", "MPN": "BM04B-SRSS-TB", "Description": "Fan: 1 5 V, 2 PWM, 3 GND, 4 tacho"}),
    Part("BT1", "Device:Battery_Cell", "CR2032", "Battery:BatteryHolder_Keystone_3034_1x20mm", (520, 300),
         {"+": "VBAT", "-": "GND"},
         fields={"Manufacturer": "Keystone", "MPN": "3034", "Description": "Coin cell holder, RTC (VBAT); keep RTC charging off with a CR2032"}),
    Part("SW1", "Switch:SW_Push", "POWER", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", (570, 250),
         {"1": "PWR_BUTTON", "2": "GND"}, fields={"Manufacturer": "C&K", "MPN": "KMR221G LFS", "Description": "Power button (PWR_Button)"}),
    Part("J9", "Connector_Generic:Conn_02x02_Odd_Even", "BOOT", "Connector_PinHeader_2.54mm:PinHeader_2x02_P2.54mm_Vertical",
         (570, 300), {"1": "NRPIBOOT", "2": "GND", "3": "EEPROM_NWP", "4": "GND"},
         fields={"Description": "Jumpers: 1-2 nRPIBOOT (USB boot), 3-4 EEPROM write protect"}),
    res("R4", "1k", "+3V3", "LED_PWR_A", (300, 300), "Resistor 1 kohm 1% 0402 (power LED, as CM5IO)"),
    Part("D1", "Device:LED_Small", "PWR", "LED_SMD:LED_0603_1608Metric", (315, 300), {"A": "LED_PWR_A", "K": "LED_NPWR"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LSURCK", "Description": "LED red 0603, power (LED_nPWR)"}),
    res("R5", "1k", "+3V3", "LED_ACT_A", (300, 330), "Resistor 1 kohm 1% 0402 (activity LED, as CM5IO)"),
    Part("D2", "Device:LED_Small", "ACT", "LED_SMD:LED_0603_1608Metric", (315, 330), {"A": "LED_ACT_A", "K": "LED_NACT"},
         fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LCGCK", "Description": "LED green 570 nm 0603, activity (LED_nACT)"}),
]
for i in range(4):
    PARTS.append(Part(f"H{i + 1}", "Mechanical:MountingHole", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5",
                      (60 + 20 * i, 360), {}, fields={"Description": "CM5 mounting hole, M2.5"}))

# Board placement: (x, y, rotation) in mm, origin top-left. The CM5 lies with its long side
# along x: Raspberry Pi's footprint frame (origin mounting hole MH1) turned 90 degrees, MH1 at
# MODULE. Nothing is placed under the module on the top side (1.5 mm stacking leaves no room).
# USB-C on the top edge by the USB pins; the MagJack bottom-left by the Ethernet pins; USB-A and
# microSD on the right edge; the 40-pin header along the bottom edge.
W, H = 90.0, 80.0
MODULE = (58.0, 46.0)


def from_cm5(fx, fy):
    """A point in Raspberry Pi's CM5 footprint frame, on this board (the frame turned 90 degrees)."""
    return MODULE[0] + fy, MODULE[1] - fx


CM5_HOLES = [from_cm5(h[0] / 1e6, h[1] / 1e6) for h in CM5["holes"]]


def from_module(x, y):
    """A point in the CM5 datasheet's Figure 4 (top view, mm from the module's top-left corner,
    pins 99/100 at the top left) on this board: MH1 sits 3.5 mm in from that corner."""
    return from_cm5(y - 3.5, 3.5 - x)


# Antenna cut-out (datasheet section 4.1.2 and Figure 4): 6.5 mm in from the pin-99 edge, 11 mm
# tall, its lower side 18.5 mm up from the 40 mm module's bottom edge, so 10.5-21.5 mm down from
# the top. The board keeps the datasheet's ideal 8 x 15 mm clear around it: 1.5 mm past the
# module edge and 2 mm above and below.
ANTENNA_CUTOUT = (0.0, 10.5, 6.5, 21.5)          # Figure 4, module frame: x0, y0, x1, y1
_a, _b = from_module(-1.5, 8.5), from_module(6.5, 23.5)
ANTENNA_KEEPOUT = (min(_a[0], _b[0]), min(_a[1], _b[1]), max(_a[0], _b[0]), max(_a[1], _b[1]))
PLACEMENT = {
    "J1": (*from_cm5(-0.5, -21.5), 0), "J2": (*from_cm5(33.5, -21.5), 0),
    **{f"H{i + 1}": (x, y, 0) for i, (x, y) in enumerate(CM5_HOLES)},
    # top edge: USB-C and its ESD; 5 V bulk capacitors below the module, by the 5 V pins
    "J3": (24.0, USB_C_EDGE, 180), "U1": (33.5, 4.0, 0),
    "C1": (40.0, 51.6, 0), "C2": (43.6, 51.6, 0), "C3": (46.6, 51.6, 0),
    # right edge: USB-A host port and its switch; LEDs, power button, boot jumpers, fan
    "J4": (77.0, 30.0, 90), "U3": (71.0, 26.5, 90), "U2": (68.0, 16.5, 0), "C4": (64.5, 14.0, 90), "C5": (64.5, 19.0, 90),
    "C6": (68.0, 36.5, 0),
    "R4": (65.0, 43.5, 0), "D1": (68.6, 43.5, 180), "R5": (65.0, 45.5, 0), "D2": (68.6, 45.5, 180),
    "SW1": (84.0, 42.5, 90), "J9": (64.6, 5.0, 0), "J8": (76.0, 5.0, 0),
    # right edge, lower: microSD and its supply switch
    "J6": (82.0, 62.0, 90), "U6": (72.0, 56.0, 0), "R3": (72.0, 52.6, 0), "C8": (72.0, 59.4, 0),
    # bottom left: the MagJack by the Ethernet pins, its ESD, centre-tap capacitor, LED resistors
    "J5": (10.75, 60.0, 270), "U4": (23.0, 55.4, 0), "U5": (23.0, 62.4, 0), "C7": (29.0, 53.0, 90),
    "R1": (25.5, 59.0, 0), "R2": (25.5, 61.0, 0),
    # bottom edge: the 40-pin header; coin cell under the module, on the bottom side
    "J7": (24.5, 76.5, 90), "BT1": (34.0, 30.0, 0),
}
_unplaced = sorted({p.ref for p in PARTS} - set(PLACEMENT))
assert not _unplaced, f"parts without a board position: {_unplaced}"
for _p in PARTS:
    _p.pcb = PLACEMENT[_p.ref]
    if _p.ref == "BT1":
        _p.side = "B"

# The Ethernet pairs are routed first, in this order, before the autorouter, so the pairs stay
# short and side by side; left to choose its own order, the autorouter boxes one of them in.
# Pairs C and D leave the connector's outer row and run straight out on the top layer; pairs A
# and B leave the inner row, under the module, and cross beneath the connector. Outer first.
# Both rows wrap round the connector's left end towards the jack, so each row goes nearest the
# end first: connector pin order.
_ETH = [("3", "9"), ("5", "10"), ("9", "8"), ("11", "7"), ("4", "3"), ("6", "6"), ("10", "2"), ("12", "1")]
# Each Ethernet line passes through its ESD part as TI lays it out: in on the pad facing the
# connector, across to the pad opposite, out towards the jack.
_FLOW = {"9": ("U5", "7", "4"), "10": ("U5", "6", "5"), "8": ("U5", "9", "2"), "7": ("U5", "10", "1"),
         "3": ("U4", "7", "4"), "6": ("U4", "6", "5"), "2": ("U4", "9", "2"), "1": ("U4", "10", "1")}
PRIORITY = [r for cm5, jack in _ETH for esd, inner, outer in [_FLOW[jack]]
            for r in ((("J1", cm5), (esd, inner)), ((esd, inner), (esd, outer)), ((esd, outer), ("J5", jack)))]
# The USB host pair passes through its ESD part (in on one pad, out on the other of the same
# line), nearer the connector's right end first.
# The ESD part's VBUS pin (5) sits between the two port-side lines and must cross D- to reach the
# port's VBUS (pin 1), and no via may sit in its pad: so it leaves first, before those two lines box
# it in, and changes layer clear of the pad (the 2026-10-20 rebuilds left it open twice).
PRIORITY += [(("J2", "36"), ("U3", "3")), (("J2", "34"), ("U3", "1")),   # USBH_DM / USBH_DP (CM5 pins 136, 134)
             (("U3", "5"), ("J4", "1")),
             (("U3", "4"), ("J4", "2")), (("U3", "6"), ("J4", "3"))]
# Three microSD lines run first, shortest first, so they nest inside one another on the top layer:
# DAT1, DAT0 and CLK leave the connector's outer row in the order they reach the socket. CMD (from
# the inner row), DAT3 and DAT2 must cross them; the autorouter, which plans crossings for the
# whole board at once, takes those. Routed one by one, the crossing lines box each other in.
SD_BUS = [(("J1", "67"), ("J6", "8")), (("J1", "63"), ("J6", "7")), (("J1", "57"), ("J6", "5"))]
PRIORITY += SD_BUS
# GPIO2 (SDA, CM5 pin 58) to the header next: it sits between GPIO3 and a ground pad, and left to the
# autorouter its way out of the connector can be closed by the lines that cross just above the pad
# row. GPIO3 stays with the autorouter: laid one after the other by the maze, either line boxes the
# other in at the pad row.
PRIORITY += [(("J1", "58"), ("J7", "3"))]
TEXTS = [
    {"text": "EoS CM5 Base  rev A", "x": 45.0, "y": 66.0, "size": 1.2, "bold": True},
    {"text": "EoS CM5 Base  rev A", "x": 62.0, "y": 60.0, "size": 1.0, "layer": "B_SilkS", "bold": True, "mirror": True},
    {"text": "(c) 2026 Kartikeydheer Srivastava", "x": 62.0, "y": 62.0, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    {"text": "All rights reserved", "x": 62.0, "y": 63.4, "size": 0.8, "layer": "B_SilkS", "mirror": True},
]

BOARD = Board(
    name="eos-cm5-base",
    title="EoS CM5 Base",
    revision="A",
    date="2026-10-11",
    company=OWNER,
    licence=LICENCE,
    contact=CONTACT,
    licence_terms=LICENCE_TERMS,
    credits=["CM5 connector and mounting-hole positions and the CM5 pinout: Raspberry Pi CM5 datasheet "
             "and CM5 IO Board design files (facts only)"],
    width=W,
    height=H,
    corner_radius=3.0,
    # 0.45 mm vias (0.2 mm drill), the size Raspberry Pi's CM5 IO Board uses around this connector:
    # a 0.6 mm via cannot sit between lines 0.5 mm apart, as at the ESD parts' ground pins.
    rules={"via": 0.45, "drill": 0.2, "min_via": 0.45, "min_drill": 0.2},
    thickness=1.6,
    layers=4,
    planes=[("GND", "In1.Cu"), ("+5V", "In2.Cu")],
    local_footprints=["EoS_Connectors"],
    copper_keepouts=[ANTENNA_KEEPOUT],
    priority_routes=PRIORITY,
    # The ESD part's ground pin (2) sits between its two module-side lines, and no via may sit in a pad:
    # its plane via goes in first (the 2026-10-20 rebuild left it a pour island with no via).
    fanout_first=["U3"],
    escape_footprints=["J1", "J2"],
    # Under the module there is room to wrap round the connector ends on the top layer, where
    # vias at the inner row's 0.4 mm pitch would block one another: make the router prefer it.
    maze_via_cost_mm=8.0,
    parts=PARTS,
    power_nets={"GND": "power:GND", "+5V": "power:+5V", "+3V3": "power:+3V3"},
    flagged_nets=["GND", "+5V", "+3V3"],
    headings=[((40, 75), "CM5 connectors (pins 1-100, 101-200)"), ((150, 75), "USB-C: power in, USB 2.0 device"),
              ((270, 75), "USB-A host (USB 3.0 port 0's USB 2.0 pair)"), ((400, 75), "Gigabit Ethernet"),
              ((500, 75), "microSD (CM5 Lite)"), ((400, 235), "40-pin GPIO header"),
              ((500, 230), "Fan, RTC battery, power button, boot jumpers"), ((280, 280), "LEDs"),
              ((40, 345), "CM5 mounting holes"), ((35, 300), "Power nets")],
    power_block=(40.64, 315.0),
    notes=[((150, 385), "EoS CM5 Base, rev A. Designed by Kartikeydheer Srivastava.\n"
                       "Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved; see LICENSE.txt.\n"
                       "Pin nets per the CM5 datasheet (table 4); choices the datasheet leaves open follow Raspberry Pi's CM5IO.\n"
                       "No HDMI, PCIe, USB 3.0 SuperSpeed or MIPI: they need impedance-controlled, length-matched pairs.")],
    netclasses={"Power": {"track": 0.5, "clearance": 0.15}, "USB": {"track": 0.2, "clearance": 0.15},
                "Ethernet": {"track": 0.2, "clearance": 0.15}},
    net_to_class={"+5V": "Power", "USBH_VBUS": "Power", "USB_P": "USB", "USB_N": "USB", "USBH_DP": "USB", "USBH_DM": "USB",
                  **{f"ETH_{p}_{s}": "Ethernet" for p in "ABCD" for s in "PN"}},
)
