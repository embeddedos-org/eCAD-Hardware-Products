"""EoS Learn RP2350: a four-layer RP2350A teaching board, designed by Kartikeydheer Srivastava.

Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved: this design file is not under
the repository's MIT licence; see boards/eos/eos-learn-rp2350/LICENSE.txt.

The circuit follows Raspberry Pi's "Hardware design with RP2350" guide and the RP2350
datasheet, values and parts included: the core regulator's 3.3 uH polarity-marked inductor
and 4.7 uF capacitors with a 33 ohm / 4.7 uF filter on VREG_AVDD, 27 ohm series resistors on
USB, the ABM8-272-T3 crystal with 15 pF load capacitors and a 1 kohm series resistor, a 1 kohm
BOOTSEL resistor on QSPI_SS, and 100 nF on every supply pin (USB_OTP_VDD and QSPI_IOVDD
share one, as the guide does). The board, its layout and its pinout are ours.

Power comes from USB-C (5.1 kohm CC pull-downs make it a 5 V sink), through a 500 mA
polyfuse and a Schottky diode (so 5 V fed into the header cannot reach the USB host), to an
AP7361C 3.3 V regulator, which is stable with the board's ceramic capacitors. A Qwiic connector on I2C0 (GPIO4/5) and a Raspberry
Pi Debug Probe SWD connector make it a classroom board; every GPIO is on the two 2.54 mm
headers, with ground pins spread along both.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..design import NC, Board, Part, USB_C_EDGE
from .owner import CONTACT, LICENCE, LICENCE_TERMS, OWNER

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"


def res(ref, value, a, b, sch, mpn=None, dnp=False):
    return Part(ref, "Device:R_Small", value, R0402, sch, {"1": a, "2": b},
                fields={"Description": f"Resistor {value} 1% 0402", **({"MPN": mpn} if mpn else {})}, dnp=dnp)


def cap(ref, value, a, b, sch, fp=C0402, desc=None):
    return Part(ref, "Device:C_Small", value, fp, sch, {"1": a, "2": b},
                fields={"Description": desc or f"Capacitor {value} X7R/X5R {'0805' if fp == C0805 else '0402'}"})


GPIO = {f"GPIO{i}": f"GPIO{i}" for i in range(26)}
GPIO.update({f"GPIO{i}/ADC{i - 26}": f"GPIO{i}_ADC{i - 26}" for i in range(26, 30)})

# Header pinouts: the chip's left side (GPIO0-11) faces J2 on the left edge and its right side
# (GPIO19-29) faces J3 on the right edge, in the same top-to-bottom order; GPIO12-15 and
# GPIO16-18 leave the bottom edge for the lower ends of J2 and J3. No two traces need to cross.
J2_PINS = ["+3V3", "GPIO0", "GPIO1", "GND", "GPIO2", "GPIO3", "GPIO4", "GPIO5", "GND", "GPIO6",
           "GPIO7", "GPIO8", "GPIO9", "GND", "GPIO10", "GPIO11", "GPIO12", "GPIO13", "GPIO14", "GPIO15"]
J3_PINS = ["+5V", "GND", "GPIO29_ADC3", "GPIO28_ADC2", "GPIO27_ADC1", "GPIO26_ADC0", "GND", "GPIO25", "GPIO24", "GPIO23",
           "GPIO22", "GPIO21", "GPIO20", "GPIO19", "GPIO18", "GPIO17", "GPIO16", "GND", "RUN", "+3V3"]

W, H = 52.6, 51.6
MCU = (26.3, 30.3)

PARTS = [
    # ---- USB-C power and data input -------------------------------------------------
    Part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
         (50, 110), {"VBUS": "VBUS", "GND": "GND", "CC1": "CC1", "CC2": "CC2", "D+": "USB_D+", "D-": "USB_D-",
                     "SBU1": NC, "SBU2": NC, "SHIELD": "GND"}, fields={"Manufacturer": "Korean Hroparts", "MPN": "TYPE-C-31-M-12",
                                       "Description": "USB-C 2.0 receptacle, 16 pins, mid-mount"}),
    res("R1", "5.1k", "CC1", "GND", (90, 95)),
    res("R2", "5.1k", "CC2", "GND", (105, 95)),
    Part("U2", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", (140, 110),
         {"I/O1": "USB_D+", "I/O2": "USB_D-", "GND": "GND", "VBUS": "VBUS"},
         fields={"Manufacturer": "STMicroelectronics", "MPN": "USBLC6-2SC6", "Description": "USB ESD protection"}),
    Part("F1", "Device:Polyfuse_Small", "500mA", "Fuse:Fuse_1206_3216Metric", (175, 95), {"1": "VBUS", "2": "VBUS_F"}, fields={"Manufacturer": "Littelfuse", "MPN": "1206L050YR",
                                     "Description": "PTC resettable fuse 500 mA hold, 1206"}),
    Part("D1", "Device:D_Schottky", "MBR120VLSFT1G", "Diode_SMD:D_SOD-123F", (190, 125), {"A": "VBUS_F", "K": "+5V"},
         fields={"Manufacturer": "onsemi", "MPN": "MBR120VLSFT1G",
                 "Description": "Schottky 20 V 1 A, SOD-123FL: 5 V fed into the header cannot reach the USB host"}),
    Part("U3", "Regulator_Linear:AP7361C-33E", "AP7361C-33", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", (205, 110),
         {"VI": "+5V", "VO": "+3V3", "GND": "GND"},
         fields={"Manufacturer": "Diodes Incorporated", "MPN": "AP7361C-33E-13",
                 "Description": "LDO 3.3 V 1 A, SOT-223, stable with ceramic capacitors of 2.2 uF or more"}),
    cap("C1", "10u", "+5V", "GND", (230, 105), C0805, "Capacitor 10 uF 10 V X5R 0805 (LDO input)"),
    cap("C2", "10u", "+3V3", "GND", (245, 105), C0805, "Capacitor 10 uF 10 V X5R 0805 (LDO output)"),
    res("R5", "1k", "+3V3", "LED_PWR_A", (265, 105)),
    Part("D2", "Device:LED_Small", "PWR", "LED_SMD:LED_0603_1608Metric", (280, 105), {"A": "LED_PWR_A", "K": "GND"}, fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LSURCK", "Description": "LED red 0603"}),

    # ---- RP2350A and its core regulator ------------------------------------------------
    Part("U1", "MCU_RaspberryPi:RP2350A", "RP2350A", "Package_DFN_QFN:QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm", (140, 240),
         {"IOVDD": "+3V3", "DVDD": "+1V1", "VREG_VIN": "+3V3", "VREG_LX": "VREG_LX", "VREG_PGND": "GND",
          "VREG_AVDD": "VREG_AVDD", "VREG_FB": "+1V1", "USB_OTP_VDD": "+3V3", "ADC_AVDD": "+3V3",
          "QSPI_IOVDD": "+3V3", "GND": "GND", "XIN": "XIN", "XOUT": "XOUT", "SWCLK": "SWCLK", "SWDIO": "SWDIO",
          "RUN": "RUN", "USB_DM": "RP_USB_DM", "USB_DP": "RP_USB_DP", "QSPI_SD0": "QSPI_SD0",
          "QSPI_SD1": "QSPI_SD1", "QSPI_SD2": "QSPI_SD2", "QSPI_SD3": "QSPI_SD3", "QSPI_SCLK": "QSPI_SCLK",
          "~{QSPI_SS}": "QSPI_SS", **GPIO}, fields={"Manufacturer": "Raspberry Pi", "MPN": "RP2350A0A2",
                                         "Description": "Dual Cortex-M33 / Hazard3 microcontroller, QFN-60"}),
    Part("L1", "Device:L_Small", "3.3u", "EoS_RPi_Reference:abracon_aota-b201610s3r3-101-t", (225, 210), {"1": "+1V1", "2": "VREG_LX"}, fields={"Manufacturer": "Abracon", "MPN": "AOTA-B201610S3R3-101-T",
                                     "Description": "Inductor 3.3 uH 2016, polarity-marked; fitted as Raspberry Pi's reference footprint orients it"}),
    cap("C6", "4.7u", "+3V3", "GND", (240, 210), desc="Capacitor 4.7 uF X5R 0402 (VREG_VIN)"),
    cap("C7", "4.7u", "+1V1", "GND", (255, 210), desc="Capacitor 4.7 uF X5R 0402 (VREG output)"),
    res("R6", "33", "+3V3", "VREG_AVDD", (270, 210)),
    cap("C9", "4.7u", "VREG_AVDD", "GND", (285, 210), desc="Capacitor 4.7 uF X5R 0402 (VREG_AVDD filter)"),
]

# 100 nF on each supply pin, placed at the pin it serves.
DECOUPLING = [
    ("C10", "+3V3"), ("C11", "+3V3"),   # IOVDD 1, 11
    ("C12", "+3V3"), ("C13", "+3V3"),     # IOVDD 20, 30
    ("C14", "+3V3"), ("C15", "+3V3"),   # IOVDD 38, 45
    ("C16", "+3V3"),                                       # USB_OTP_VDD + QSPI_IOVDD
    ("C17", "+3V3"),                                      # ADC_AVDD
    ("C18", "+1V1"), ("C19", "+1V1"),    # DVDD 6, 23
    ("C20", "+1V1"),                                      # DVDD 39
]
for i, (ref, net) in enumerate(DECOUPLING):
    PARTS.append(cap(ref, "100n", net, "GND", (210 + 13 * i, 285), desc="Capacitor 100 nF X7R 0402 (decoupling)"))

PARTS += [
    # ---- QSPI flash and BOOTSEL -----------------------------------------------------------
    Part("U4", "Memory_Flash:W25Q128JVS", "W25Q128JVS", "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm", (360, 110),
         {"~{CS}": "QSPI_SS", "DO/IO_{1}": "QSPI_SD1", "~{WP}/IO_{2}": "QSPI_SD2", "GND": "GND",
          "DI/IO_{0}": "QSPI_SD0", "CLK": "QSPI_SCLK", "~{HOLD}/~{RESET}/IO_{3}": "QSPI_SD3", "VCC": "+3V3"}, fields={"Manufacturer": "Winbond", "MPN": "W25Q128JVSIQ",
                                     "Description": "128 Mbit QSPI NOR flash, SOIC-8 208 mil"}),
    cap("C21", "100n", "+3V3", "GND", (385, 105), desc="Capacitor 100 nF X7R 0402 (flash)"),
    res("R7", "10k", "QSPI_SS", "+3V3", (400, 95), dnp=True),
    res("R8", "1k", "QSPI_SS", "BOOTSEL", (415, 95)),
    Part("SW1", "Switch:SW_Push", "BOOTSEL", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", (440, 110),
         {"1": "BOOTSEL", "2": "GND"},
         fields={"Manufacturer": "C&K", "MPN": "KMR221G LFS", "Description": "Tactile switch, BOOTSEL"}),

    # ---- Crystal and reset -----------------------------------------------------------------
    Part("Y1", "Device:Crystal_GND24_Small", "12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", (360, 210),
         {"1": "XIN", "3": "XTAL_OUT", "G": "GND"},
         fields={"Manufacturer": "Abracon", "MPN": "ABM8-272-T3", "Description": "Crystal 12 MHz 10 pF 30 ppm, 3225"}),
    cap("C3", "15p", "XIN", "GND", (380, 205), desc="Capacitor 15 pF C0G 0402 (crystal load)"),
    cap("C4", "15p", "XTAL_OUT", "GND", (395, 205), desc="Capacitor 15 pF C0G 0402 (crystal load)"),
    res("R10", "1k", "XOUT", "XTAL_OUT", (335, 205)),
    Part("SW2", "Switch:SW_Push", "RUN", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", (440, 210),
         {"1": "RUN", "2": "GND"},
         fields={"Manufacturer": "C&K", "MPN": "KMR221G LFS", "Description": "Tactile switch, RUN (reset)"}),
    res("R9", "10k", "RUN", "+3V3", (460, 205)),

    # ---- USB series termination, at the chip ------------------------------------------------
    res("R3", "27", "USB_D+", "RP_USB_DP", (300, 160)),
    res("R4", "27", "USB_D-", "RP_USB_DM", (315, 160)),

    # ---- User LED, Qwiic, SWD ------------------------------------------------------------------
    res("R11", "470", "GPIO25", "LED_USR_A", (360, 270)),
    Part("D3", "Device:LED_Small", "GP25", "LED_SMD:LED_0603_1608Metric", (375, 270), {"A": "LED_USR_A", "K": "GND"}, fields={"Manufacturer": "Kingbright", "MPN": "APTD1608LCGCK", "Description": "LED green 570 nm 0603, about 1.9 V at 2 mA"}),
    Part("J4", "Connector:Conn_01x03_Pin", "SWD", "Connector_JST:JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal",
         (480, 320), {"1": "SWCLK", "2": "GND", "3": "SWDIO"},
         fields={"Manufacturer": "JST", "MPN": "SM03B-SRSS-TB", "Description": "SWD: Raspberry Pi Debug Probe pinout"}),
    Part("J5", "Connector:Conn_01x04_Pin", "Qwiic", "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal",
         (520, 320), {"1": "GND", "2": "+3V3", "3": "GPIO4", "4": "GPIO5"},
         fields={"Manufacturer": "JST", "MPN": "SM04B-SRSS-TB", "Description": "Qwiic / STEMMA QT I2C0: SDA GPIO4, SCL GPIO5"}),
    res("R12", "4.7k", "GPIO4", "+3V3", (545, 310)),
    res("R13", "4.7k", "GPIO5", "+3V3", (560, 310)),

    # ---- Headers ----------------------------------------------------------------------------------
    Part("J2", "Connector:Conn_01x20_Pin", "GPIO 0-15", "Connector_PinHeader_2.54mm:PinHeader_1x20_P2.54mm_Vertical",
         (480, 150), {str(i + 1): n for i, n in enumerate(J2_PINS)},
         fields={"Description": "Pin header 1x20 2.54 mm"}),
    Part("J3", "Connector:Conn_01x20_Pin", "Power, GPIO 16-29", "Connector_PinHeader_2.54mm:PinHeader_1x20_P2.54mm_Vertical",
         (530, 150), {str(i + 1): n for i, n in enumerate(J3_PINS)},
         fields={"Description": "Pin header 1x20 2.54 mm"}),
]

for i in range(4):
    PARTS.append(Part(f"H{i + 1}", "Mechanical:MountingHole_Pad", "M2", "MountingHole:MountingHole_2.2mm_M2_Pad_Via",
                      (60 + 20 * i, 360), {"1": "GND"}, fields={"Description": "Mounting hole M2, grounded"}))

# Board placement: (x, y, rotation) in mm, origin top-left, all parts on the top side.
# The floorplan follows Raspberry Pi's RP2350A Minimal Design (R4, MIT licence, (c) 2026
# Raspberry Pi Ltd), which the RP2350 hardware guide recommends for the core regulator: the
# chip in the middle of a square board with its regulator, USB and QSPI pins facing the USB
# connector at the top, the regulator parts (L1, C6, C7, C9, R6), the USB resistors and the
# decoupling ring at the positions that design gives them relative to the chip, and the
# headers down the left and right edges. Routing, the USB-C power path, ESD protection,
# Qwiic, LEDs, mounting holes and the pinout are this board's own.
PLACEMENT = {
    "J2": (3.44, 1.7, 0), "J3": (W - 3.44, 1.7, 0),
    "H1": (12.33, 4.3, 0), "H2": (W - 12.33, 4.3, 0), "H3": (12.33, H - 4.12, 0), "H4": (W - 12.33, H - 4.12, 0),
    # USB-C at the top edge, protection and CC pull-downs below it, fuse and LDO to the right
    "J1": (MCU[0], USB_C_EDGE, 180), "U2": (MCU[0], 11.0, 0), "R1": (21.4, 10.6, 90), "R2": (31.2, 10.6, 90),
    "F1": (34.0, 7.8, 0), "D1": (31.6, 14.2, 90), "C1": (39.0, 9.6, 0), "U3": (37.6, 14.8, 180), "C2": (37.6, 19.9, 0),
    # RP2350A, its regulator, decoupling, crystal and USB resistors: see REFERENCE below
    "C17": (32.78, 26.3, 0),                                                              # ADC_AVDD (pin 44)
    # flash and BOOTSEL, upper left
    "U4": (19.35, 17.58, 0), "C21": (22.49, 13.13, 180), "R7": (19.3, 12.5, 270), "R8": (15.2, 11.6, 0),
    "SW1": (18.0, 7.6, 0),
    # reset and SWD, lower right
    "SW2": (38.1, 37.8, 180), "R9": (41.7, 39.4, 270), "J4": (33.9, 45.7, 0),
    # Qwiic (I2C0) lower left, LEDs upper right
    "J5": (13.0, 40.6, 0), "R12": (18.0, 39.0, 90), "R13": (19.2, 39.0, 90),
    "R5": (42.6, 22.0, 0), "D2": (45.2, 22.0, 180), "R11": (42.6, 24.6, 0), "D3": (45.2, 24.6, 180),
}
# The chip, its regulator, decoupling, crystal and USB resistors take Raspberry Pi's footprints
# and positions, so Raspberry Pi's copper lands on pads of exactly the shape it was drawn for.
REFERENCE = "reference/rp2350a_minimal_r4_core.json"
_core = json.loads((Path(__file__).resolve().parents[1] / REFERENCE).read_text())["footprints"]
for _p in PARTS:
    if _p.ref in _core:
        _f = _core[_p.ref]
        _p.footprint = _f["footprint"]
        PLACEMENT[_p.ref] = (round(MCU[0] + _f["x"], 6), round(MCU[1] + _f["y"], 6), _f["rot"])
_unplaced = sorted({p.ref for p in PARTS} - set(PLACEMENT))
assert not _unplaced, f"parts without a board position: {_unplaced}"
for _p in PARTS:
    _p.pcb = PLACEMENT[_p.ref]

# GPIO routing order. Each line leaves the chip along Raspberry Pi's own escape through the
# decoupling ring and then runs to its header pin. The lines on each side are routed so that each
# one nests outside the one before. Lines turning up go top row first and lines turning down go
# bottom row first, then the lines off the bottom edge, innermost first. A net with two ends
# besides the chip (GPIO25 to J3 and its LED) is routed in full, so the autorouter never gets half
# a net.
_U1_PIN = {f"GPIO{i}": p for i, p in enumerate([2, 3, 4, 5, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19,
                                                  27, 28, 29, 31, 32, 33, 34, 35, 36, 37, 40, 41, 42, 43])}
_J2_PIN = {n: str(i + 1) for i, n in enumerate(J2_PINS)}
_J3_PIN = {n: str(i + 1) for i, n in enumerate(J3_PINS)}


def _to_header(gpio):
    net = gpio if gpio in _J2_PIN or gpio in _J3_PIN else next(n for n in J3_PINS if n.startswith(gpio + "_"))
    head = ("J2", _J2_PIN[net]) if net in _J2_PIN else ("J3", _J3_PIN[net])
    return ("U1", str(_U1_PIN[gpio])), head


GPIO_ROUTES = [_to_header(f"GPIO{i}") for i in (
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9,       # left side, turning up: top row first
    11, 10,                             # left side, turning down: bottom row first
    12, 13, 14, 15,                     # bottom edge, to the foot of J2
    29, 28, 27, 26, 25, 24, 23, 22, 21, 20,   # right side, turning up: top row first
    19,                                 # right side, turning down
    18, 17, 16)]                        # bottom edge, to the foot of J3
GPIO_ROUTES.append((("R11", "1"), ("J3", _J3_PIN["GPIO25"])))   # GPIO25's LED

# Back silkscreen: name, revision, copyright, and the notice Raspberry Pi's MIT licence requires.
TEXTS = [
    {"text": "EoS Learn RP2350  rev A", "x": MCU[0], "y": 13.6, "size": 1.0, "layer": "B_SilkS", "bold": True, "mirror": True},
    {"text": "(c) 2026 Kartikeydheer Srivastava", "x": MCU[0], "y": 15.4, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    {"text": "All rights reserved", "x": MCU[0], "y": 16.8, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    {"text": "Core layout (c) 2026 Raspberry Pi Ltd  MIT", "x": MCU[0], "y": 44.4, "size": 0.8, "layer": "B_SilkS", "mirror": True},
]

BOARD = Board(
    name="eos-learn-rp2350",
    title="EoS Learn RP2350",
    revision="A",
    date="2026-10-11",
    company=OWNER,
    licence=LICENCE,
    contact=CONTACT,
    licence_terms=LICENCE_TERMS,
    credits=["RP2350A core layout (regulator, decoupling, crystal, USB, QSPI): Raspberry Pi RP2350A Minimal "
             "Design R4, Copyright (c) 2026 Raspberry Pi Ltd, MIT licence"],
    width=W,
    height=H,
    thickness=1.6,
    layers=4,
    planes=[("GND", "In1.Cu"), ("+3V3", "In2.Cu")],
    fanout_avoid=[MCU],
    # The chip's surroundings are Raspberry Pi's own copper (MIT): its exposed-pad vias, the
    # 1.1 V and 3.3 V rings under the chip, the regulator corner, the decoupling, the crystal,
    # the USB termination and the QSPI lines. The regulator corner is joined by that copper
    # alone; the decoupling capacitors also get a via each into the planes.
    no_fanout=["U1", "L1", "C6", "C7", "C9", "R6", "R3", "R4"],
    # Two of Raspberry Pi's ground vias beside the regulator capacitors come 0.05 mm from C6.2 and
    # C7.2, and solder wicks down an open barrel that close. Each moves to the nearest spot clear of
    # both pads by VIA_PAD_GAP, inside Raspberry Pi's ground pour and 0.15 mm off the VREG_AVDD track.
    reference_copper={"file": REFERENCE, "origin": MCU,
                      "moved_vias": [((3.1, -5.5), (3.16, -5.59)), ((3.1, -4.9), (3.11, -5.08))]},
    # Inside the pin ring belongs to that copper: the autorouter may not escape signals inward.
    router_keepouts=[(MCU[0] - 3.0, MCU[1] - 3.0, MCU[0] + 3.0, MCU[1] + 3.0)],
    # Every GPIO line is routed before the autorouter, which, left to pick its own order, boxes
    # one or two of them in at the decoupling ring. See GPIO_ROUTES.
    priority_routes=GPIO_ROUTES,
    local_footprints=["EoS_RPi_Reference"],
    parts=PARTS,
    power_nets={"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V", "VBUS": "power:VBUS", "+1V1": "power:+1V1"},
    flagged_nets=["GND", "VBUS", "+5V", "+1V1", "VREG_AVDD"],
    headings=[((35, 75), "USB-C input and ESD protection"), ((160, 75), "Fuse and 3.3 V regulator"),
              ((250, 75), "Power LED"), ((285, 140), "USB series termination (at the chip)"),
              ((95, 175), "RP2350A"), ((215, 180), "Core regulator: place exactly as the datasheet shows"),
              ((205, 260), "100 nF decoupling, one per supply pin"), ((330, 75), "QSPI flash and BOOTSEL"),
              ((320, 180), "12 MHz crystal (ABM8-272-T3)"), ((425, 180), "Reset"), ((335, 250), "User LED (GPIO25)"),
              ((465, 75), "2.54 mm headers"), ((465, 290), "SWD and Qwiic (I2C0)"), ((40, 345), "Mounting holes"),
              ((35, 300), "Power nets")],
    power_block=(40.64, 315.0),
    notes=[((280, 345), "EoS Learn RP2350, rev A. Designed by Kartikeydheer Srivastava.\n"
                      "Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved; see LICENSE.txt.\n"
                      "Circuit values follow Raspberry Pi's 'Hardware design with RP2350' and the RP2350 datasheet.\n"
                      "Core regulator: L1 3.3 uH polarity-marked, C6/C7/C9 4.7 uF, R6 33 ohm, footprints, positions and\n"
                      "copper exactly as Raspberry Pi's RP2350A Minimal Design R4 (MIT), as datasheet Figure 26 requires.\n"
                      "Crystal: ABM8-272-T3 with C3/C4 15 pF and R10 1 kohm, tuned for IOVDD = 3.3 V.\n"
                      "R7 (QSPI_SS pull-up) is not fitted, as the guide recommends for the W25Q128JV.")],
    netclasses={
        "Power": {"track": 0.5, "clearance": 0.15},      # VBUS and +5V, away from fine-pitch pads
        "PowerFine": {"track": 0.2, "clearance": 0.15},  # supplies that reach the 0.4 mm-pitch QFN
        "USB": {"track": 0.2, "clearance": 0.15},      # over the In1 ground plane
    },
    net_to_class={"VBUS": "Power", "VBUS_F": "Power", "+5V": "Power", "+3V3": "PowerFine", "+1V1": "PowerFine", "VREG_LX": "PowerFine",
                  "USB_D+": "USB", "USB_D-": "USB", "RP_USB_DP": "USB", "RP_USB_DM": "USB"},
)
