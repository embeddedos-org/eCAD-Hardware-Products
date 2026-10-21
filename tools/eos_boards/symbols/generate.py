"""Write the symbols KiCad's own libraries do not have.

EoS_Connectors.kicad_sym: KiCad's generic double-row connectors stop at 2x40, and the Raspberry Pi
Compute Module 5 needs two 100-pin (2x50) connectors, and a 98-hole (2x49) breakout row needs a
2x49. The symbols follow KiCad's Conn_02xNN_Odd_Even layout exactly: odd pins on the left, even
pins on the right, 2.54 mm apart, passive.

EoS_Parts.kicad_sym: a flow-through TPD4EUSB30 (see its docstring).

EoS_Sensors.kicad_sym: the Analog Devices ADT7410 temperature sensor (SOIC-8), which KiCad doesn't ship.

EoS_MCU.kicad_sym: the TI TM4C123GH6PM (LQFP-64). KiCad ships only the TM4C1230/1231, which lack USB;
the pins follow TI SPMS376E Table 23-2 and agree pin for pin with KiCad's TM4C1231H6PM.
It also holds the NXP LPC55S69JBD100 (HLQFP-100, exposed pad as pin 101), pins from the LPC55S6x data
sheet Rev. 2.5, Table 3, which KiCad doesn't ship.
And the Renesas R7FA2E1A92DFM (RA2E1, LQFP-64), pins from the RA2E1 data sheet R01DS0386EJ0170
Rev. 1.70, Table 1.15; KiCad has no RA-family symbol.

The Renesas R7FA4M2AD3CFP (RA4M2, LQFP-100) follows R01DS0367EJ0150 Table 1.17;
R5F100LEAFB (RL78/G13, LFQFP-64) follows R01DS0131EJ0380 section 1.3.11;
TI TMS320F280049CPZ (C2000, LQFP-100) follows SPRS945H Table 5-1 and Figure 5-1;
TI TM4C1294NCPDT (TQFP-128) follows SPMS433B Table 26-5 (the 90 GPIO pins), Table 26-3 (the fixed
supply, oscillator, hibernation and Ethernet pins) and Figure 25-1. KiCad 10 has no TM4C129x symbol.

usage: python3 tools/eos_boards/symbols/generate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from eos_boards.sexpr import Sym, dumps  # noqa: E402


def _font():
    return [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]]]


def _prop(key, value, x, y, hide=False):
    node = [Sym("property"), key, value, [Sym("at"), x, y, 0]]
    eff = _font()
    if hide:
        eff.append([Sym("hide"), Sym("yes")])
    node.append(eff)
    return node


def double_row(rows: int) -> list:
    name = f"Conn_02x{rows:02d}_Odd_Even"
    top = round(2.54 * (rows // 2 - 1), 2)
    bottom = round(top - 2.54 * (rows - 1), 2)
    body = [Sym("symbol"), f"{name}_1_1",
            [Sym("rectangle"), [Sym("start"), -1.27, round(top + 1.27, 2)], [Sym("end"), 3.81, round(bottom - 1.27, 2)],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("background")]]]]
    for k in range(rows):
        y = round(top - 2.54 * k, 2)
        for number, x, angle in ((2 * k + 1, -5.08, 0), (2 * k + 2, 7.62, 180)):
            body.append([Sym("pin"), Sym("passive"), Sym("line"), [Sym("at"), x, y, angle], [Sym("length"), 3.81],
                         [Sym("name"), f"Pin_{number}", _font()], [Sym("number"), str(number), _font()]])
    return [Sym("symbol"), name, [Sym("pin_names"), [Sym("offset"), 1.016], [Sym("hide"), Sym("yes")]],
            [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            _prop("Reference", "J", 1.27, round(top + 2.54, 2)), _prop("Value", name, 1.27, round(bottom - 2.54, 2)),
            _prop("Footprint", "", 0, 0, True), _prop("Datasheet", "", 0, 0, True),
            _prop("Description", f"Generic connector, double row, 02x{rows:02d}, odd/even pin numbering "
                                 "(row 1 odd numbers, row 2 even numbers), laid out as KiCad's own", 0, 0, True),
            body]


def tpd4eusb30_flow_through() -> list:
    """TI TPD4EUSB30 drawn for flow-through routing, as TI lays it out: each line enters one side
    of the package and leaves from the pad opposite (1/10, 2/9, 4/7, 5/6). KiCad's own symbol
    marks the far-side pads no-connect, so a line could not pass through."""
    name = "TPD4EUSB30_FlowThrough"
    body = [Sym("symbol"), f"{name}_1_1",
            [Sym("rectangle"), [Sym("start"), -5.08, 7.62], [Sym("end"), 5.08, -7.62],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("background")]]]]
    rows = [("1", "D1+", "10"), ("2", "D1-", "9"), ("4", "D2+", "7"), ("5", "D2-", "6")]
    for k, (left, label, right) in enumerate(rows):
        y = round(5.08 - 2.54 * k - (2.54 if k >= 2 else 0), 2)
        body.append([Sym("pin"), Sym("passive"), Sym("line"), [Sym("at"), -7.62, y, 0], [Sym("length"), 2.54],
                     [Sym("name"), label, _font()], [Sym("number"), left, _font()]])
        body.append([Sym("pin"), Sym("passive"), Sym("line"), [Sym("at"), 7.62, y, 180], [Sym("length"), 2.54],
                     [Sym("name"), label, _font()], [Sym("number"), right, _font()]])
    for number, x in (("3", -1.27), ("8", 1.27)):
        body.append([Sym("pin"), Sym("power_in"), Sym("line"), [Sym("at"), x, -10.16, 90], [Sym("length"), 2.54],
                     [Sym("name"), "GND", _font()], [Sym("number"), number, _font()]])
    return [Sym("symbol"), name, [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            _prop("Reference", "U", 0, 8.89), _prop("Value", "TPD4EUSB30", 0, -12.7),
            _prop("Footprint", "Package_SON:USON-10_2.5x1.0mm_P0.5mm", 0, 0, True),
            _prop("Datasheet", "https://www.ti.com/lit/ds/symlink/tpd4eusb30.pdf", 0, 0, True),
            _prop("Description", "4-channel ESD protection, flow-through: each line enters one pad and leaves the pad "
                                 "opposite (1/10, 2/9, 4/7, 5/6)", 0, 0, True),
            body]


def adt7410() -> list:
    """Analog Devices ADT7410, SOIC-8: pins as its data sheet (Rev. C, Table 4): 1 SCL, 2 SDA,
    3 A0, 4 A1, 5 INT (open drain), 6 CT (open drain), 7 GND, 8 VDD."""
    name = "ADT7410"
    body = [Sym("symbol"), f"{name}_1_1",
            [Sym("rectangle"), [Sym("start"), -7.62, 5.08], [Sym("end"), 7.62, -7.62],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("background")]]]]
    left = [("1", "SCL", "input", 2.54), ("2", "SDA", "bidirectional", 0.0),
            ("3", "A0", "input", -2.54), ("4", "A1", "input", -5.08)]
    right = [("5", "INT", "open_collector", 2.54), ("6", "CT", "open_collector", 0.0)]
    for number, label, kind, y in left:
        body.append([Sym("pin"), Sym(kind), Sym("line"), [Sym("at"), -10.16, y, 0], [Sym("length"), 2.54],
                     [Sym("name"), label, _font()], [Sym("number"), number, _font()]])
    for number, label, kind, y in right:
        body.append([Sym("pin"), Sym(kind), Sym("line"), [Sym("at"), 10.16, y, 180], [Sym("length"), 2.54],
                     [Sym("name"), label, _font()], [Sym("number"), number, _font()]])
    body.append([Sym("pin"), Sym("power_in"), Sym("line"), [Sym("at"), 0, 7.62, 270], [Sym("length"), 2.54],
                 [Sym("name"), "VDD", _font()], [Sym("number"), "8", _font()]])
    body.append([Sym("pin"), Sym("power_in"), Sym("line"), [Sym("at"), 0, -10.16, 90], [Sym("length"), 2.54],
                 [Sym("name"), "GND", _font()], [Sym("number"), "7", _font()]])
    return [Sym("symbol"), name, [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            _prop("Reference", "U", 0, 10.16), _prop("Value", name, 0, -12.7),
            _prop("Footprint", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 0, 0, True),
            _prop("Datasheet", "https://www.analog.com/media/en/technical-documentation/data-sheets/ADT7410.pdf", 0, 0, True),
            _prop("Description", "16-bit digital I2C temperature sensor, +-0.5 C, SOIC-8", 0, 0, True),
            body]


def tm4c123gh6pm() -> list:
    """TI TM4C123GH6PM, 64-pin LQFP (PM). Pins as TI SPMS376E, Table 23-2 (Signals by Pin Number),
    names with each pin's fixed function from Table 10-2: GPIOs on the right by port (A to D) and
    on the left (E, F), with reset, both oscillators and the hibernation pins; supplies on top
    (VDD 11/26/42/54, VDDA 2, VDDC 25/56), grounds below (GND 12/27/39/55, GNDA 3, GNDX 35)."""
    name = "TM4C123GH6PM"
    body = [Sym("symbol"), f"{name}_1_1",
            [Sym("rectangle"), [Sym("start"), -17.78, 45.72], [Sym("end"), 17.78, -45.72],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("background")]]]]
    io = "bidirectional"
    # (number, name, type); None leaves a gap of one row
    left = [("38", "~{RST}", "input"), None,
            ("40", "OSC0", "passive"), ("41", "OSC1", "passive"), None,
            ("34", "XOSC0", "passive"), ("36", "XOSC1", "passive"), None,
            ("32", "~{WAKE}", "input"), ("33", "~{HIB}", "output"), ("37", "VBAT", "power_in"), None,
            ("9", "PE0/AIN3", io), ("8", "PE1/AIN2", io), ("7", "PE2/AIN1", io), ("6", "PE3/AIN0", io),
            ("59", "PE4/AIN9", io), ("60", "PE5/AIN8", io), None,
            ("28", "PF0/NMI", io), ("29", "PF1", io), ("30", "PF2", io), ("31", "PF3", io), ("5", "PF4", io)]
    right = [("17", "PA0/U0RX", io), ("18", "PA1/U0TX", io), ("19", "PA2", io), ("20", "PA3", io),
             ("21", "PA4", io), ("22", "PA5", io), ("23", "PA6", io), ("24", "PA7", io), None,
             ("45", "PB0/USB0ID", io), ("46", "PB1/USB0VBUS", io), ("47", "PB2", io), ("48", "PB3", io),
             ("58", "PB4/AIN10", io), ("57", "PB5/AIN11", io), ("1", "PB6", io), ("4", "PB7", io), None,
             ("52", "PC0/TCK/SWCLK", io), ("51", "PC1/TMS/SWDIO", io), ("50", "PC2/TDI", io),
             ("49", "PC3/TDO/SWO", io), ("16", "PC4", io), ("15", "PC5", io), ("14", "PC6", io), ("13", "PC7", io), None,
             ("61", "PD0/AIN7", io), ("62", "PD1/AIN6", io), ("63", "PD2/AIN5", io), ("64", "PD3/AIN4", io),
             ("43", "PD4/USB0DM", io), ("44", "PD5/USB0DP", io), ("53", "PD6", io), ("10", "PD7/NMI", io)]
    top = [("11", "VDD"), ("26", "VDD"), ("42", "VDD"), ("54", "VDD"), ("2", "VDDA"), ("25", "VDDC"), ("56", "VDDC")]
    bottom = [("12", "GND"), ("27", "GND"), ("39", "GND"), ("55", "GND"), ("3", "GNDA"), ("35", "GNDX")]

    def pin(number, label, kind, x, y, angle):
        return [Sym("pin"), Sym(kind), Sym("line"), [Sym("at"), x, y, angle], [Sym("length"), 2.54],
                [Sym("name"), label, _font()], [Sym("number"), number, _font()]]

    for column, x, angle in ((left, -20.32, 0), (right, 20.32, 180)):
        for row, entry in enumerate(column):
            if entry is not None:
                body.append(pin(*entry, x, round(43.18 - 2.54 * row, 2), angle))
    for k, (number, label) in enumerate(top):
        body.append(pin(number, label, "power_in", round(-7.62 + 2.54 * k, 2), 48.26, 270))
    for k, (number, label) in enumerate(bottom):
        body.append(pin(number, label, "power_in", round(-6.35 + 2.54 * k, 2), -48.26, 90))
    return [Sym("symbol"), name, [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            _prop("Reference", "U", 0, 50.8), _prop("Value", name, 0, -50.8),
            _prop("Footprint", "Package_QFP:LQFP-64_10x10mm_P0.5mm", 0, 0, True),
            _prop("Datasheet", "https://www.ti.com/lit/ds/symlink/tm4c123gh6pm.pdf", 0, 0, True),
            _prop("Description", "Tiva C Arm Cortex-M4F MCU, 80 MHz, 256 kB flash, 32 kB SRAM, 2 kB EEPROM, USB 2.0 "
                                 "full speed, hibernation module, LQFP-64 (TI SPMS376E)", 0, 0, True),
            body]


# --- pin table: (number, name, KiCad electrical type), NXP LPC55S6x data sheet Rev. 2.5 Table 3 ---
LPC55_PIO0 = {0: 54, 1: 7, 2: 81, 3: 83, 4: 86, 5: 88, 6: 89, 7: 6, 8: 26, 9: 55, 10: 21, 11: 13, 12: 12, 13: 71,
        14: 72, 15: 22, 16: 14, 17: 8, 18: 56, 19: 90, 20: 74, 21: 76, 22: 78, 23: 20, 24: 70, 25: 79, 26: 60,
        27: 27, 28: 66, 29: 92, 30: 94, 31: 23}
LPC55_PIO1 = {0: 11, 1: 59, 2: 61, 3: 62, 4: 1, 5: 31, 6: 5, 7: 9, 8: 24, 9: 10, 10: 40, 11: 93, 12: 67, 13: 2,
        14: 57, 15: 82, 16: 87, 17: 43, 18: 64, 19: 58, 20: 4, 21: 30, 22: 41, 23: 42, 24: 3, 25: 77, 26: 68,
        27: 85, 28: 73, 29: 80, 30: 65, 31: 91}
LPC55_TOP = [  # supplies, drawn along the top edge
    ("15", "VDD"), ("25", "VDD"), ("44", "VDD"), ("63", "VDD"), ("69", "VDD"), ("75", "VDD"), ("84", "VDD"),
    ("95", "VDD"), ("100", "VDD"), ("16", "VDDA"), ("17", "VREFP"), ("49", "VBAT_DCDC"), ("50", "VBAT_DCDC"),
    ("51", "VBAT_PMU"), ("96", "USB0_3V3"), ("38", "USB1_3V3"), ("39", "VDD_PMU"), ("45", "FB"),
]
LPC55_BOTTOM = [  # DC-DC switch node, reset, oscillators, USB, then every ground
    ("48", "LX"), ("32", "RESETN"), ("29", "XTAL32M_P"), ("28", "XTAL32M_N"), ("52", "XTAL32K_P"),
    ("53", "XTAL32K_N"), ("97", "USB0_DP"), ("98", "USB0_DM"), ("34", "USB1_DP"), ("35", "USB1_DM"),
    ("36", "USB1_VBUS"), ("101", "VSS"), ("19", "VSSA"), ("18", "VREFN"), ("46", "VSS_DCDC"), ("47", "VSS_DCDC"),
    ("99", "USB0_VSS"), ("33", "USB1_VSS"), ("37", "USB1_VSS"),
]
LPC55_ETYPE = {"FB": "input", "LX": "power_out", "RESETN": "input", "XTAL32M_P": "input", "XTAL32M_N": "output",
         "XTAL32K_P": "input", "XTAL32K_N": "output", "USB0_DP": "bidirectional", "USB0_DM": "bidirectional",
         "USB1_DP": "bidirectional", "USB1_DM": "bidirectional", "USB1_VBUS": "input"}

LPC55_FOOTPRINT = "EoS_Packages:HLQFP-100-1EP_14x14mm_P0.5mm_EP3.21x3.21mm"
LPC55_DATASHEET = "https://www.nxp.com/docs/en/data-sheet/LPC55S6x.pdf"


def lpc55s69jbd100() -> list:
    """NXP LPC55S69JBD100, HLQFP-100 (SOT1570-3) with exposed pad (pin 101, VSS). Pins as the
    LPC55S6x data sheet Rev. 2.5, Table 3 (100-pin HLQFP column): PIO0_0-31 on the left, PIO1_0-31
    on the right, supplies along the top, and the DC-DC node, reset, oscillators, USB and grounds
    along the bottom."""
    name = "LPC55S69JBD100"
    left = [(str(LPC55_PIO0[i]), f"PIO0_{i}") for i in range(32)]
    right = [(str(LPC55_PIO1[i]), f"PIO1_{i}") for i in range(32)]
    body = [Sym("symbol"), f"{name}_1_1",
            [Sym("rectangle"), [Sym("start"), -27.94, 43.18], [Sym("end"), 27.94, -45.72],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("background")]]]]

    def pin(kind, x, y, angle, label, number):
        return [Sym("pin"), Sym(kind), Sym("line"), [Sym("at"), x, y, angle], [Sym("length"), 2.54],
                [Sym("name"), label, _font()], [Sym("number"), number, _font()]]

    for k, (number, label) in enumerate(left):
        body.append(pin("bidirectional", -30.48, round(38.1 - 2.54 * k, 2), 0, label, number))
    for k, (number, label) in enumerate(right):
        body.append(pin("bidirectional", 30.48, round(38.1 - 2.54 * k, 2), 180, label, number))
    for k, (number, label) in enumerate(LPC55_TOP):
        body.append(pin(LPC55_ETYPE.get(label, "power_in"), round(-22.86 + 2.54 * k, 2), 45.72, 270, label, number))
    for k, (number, label) in enumerate(LPC55_BOTTOM):
        body.append(pin(LPC55_ETYPE.get(label, "power_in"), round(-22.86 + 2.54 * k, 2), -48.26, 90, label, number))
    return [Sym("symbol"), name, [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            _prop("Reference", "U", 0, 46.99), _prop("Value", name, 0, -52.07),
            _prop("Footprint", LPC55_FOOTPRINT, 0, 0, True),
            _prop("Datasheet", LPC55_DATASHEET, 0, 0, True),
            _prop("Description", "Dual Arm Cortex-M33 MCU, 150 MHz, 640 KB flash, 320 KB SRAM, USB FS + HS, "
                                 "HLQFP-100 with exposed pad (VSS)", 0, 0, True),
            body]


def _check_lpc55s69() -> None:
    """Every HLQFP-100 pin 1-100, plus the pad (101), exactly once."""
    numbers = [str(n) for n in LPC55_PIO0.values()] + [str(n) for n in LPC55_PIO1.values()] + [n for n, _ in LPC55_TOP + LPC55_BOTTOM]
    assert len(numbers) == 101, len(numbers)
    assert sorted(numbers, key=int) == [str(n) for n in range(1, 102)], sorted(set(range(1, 102)) - {int(n) for n in numbers})

# --- pin table: (number, name, KiCad electrical type), Renesas R01DS0386EJ0170 Table 1.15, LQFP 64 ---
_IO = "bidirectional"
RA2E1_LEFT = [  # system pins and oscillators, then port 0 (the ADC pins), port 4, port 5; None leaves a row free
    ("25", "~{RES}", "input"), ("26", "P201/MD", _IO), ("27", "P200/NMI", "input"), None,
    ("10", "P212/EXTAL", _IO), ("9", "P213/XTAL", _IO), None,
    ("6", "P215/XCIN", "passive"), ("7", "P214/XCOUT", "passive"), None,
    ("64", "P000", _IO), ("63", "P001", _IO), ("62", "P002", _IO), ("61", "P003", _IO), ("60", "P004", _IO),
    ("59", "P010/VREFH0", "passive"), ("58", "P011/VREFL0", "passive"), ("55", "P012", _IO), ("54", "P013", _IO),
    ("53", "P014", _IO), ("52", "P015", _IO), None,
    ("1", "P400", _IO), ("2", "P401", _IO), ("3", "P402", _IO), ("4", "P403", _IO), ("16", "P407", _IO),
    ("15", "P408", _IO), ("14", "P409", _IO), ("13", "P410", _IO), ("12", "P411", _IO), None,
    ("49", "P500", _IO), ("50", "P501", _IO), ("51", "P502", _IO),
]
RA2E1_RIGHT = [  # port 1 (with SWDIO), port 2, port 3 (with SWCLK), port 9
    ("48", "P100", _IO), ("47", "P101", _IO), ("46", "P102", _IO), ("45", "P103", _IO), ("44", "P104", _IO),
    ("43", "P105", _IO), ("42", "P106", _IO), ("41", "P107", _IO), ("33", "P108/SWDIO", _IO), ("34", "P109", _IO),
    ("35", "P110", _IO), ("36", "P111", _IO), ("37", "P112", _IO), ("38", "P113", _IO), None,
    ("24", "P204", _IO), ("23", "P205", _IO), ("22", "P206", _IO), ("21", "P207", _IO), ("20", "P208", _IO), None,
    ("32", "P300/SWCLK", _IO), ("31", "P301", _IO), ("30", "P302", _IO), ("29", "P303", _IO), ("28", "P304", _IO), None,
    ("19", "P913", _IO), ("18", "P914", _IO), ("17", "P915", _IO),
]
RA2E1_TOP = [("11", "VCC", "power_in"), ("39", "VCC", "power_in"), ("56", "AVCC0", "power_in"), ("5", "VCL", "power_out")]
RA2E1_BOTTOM = [("8", "VSS", "power_in"), ("40", "VSS", "power_in"), ("57", "AVSS0", "power_in")]

RA2E1_FOOTPRINT = "Package_QFP:LQFP-64_10x10mm_P0.5mm"
RA2E1_DATASHEET = "https://www.renesas.com/en/document/dst/ra2e1-group-datasheet"


def r7fa2e1a92dfm() -> list:
    """Renesas R7FA2E1A92DFM, RA2E1 Group, 64-pin LQFP 10 x 10 mm, 0.5 mm pitch (PLQP0064KB-C or
    PLQP0064KL-A). Pins as R01DS0386EJ0170 Rev.1.70, Table 1.15 (LQFP/QFN 64-pin column), names as
    Figure 1.3: reset, mode, NMI, both oscillators and ports 0, 4 and 5 on the left; ports 1, 2, 3 and
    9 on the right; VCC (11, 39), AVCC0 (56) and VCL (5) on top; VSS (8, 40) and AVSS0 (57) below."""
    name = "R7FA2E1A92DFM"
    body = [Sym("symbol"), f"{name}_1_1",
            [Sym("rectangle"), [Sym("start"), -17.78, 45.72], [Sym("end"), 17.78, -45.72],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("background")]]]]

    def pin(number, label, kind, x, y, angle):
        return [Sym("pin"), Sym(kind), Sym("line"), [Sym("at"), x, y, angle], [Sym("length"), 2.54],
                [Sym("name"), label, _font()], [Sym("number"), number, _font()]]

    for column, x, angle in ((RA2E1_LEFT, -20.32, 0), (RA2E1_RIGHT, 20.32, 180)):
        for row, entry in enumerate(column):
            if entry is not None:
                body.append(pin(*entry, x, round(43.18 - 2.54 * row, 2), angle))
    for k, (number, label, kind) in enumerate(RA2E1_TOP):
        body.append(pin(number, label, kind, round(-3.81 + 2.54 * k, 2), 48.26, 270))
    for k, (number, label, kind) in enumerate(RA2E1_BOTTOM):
        body.append(pin(number, label, kind, round(-2.54 + 2.54 * k, 2), -48.26, 90))
    return [Sym("symbol"), name, [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            _prop("Reference", "U", 0, 50.8), _prop("Value", name, 0, -50.8),
            _prop("Footprint", RA2E1_FOOTPRINT, 0, 0, True),
            _prop("Datasheet", RA2E1_DATASHEET, 0, 0, True),
            _prop("Description", "Renesas RA2E1 Arm Cortex-M23 MCU, 48 MHz, 128 KB code flash, 4 KB data flash, "
                                 "16 KB SRAM, 1.6-5.5 V, -40 to +85 C, LQFP-64 10 x 10 mm (R01DS0386)", 0, 0, True),
            body]


def _check_ra2e1() -> None:
    """Every LQFP-64 pin 1-64 exactly once."""
    entries = [e for e in RA2E1_LEFT + RA2E1_RIGHT if e is not None] + RA2E1_TOP + RA2E1_BOTTOM
    numbers = [e[0] for e in entries]
    assert len(numbers) == 64, len(numbers)
    assert sorted(numbers, key=int) == [str(n) for n in range(1, 65)], sorted(set(range(1, 65)) - {int(n) for n in numbers})


# --- pin table: (number, name, KiCad electrical type), Renesas R01DS0367EJ0150 Table 1.17, LQFP100 ---
RA4M2_LEFT = [  # system pins, both oscillators and USB, then port 0 (the ADC pins), port 4, P708, port 5
    ("38", "~{RES}", "input"), ("39", "P201/MD", _IO), ("40", "P200/NMI", "input"), None,
    ("14", "P212/EXTAL", _IO), ("13", "P213/XTAL", _IO), None,
    ("10", "XCIN", "passive"), ("11", "XCOUT", "passive"), None,
    ("28", "USB_DP", _IO), ("27", "USB_DM", _IO), None,
    ("100", "P000", _IO), ("99", "P001", _IO), ("98", "P002", _IO), ("97", "P003", _IO), ("96", "P004", _IO),
    ("95", "P005", _IO), ("94", "P006", _IO), ("93", "P007", _IO), ("92", "P008", _IO), ("86", "P013", _IO),
    ("85", "P014", _IO), ("84", "P015", _IO), None,
    ("1", "P400", _IO), ("2", "P401", _IO), ("3", "P402", _IO), ("4", "P403", _IO), ("5", "P404", _IO),
    ("6", "P405", _IO), ("7", "P406", _IO), ("25", "P407", _IO), ("24", "P408", _IO), ("23", "P409", _IO),
    ("22", "P410", _IO), ("21", "P411", _IO), ("20", "P412", _IO), ("19", "P413", _IO), ("18", "P414", _IO),
    ("17", "P415", _IO), ("16", "P708", _IO), None,
    ("76", "P500", _IO), ("77", "P501", _IO), ("78", "P502", _IO), ("79", "P503", _IO), ("80", "P504", _IO),
    ("81", "P505", _IO),
]
RA4M2_RIGHT = [  # port 1 (with SWDIO, TDO/SWO, TDI), port 2, port 3 (with SWCLK), port 6
    ("75", "P100", _IO), ("74", "P101", _IO), ("73", "P102", _IO), ("72", "P103", _IO), ("71", "P104", _IO),
    ("70", "P105", _IO), ("69", "P106", _IO), ("68", "P107", _IO), ("51", "P108/TMS/SWDIO", _IO),
    ("52", "P109/TDO/SWO", _IO), ("53", "P110/TDI", _IO), ("54", "P111", _IO), ("55", "P112", _IO),
    ("56", "P113", _IO), ("57", "P114", _IO), ("58", "P115", _IO), None,
    ("32", "P205", _IO), ("31", "P206", _IO), ("30", "P207", _IO), ("37", "P208", _IO), ("36", "P209", _IO),
    ("35", "P210", _IO), ("34", "P211", _IO), ("33", "P214", _IO), None,
    ("50", "P300/TCK/SWCLK", _IO), ("49", "P301", _IO), ("48", "P302", _IO), ("47", "P303", _IO),
    ("44", "P304", _IO), ("43", "P305", _IO), ("42", "P306", _IO), ("41", "P307", _IO), None,
    ("67", "P600", _IO), ("66", "P601", _IO), ("65", "P602", _IO), ("64", "P603", _IO), ("59", "P608", _IO),
    ("60", "P609", _IO), ("61", "P610", _IO),
]
RA4M2_TOP = [("15", "VCC", "power_in"), ("46", "VCC", "power_in"), ("62", "VCC", "power_in"), ("82", "VCC", "power_in"),
             ("29", "VCC_USB", "power_in"), ("8", "VBATT", "power_in"), ("88", "AVCC0", "power_in"),
             ("87", "VREFH", "power_in"), ("91", "VREFH0", "power_in"), ("9", "VCL", "power_out")]
RA4M2_BOTTOM = [("12", "VSS", "power_in"), ("45", "VSS", "power_in"), ("63", "VSS", "power_in"), ("83", "VSS", "power_in"),
                ("26", "VSS_USB", "power_in"), ("89", "AVSS0/VREFL", "power_in"), ("90", "VREFL0", "power_in")]

RA4M2_FOOTPRINT = "Package_QFP:LQFP-100_14x14mm_P0.5mm"
RA4M2_DATASHEET = "https://www.renesas.com/en/document/dst/ra4m2-group-datasheet"


def r7fa4m2ad3cfp() -> list:
    """Renesas R7FA4M2AD3CFP, RA4M2 Group, 100-pin LQFP 14 x 14 mm, 0.5 mm pitch (PLQP0100KB-B).
    Pins as R01DS0367EJ0150 Rev.1.50, Table 1.17 (LQFP100 column), names as Figure 1.3: reset,
    mode, NMI, both oscillators, USB and ports 0, 4, 5 and P708 on the left; ports 1, 2, 3 and 6 on
    the right; VCC (15, 46, 62, 82), VCC_USB (29), VBATT (8), AVCC0 (88), VREFH (87), VREFH0 (91) and
    VCL (9) on top; VSS (12, 45, 63, 83), VSS_USB (26), AVSS0/VREFL (89) and VREFL0 (90) below."""
    name = "R7FA4M2AD3CFP"
    body = [Sym("symbol"), f"{name}_1_1",
            [Sym("rectangle"), [Sym("start"), -20.32, 66.04], [Sym("end"), 20.32, -66.04],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("background")]]]]

    def pin(number, label, kind, x, y, angle):
        return [Sym("pin"), Sym(kind), Sym("line"), [Sym("at"), x, y, angle], [Sym("length"), 2.54],
                [Sym("name"), label, _font()], [Sym("number"), number, _font()]]

    for column, x, angle in ((RA4M2_LEFT, -22.86, 0), (RA4M2_RIGHT, 22.86, 180)):
        for row, entry in enumerate(column):
            if entry is not None:
                body.append(pin(*entry, x, round(63.5 - 2.54 * row, 2), angle))
    for k, (number, label, kind) in enumerate(RA4M2_TOP):
        body.append(pin(number, label, kind, round(-11.43 + 2.54 * k, 2), 68.58, 270))
    for k, (number, label, kind) in enumerate(RA4M2_BOTTOM):
        body.append(pin(number, label, kind, round(-7.62 + 2.54 * k, 2), -68.58, 90))
    return [Sym("symbol"), name, [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            _prop("Reference", "U", 0, 71.12), _prop("Value", name, 0, -71.12),
            _prop("Footprint", RA4M2_FOOTPRINT, 0, 0, True),
            _prop("Datasheet", RA4M2_DATASHEET, 0, 0, True),
            _prop("Description", "Renesas RA4M2 Arm Cortex-M33 MCU, 100 MHz, 512 KB code flash, 8 KB data flash, "
                                 "128 KB SRAM, USB 2.0 full speed, 2.7-3.6 V, -40 to +105 C, LQFP-100 14 x 14 mm "
                                 "(R01DS0367)", 0, 0, True),
            body]


def _check_ra4m2() -> None:
    """Every LQFP-100 pin 1-100 exactly once."""
    entries = [e for e in RA4M2_LEFT + RA4M2_RIGHT if e is not None] + RA4M2_TOP + RA4M2_BOTTOM
    numbers = [e[0] for e in entries]
    assert len(numbers) == 100, len(numbers)
    assert sorted(numbers, key=int) == [str(n) for n in range(1, 101)], sorted(set(range(1, 101)) - {int(n) for n in numbers})


# --- pin table: (number, name, KiCad electrical type), Renesas R01DS0131EJ0380 section 1.3.11, 64-pin LFQFP ---
RL78G13_LEFT = [  # reset and TOOL0, both oscillators, P137, then ports 0, 2, 12/13 and 14; None leaves a row free
    ("6", "~{RESET}", "input"), ("5", "P40/TOOL0", _IO), None,
    ("11", "P121/X1", "passive"), ("10", "P122/X2", "passive"), None,
    ("8", "P123/XT1", "passive"), ("7", "P124/XT2", "passive"), None,
    ("9", "P137/INTP0", "input"), None,
    ("62", "P00/TI00", _IO), ("61", "P01/TO00", _IO), ("60", "P02/TxD1", _IO), ("59", "P03/RxD1", _IO),
    ("58", "P04/SCK10", _IO), ("31", "P05/TO05", _IO), ("30", "P06/TO06", _IO), None,
    ("56", "P20/AVREFP", _IO), ("55", "P21/AVREFM", _IO), ("54", "P22/ANI2", _IO), ("53", "P23/ANI3", _IO),
    ("52", "P24/ANI4", _IO), ("51", "P25/ANI5", _IO), ("50", "P26/ANI6", _IO), ("49", "P27/ANI7", _IO), None,
    ("1", "P120/ANI19", _IO), ("57", "P130", "output"), None,
    ("64", "P140/INTP6", _IO), ("63", "P141/INTP7", _IO), ("47", "P146", _IO), ("48", "P147/ANI18", _IO),
]
RL78G13_RIGHT = [  # port 1 (with TOOLTxD/TOOLRxD), ports 3 and 4, port 5, port 6 (N-ch open drain), port 7
    ("46", "P10/SCK00", _IO), ("45", "P11/TOOLRxD", _IO), ("44", "P12/TOOLTxD", _IO), ("43", "P13/TxD2", _IO),
    ("42", "P14/RxD2", _IO), ("41", "P15/SCK20", _IO), ("40", "P16/TO01", _IO), ("39", "P17/TO02", _IO), None,
    ("32", "P30/INTP3", _IO), ("21", "P31/TO03", _IO), ("4", "P41/TO07", _IO), ("3", "P42/TO04", _IO),
    ("2", "P43", _IO), None,
    ("33", "P50/INTP1", _IO), ("34", "P51/INTP2", _IO), ("35", "P52", _IO), ("36", "P53", _IO), ("37", "P54", _IO),
    ("38", "P55", _IO), None,
    ("17", "P60/SCLA0", _IO), ("18", "P61/SDAA0", _IO), ("19", "P62", _IO), ("20", "P63", _IO), None,
    ("29", "P70/KR0", _IO), ("28", "P71/KR1", _IO), ("27", "P72/KR2", _IO), ("26", "P73/KR3", _IO),
    ("25", "P74/KR4", _IO), ("24", "P75/KR5", _IO), ("23", "P76/KR6", _IO), ("22", "P77/KR7", _IO),
]
RL78G13_TOP = [("15", "VDD", "power_in"), ("16", "EVDD0", "power_in"), ("12", "REGC", "power_out")]
RL78G13_BOTTOM = [("13", "VSS", "power_in"), ("14", "EVSS0", "power_in")]

RL78G13_FOOTPRINT = "Package_QFP:LQFP-64_10x10mm_P0.5mm"
RL78G13_DATASHEET = "https://www.renesas.com/en/document/dst/rl78g13-data-sheet"


def r5f100leafb() -> list:
    """Renesas R5F100LEAFB, RL78/G13, 64-pin LFQFP 10 x 10 mm, 0.5 mm pitch (PLQP0064KF-A or
    PLQP0064KB-C). Pins as R01DS0131EJ0380 Rev.3.80, section 1.3.11 (64-pin products, top view):
    reset, TOOL0, both oscillators, P137 and ports 0, 2, 12/13 and 14 on the left; ports 1, 3, 4,
    5, 6 and 7 on the right; VDD (15), EVDD0 (16) and REGC (12) on top; VSS (13) and EVSS0 (14) below."""
    name = "R5F100LEAFB"
    body = [Sym("symbol"), f"{name}_1_1",
            [Sym("rectangle"), [Sym("start"), -17.78, 45.72], [Sym("end"), 17.78, -45.72],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("background")]]]]

    def pin(number, label, kind, x, y, angle):
        return [Sym("pin"), Sym(kind), Sym("line"), [Sym("at"), x, y, angle], [Sym("length"), 2.54],
                [Sym("name"), label, _font()], [Sym("number"), number, _font()]]

    for column, x, angle in ((RL78G13_LEFT, -20.32, 0), (RL78G13_RIGHT, 20.32, 180)):
        for row, entry in enumerate(column):
            if entry is not None:
                body.append(pin(*entry, x, round(43.18 - 2.54 * row, 2), angle))
    for k, (number, label, kind) in enumerate(RL78G13_TOP):
        body.append(pin(number, label, kind, round(-2.54 + 2.54 * k, 2), 48.26, 270))
    for k, (number, label, kind) in enumerate(RL78G13_BOTTOM):
        body.append(pin(number, label, kind, round(-1.27 + 2.54 * k, 2), -48.26, 90))
    return [Sym("symbol"), name, [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            _prop("Reference", "U", 0, 50.8), _prop("Value", name, 0, -50.8),
            _prop("Footprint", RL78G13_FOOTPRINT, 0, 0, True),
            _prop("Datasheet", RL78G13_DATASHEET, 0, 0, True),
            _prop("Description", "Renesas RL78/G13 16-bit MCU, 32 MHz, 64 KB code flash, 4 KB data flash, 4 KB RAM, "
                                 "1.6-5.5 V, -40 to +85 C, LFQFP-64 10 x 10 mm (R01DS0131)", 0, 0, True),
            body]


def _check_rl78g13() -> None:
    """Every LFQFP-64 pin 1-64 exactly once, and no pin name used twice."""
    entries = [e for e in RL78G13_LEFT + RL78G13_RIGHT if e is not None] + RL78G13_TOP + RL78G13_BOTTOM
    numbers = [e[0] for e in entries]
    assert len(numbers) == 64, len(numbers)
    assert sorted(numbers, key=int) == [str(n) for n in range(1, 65)], sorted(set(range(1, 65)) - {int(n) for n in numbers})
    names = [e[1] for e in entries]
    assert len(set(names)) == len(names), sorted({n for n in names if names.count(n) > 1})



# --- pin table: (number, name, KiCad electrical type), TI SPRS945H (March 2026) Table 5-1 "Pin
# Attributes", 100 PZ column, checked against Figure 5-1 (100-Pin PZ, top view) ---
F28_LEFT = [  # reset, clock, JTAG, regulator enable, flash test pins, then the 21 ADC pins and the PGA inputs
    ("2", "~{XRS}", "open_collector"), ("69", "X1", _IO), ("68", "GPIO18_X2", _IO), None,
    ("60", "TCK", "input"), ("62", "TMS", _IO), ("63", "GPIO35/TDI", _IO), ("61", "GPIO37/TDO", _IO), None,
    ("73", "VREGENZ", "input"), ("49", "FLT1", _IO), ("48", "FLT2", _IO), None,
    ("23", "A0/B15/C15/DACA_OUT", "passive"), ("22", "A1/DACB_OUT", "passive"), ("9", "A2/B6/PGA1_OF", "passive"),
    ("10", "A3", "passive"), ("36", "A4/B8/PGA2_OF", "passive"), ("35", "A5", "passive"),
    ("6", "A6/PGA5_OF", "passive"), ("37", "A8/PGA6_OF", "passive"), ("38", "A9", "passive"),
    ("40", "A10/B1/C10/PGA7_OF", "passive"), ("41", "B0", "passive"), ("7", "B2/C6/PGA3_OF", "passive"),
    ("8", "B3/VDAC", "passive"), ("39", "B4/C8/PGA4_OF", "passive"), ("19", "C0", "passive"), ("29", "C1", "passive"),
    ("21", "C2", "passive"), ("31", "C3/PGA4_IN", "passive"), ("17", "C4", "passive"), ("28", "C5/PGA6_IN", "passive"),
    ("44", "C14", "passive"), None,
    ("18", "PGA1_IN", "passive"), ("30", "PGA2_IN", "passive"), ("20", "PGA3_IN", "passive"),
    ("16", "PGA5_IN", "passive"), ("43", "PGA7_IN", "passive"),
]
F28_RIGHT = [  # the GPIOs by number; GPIO18, GPIO35 and GPIO37 are on the left with X1 and JTAG
    ("79", "GPIO0", _IO), ("78", "GPIO1", _IO), ("77", "GPIO2", _IO), ("76", "GPIO3", _IO), ("75", "GPIO4", _IO),
    ("89", "GPIO5", _IO), ("97", "GPIO6", _IO), ("84", "GPIO7", _IO), ("74", "GPIO8", _IO), ("90", "GPIO9", _IO), None,
    ("93", "GPIO10", _IO), ("52", "GPIO11", _IO), ("51", "GPIO12", _IO), ("50", "GPIO13", _IO), ("96", "GPIO14", _IO),
    ("95", "GPIO15", _IO), ("54", "GPIO16", _IO), ("55", "GPIO17", _IO), None,
    ("83", "GPIO22_VFBSW", _IO), ("81", "GPIO23_VSW", _IO), ("56", "GPIO24", _IO), ("57", "GPIO25", _IO),
    ("58", "GPIO26", _IO), ("59", "GPIO27", _IO), None,
    ("1", "GPIO28", _IO), ("100", "GPIO29", _IO), ("98", "GPIO30", _IO), ("99", "GPIO31", _IO), ("64", "GPIO32", _IO),
    ("53", "GPIO33", _IO), ("94", "GPIO34", _IO), None,
    ("91", "GPIO39", _IO), ("85", "GPIO40", _IO), ("65", "GPIO56", _IO), ("66", "GPIO57", _IO), ("67", "GPIO58", _IO),
    ("92", "GPIO59", _IO),
]
F28_TOP = [  # 3.3 V supplies, 1.2 V core pins, the ADC high references
    ("3", "VDDIO", "power_in"), ("47", "VDDIO", "power_in"), ("70", "VDDIO", "power_in"), ("88", "VDDIO", "power_in"),
    ("80", "VDDIO_SW", "power_in"), ("11", "VDDA", "power_in"), ("34", "VDDA", "power_in"),
    ("4", "VDD", "power_in"), ("46", "VDD", "power_in"), ("71", "VDD", "power_in"), ("87", "VDD", "power_in"),
    ("25", "VREFHIA", "passive"), ("24", "VREFHIB/VREFHIC", "passive"),
]
F28_BOTTOM = [  # grounds, the ADC low references and the PGA grounds
    ("5", "VSS", "power_in"), ("45", "VSS", "power_in"), ("72", "VSS", "power_in"), ("86", "VSS", "power_in"),
    ("82", "VSS_SW", "power_in"), ("12", "VSSA", "power_in"), ("33", "VSSA", "power_in"),
    ("27", "VREFLOA", "input"), ("26", "VREFLOB/VREFLOC", "input"), ("14", "PGA1_GND", "input"),
    ("32", "PGA2_GND/PGA4_GND/PGA6_GND", "input"), ("15", "PGA3_GND", "input"), ("13", "PGA5_GND", "input"),
    ("42", "PGA7_GND", "input"),
]

F28_FOOTPRINT = "Package_QFP:LQFP-100_14x14mm_P0.5mm"
F28_DATASHEET = "https://www.ti.com/lit/ds/symlink/tms320f280049c.pdf"


def tms320f280049cpz() -> list:
    """TI TMS320F280049C, 100-pin LQFP (PZ, TI drawing PZ0100A). Pins as TI SPRS945H Table 5-1 (Pin
    Attributes, 100 PZ column) and Figure 5-1, each named with its fixed functions: reset, X1/X2, JTAG,
    VREGENZ, the flash test pins and the analog pins (ADC inputs with their DAC and PGA functions, then
    the PGA-only inputs) on the left; the GPIOs on the right; the 3.3 V supplies, the 1.2 V core pins and
    the ADC high references on top; the grounds, the ADC low references and the PGA grounds below."""
    name = "TMS320F280049CPZ"
    body = [Sym("symbol"), f"{name}_1_1",
            [Sym("rectangle"), [Sym("start"), -38.1, 53.34], [Sym("end"), 38.1, -53.34],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("background")]]]]

    def pin(number, label, kind, x, y, angle):
        return [Sym("pin"), Sym(kind), Sym("line"), [Sym("at"), x, y, angle], [Sym("length"), 2.54],
                [Sym("name"), label, _font()], [Sym("number"), number, _font()]]

    for column, x, angle in ((F28_LEFT, -40.64, 0), (F28_RIGHT, 40.64, 180)):
        for row, entry in enumerate(column):
            if entry is not None:
                body.append(pin(*entry, x, round(50.8 - 2.54 * row, 2), angle))
    for k, (number, label, kind) in enumerate(F28_TOP):
        body.append(pin(number, label, kind, round(-15.24 + 2.54 * k, 2), 55.88, 270))
    for k, (number, label, kind) in enumerate(F28_BOTTOM):
        body.append(pin(number, label, kind, round(-16.51 + 2.54 * k, 2), -55.88, 90))
    return [Sym("symbol"), name, [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            _prop("Reference", "U", 0, 58.42), _prop("Value", name, 0, -58.42),
            _prop("Footprint", F28_FOOTPRINT, 0, 0, True),
            _prop("Datasheet", F28_DATASHEET, 0, 0, True),
            _prop("Description", "TI C2000 real-time MCU, C28x 100 MHz with FPU, TMU and CLA, 256 KB flash, 100 KB RAM, "
                                 "three 12-bit ADCs, LQFP-100 14 x 14 mm (TI SPRS945H)", 0, 0, True),
            body]


def _check_f280049c() -> None:
    """Every LQFP-100 pin 1-100 exactly once, and no name given twice except the supply and ground pins."""
    entries = [e for e in F28_LEFT + F28_RIGHT if e is not None] + F28_TOP + F28_BOTTOM
    numbers = [e[0] for e in entries]
    assert len(numbers) == 100, len(numbers)
    assert sorted(numbers, key=int) == [str(n) for n in range(1, 101)], sorted(set(range(1, 101)) - {int(n) for n in numbers})
    names = [e[1] for e in entries if e[1] not in ("VDDIO", "VDDA", "VDD", "VSS", "VSSA")]
    assert len(names) == len(set(names)), sorted({n for n in names if names.count(n) > 1})


# --- pin table: (number, name, KiCad electrical type), TI SPMS433B (June 18, 2014): the GPIO pins from
# Table 26-5 (GPIO Pins and Alternate Functions), the fixed pins from Table 26-3 (Signals by Signal
# Name), checked against Figure 25-1 (128-Pin TQFP Package Pin Diagram). A name carries the pin's
# fixed or analog function where it has one (Table 26-5, "Analog or Special Function") ---
TM4C129_LEFT = [  # reset, both oscillators, hibernation, the Ethernet PHY, then ports A to E and L
    ("70", "~{RST}", "input"), None,
    ("88", "OSC0", "passive"), ("89", "OSC1", "passive"), ("66", "XOSC0", "passive"), ("67", "XOSC1", "passive"), None,
    ("64", "~{WAKE}", "input"), ("65", "~{HIB}", "output"), None,
    ("53", "EN0RXIN", _IO), ("54", "EN0RXIP", _IO), ("56", "EN0TXON", _IO), ("57", "EN0TXOP", _IO),
    ("59", "RBIAS", "passive"), None,
    ("33", "PA0/U0Rx", _IO), ("34", "PA1/U0Tx", _IO), ("35", "PA2", _IO), ("36", "PA3", _IO), ("37", "PA4", _IO),
    ("38", "PA5", _IO), ("40", "PA6", _IO), ("41", "PA7", _IO), None,
    ("95", "PB0/USB0ID", _IO), ("96", "PB1/USB0VBUS", _IO), ("91", "PB2", _IO), ("92", "PB3", _IO),
    ("121", "PB4/AIN10", _IO), ("120", "PB5/AIN11", _IO), None,
    ("100", "PC0/TCK/SWCLK", _IO), ("99", "PC1/TMS/SWDIO", _IO), ("98", "PC2/TDI", _IO), ("97", "PC3/TDO/SWO", _IO),
    ("25", "PC4/C1-", _IO), ("24", "PC5/C1+", _IO), ("23", "PC6/C0+", _IO), ("22", "PC7/C0-", _IO), None,
    ("1", "PD0/AIN15", _IO), ("2", "PD1/AIN14", _IO), ("3", "PD2/AIN13", _IO), ("4", "PD3/AIN12", _IO),
    ("125", "PD4/AIN7", _IO), ("126", "PD5/AIN6", _IO), ("127", "PD6/AIN5", _IO), ("128", "PD7/AIN4/NMI", _IO), None,
    ("15", "PE0/AIN3", _IO), ("14", "PE1/AIN2", _IO), ("13", "PE2/AIN1", _IO), ("12", "PE3/AIN0", _IO),
    ("123", "PE4/AIN9", _IO), ("124", "PE5/AIN8", _IO), None,
    ("81", "PL0", _IO), ("82", "PL1", _IO), ("83", "PL2", _IO), ("84", "PL3", _IO), ("85", "PL4", _IO), ("86", "PL5", _IO),
    ("94", "PL6/USB0DP", _IO), ("93", "PL7/USB0DM", _IO),
]
TM4C129_RIGHT = [  # ports F to K, M, N, P and Q
    ("42", "PF0", _IO), ("43", "PF1", _IO), ("44", "PF2", _IO), ("45", "PF3", _IO), ("46", "PF4", _IO), None,
    ("49", "PG0", _IO), ("50", "PG1", _IO), None,
    ("29", "PH0", _IO), ("30", "PH1", _IO), ("31", "PH2", _IO), ("32", "PH3", _IO), None,
    ("116", "PJ0", _IO), ("117", "PJ1", _IO), None,
    ("18", "PK0/AIN16", _IO), ("19", "PK1/AIN17", _IO), ("20", "PK2/AIN18", _IO), ("21", "PK3/AIN19", _IO),
    ("63", "PK4", _IO), ("62", "PK5", _IO), ("61", "PK6", _IO), ("60", "PK7", _IO), None,
    ("78", "PM0", _IO), ("77", "PM1", _IO), ("76", "PM2", _IO), ("75", "PM3", _IO),
    ("74", "PM4/TMPR3", _IO), ("73", "PM5/TMPR2", _IO), ("72", "PM6/TMPR1", _IO), ("71", "PM7/TMPR0", _IO), None,
    ("107", "PN0", _IO), ("108", "PN1", _IO), ("109", "PN2", _IO), ("110", "PN3", _IO), ("111", "PN4", _IO),
    ("112", "PN5", _IO), None,
    ("118", "PP0/C2+", _IO), ("119", "PP1/C2-", _IO), ("103", "PP2", _IO), ("104", "PP3", _IO), ("105", "PP4", _IO),
    ("106", "PP5", _IO), None,
    ("5", "PQ0", _IO), ("6", "PQ1", _IO), ("11", "PQ2", _IO), ("27", "PQ3", _IO), ("102", "PQ4", _IO),
]
TM4C129_TOP = [  # 3.3 V supplies, the ADC's analog supply and high reference, the 1.2 V core pins, VBAT
    *[(n, "VDD", "power_in") for n in ("7", "16", "26", "28", "39", "47", "51", "52", "69", "79", "90", "101", "113", "122")],
    ("8", "VDDA", "power_in"), ("9", "VREFA+", "power_in"), ("87", "VDDC", "power_in"), ("115", "VDDC", "power_in"),
    ("68", "VBAT", "power_in"),
]
TM4C129_BOTTOM = [(n, "GND", "power_in") for n in ("17", "48", "55", "58", "80", "114")] + [("10", "GNDA", "power_in")]

TM4C129_FOOTPRINT = "Package_QFP:TQFP-128_14x14mm_P0.4mm"
TM4C129_DATASHEET = "https://www.ti.com/lit/ds/symlink/tm4c1294ncpdt.pdf"


def tm4c1294ncpdt() -> list:
    """TI TM4C1294NCPDT, 128-pin TQFP (PDT). Pins as TI SPMS433B Tables 26-5 and 26-3 and Figure 25-1:
    reset, the main and hibernation oscillators, WAKE/HIB, the Ethernet PHY pins and RBIAS, then ports
    A to E and L on the left; ports F to K, M, N, P and Q on the right; VDD, VDDA, VREFA+, VDDC and VBAT
    on top; GND and GNDA below. The oscillator pins and RBIAS are passive (a crystal, a resistor), as on
    the TM4C123GH6PM symbol above."""
    name = "TM4C1294NCPDT"
    rows = max(len(TM4C129_LEFT), len(TM4C129_RIGHT))
    top = round(2.54 * (rows + 1) / 2, 2)
    top = round(2.54 * round(top / 2.54), 2)
    body = [Sym("symbol"), f"{name}_1_1",
            [Sym("rectangle"), [Sym("start"), -25.4, top], [Sym("end"), 25.4, -top],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("background")]]]]

    def pin(number, label, kind, x, y, angle):
        return [Sym("pin"), Sym(kind), Sym("line"), [Sym("at"), x, y, angle], [Sym("length"), 2.54],
                [Sym("name"), label, _font()], [Sym("number"), number, _font()]]

    for column, x, angle in ((TM4C129_LEFT, -27.94, 0), (TM4C129_RIGHT, 27.94, 180)):
        for row, entry in enumerate(column):
            if entry is not None:
                body.append(pin(*entry, x, round(top - 2.54 * (row + 1), 2), angle))
    for k, (number, label, kind) in enumerate(TM4C129_TOP):
        body.append(pin(number, label, kind, round(-22.86 + 2.54 * k, 2), round(top + 2.54, 2), 270))
    for k, (number, label, kind) in enumerate(TM4C129_BOTTOM):
        body.append(pin(number, label, kind, round(-7.62 + 2.54 * k, 2), round(-top - 2.54, 2), 90))
    return [Sym("symbol"), name, [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            _prop("Reference", "U", 0, round(top + 5.08, 2)), _prop("Value", name, 0, round(-top - 5.08, 2)),
            _prop("Footprint", TM4C129_FOOTPRINT, 0, 0, True),
            _prop("Datasheet", TM4C129_DATASHEET, 0, 0, True),
            _prop("Description", "Tiva C Arm Cortex-M4F MCU, 120 MHz, 1 MB flash, 256 kB SRAM, 6 kB EEPROM, 10/100 "
                                 "Ethernet MAC and PHY, USB 2.0 OTG, TQFP-128 14 x 14 mm (TI SPMS433B)", 0, 0, True),
            body]


def _check_tm4c1294() -> None:
    """Every TQFP-128 pin 1-128 exactly once, the 90 GPIOs named PA0-PQ4 as Table 26-5 lists them, and no
    name given twice except the supply and ground pins."""
    entries = [e for e in TM4C129_LEFT + TM4C129_RIGHT if e is not None] + TM4C129_TOP + TM4C129_BOTTOM
    numbers = [e[0] for e in entries]
    assert len(numbers) == 128, len(numbers)
    assert sorted(numbers, key=int) == [str(n) for n in range(1, 129)], sorted(set(range(1, 129)) - {int(n) for n in numbers})
    gpio = [e[1].split("/")[0] for e in entries if e[1].startswith("P")]
    assert len(gpio) == 90 and len(set(gpio)) == 90, len(gpio)
    names = [e[1] for e in entries if e[1] not in ("VDD", "VDDC", "GND")]
    assert len(names) == len(set(names)), sorted({n for n in names if names.count(n) > 1})


def main() -> int:
    _check_lpc55s69()
    _check_ra2e1()
    _check_ra4m2()
    _check_rl78g13()
    _check_f280049c()
    _check_tm4c1294()
    for file, symbols in (("EoS_Connectors", [double_row(50), double_row(49)]), ("EoS_Parts", [tpd4eusb30_flow_through()]),
                          ("EoS_Sensors", [adt7410()]), ("EoS_MCU", [tm4c123gh6pm(), lpc55s69jbd100(), r7fa2e1a92dfm(),
                                       r7fa4m2ad3cfp(), r5f100leafb(), tms320f280049cpz(),
                                       tm4c1294ncpdt()])):
        lib = [Sym("kicad_symbol_lib"), [Sym("version"), 20231120], [Sym("generator"), "eos_boards"], *symbols]
        out = HERE / f"{file}.kicad_sym"
        out.write_text(dumps(lib) + "\n")
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
