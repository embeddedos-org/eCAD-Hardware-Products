"""EoS Motion Wing: an accelerometer and temperature FeatherWing, designed by Kartikeydheer Srivastava.

Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved: this design file is not under
the repository's MIT licence; see boards/eos/eos-motion-wing/LICENSE.txt.

A FeatherWing with an Analog Devices ADXL343 3-axis accelerometer (LGA-14) and an ADT7410 16-bit
temperature sensor (SOIC-8), both on the Feather's I2C bus and both powered from its 3V pin.

Form factor, from Adafruit's Feather Specification
(https://learn.adafruit.com/adafruit-feather/feather-specification):

* 0.9 x 2.0 in (22.86 x 50.8 mm) with 0.1 in holes at each corner. The page's dimension drawing
  puts the hole centres 0.1 in from each edge (1.8 in and 0.7 in apart). KiCad's nearest stock
  hole is 2.5 mm, unplated.
* A 16-pin strip along the bottom edge, centred 1.0 in from the left edge, and a 12-pin strip
  along the top edge, centred 1.2 in from the left edge, 0.8 in apart. So pin 1 of the 16-pin
  strip is at (6.35, 21.59) mm and pin 1 of the 12-pin strip at (16.51, 1.27) mm; both strips end
  at x = 44.45 mm.
* Pin order from the USB end (the spec's naming table). 16-pin: RST, 3V, AREF, GND, A0-A5, SCK,
  MO, MI, RX, TX, free pin. 12-pin: BAT, EN, USB, D13, D12, D11, D10, D9, D6, D5, SCL, SDA.
* The spec puts I2C pull-ups on the wings, not on the Feather, so this wing carries them. JP1
  takes them off the bus when the Feather or another wing in the stack already has them.
* The 3V pin is the host Feather's 3.3 V regulator output, so its tolerance is that regulator's (an
  AP2112K-3.3 holds 3.25-3.35 V: Diodes DS39724 Rev. 2-2, AP2112-3.3 Electrical Characteristics, page 8);
  the spec recommends that a Feather leave at least 100 mA for wings.

The headers sit on the back: a wing's male headers point down into the Feather's sockets, with
their plastic under the wing. The spec gives no corner radius; 2.54 mm is used, concentric with
the corner holes.

Every value follows the part's data sheet:

* ADXL343 (Analog Devices data sheet Rev. 0). CS tied to VDD I/O selects I2C (p. 16). ALT
  ADDRESS (SDO, pin 12) has no internal pull and must go to VDD I/O or GND (p. 16), so it goes
  through JP3: GND as delivered gives 0x53, VDD I/O gives 0x1D. VS and VDD I/O share the 3V pin,
  which the data sheet allows for single-supply operation (p. 11). Decoupling (p. 26): 1 uF
  tantalum at VS and 0.1 uF ceramic at VDD I/O is the base recommendation; where VS and VDD I/O
  cannot be separate supplies it suggests more filtering, such as 10 uF tantalum in parallel with
  0.1 uF ceramic at VS. That is what this board fits (C1 + C2), and it is also the condition
  Table 1 is specified under (CS = 10 uF tantalum, CI/O = 0.1 uF); C3 is the 0.1 uF at VDD I/O.
  Reserved pins 3 and 11 are left open, which Table 5 allows (pin 3: VS or open; pin 11: GND or
  open); pin 10 has no internal connection. INT1 and INT2 are push-pull, active high by default
  (p. 18), so they need no pull-up.
* ADT7410 (Analog Devices data sheet Rev. C). 0.1 uF ceramic at VDD, as close to the pin as
  possible (Table 4; Supply Decoupling, p. 23). A0 and A1 must go to GND or VDD (Table 4): JP2
  and JP4 tie both to GND as delivered, 0x48; A0 high gives 0x49, A1 high 0x4A, both 0x4B
  (Table 20, p. 17). INT and CT are open drain and need a 10 kohm pull-up to VDD (p. 21): R3 and
  R4, on the sensor side of the jumpers, so the pins idle high whether or not a jumper is made.
* I2C pull-ups, 10 kohm (R1, R2). The ADT7410 data sheet recommends 10 kohm on SDA and SCL
  (p. 17), and it specifies VOL <= 0.4 V for its open-drain outputs at 1 mA at 3.3 V only
  (Table 1). Everything pulling up the bus must therefore add up to at least
  (3.3 - 0.4) V / 1 mA = 2.9 kohm; 10 kohm leaves room for other pull-ups in parallel.
  NXP UM10204 Rev. 7.0, section 7.1 and Table 10: Rp(max) = tr / (0.8473 x Cb), so 10 kohm keeps
  Standard-mode (tr <= 1000 ns) up to 118 pF of bus and Fast-mode (tr <= 300 ns) up to 35 pF.
  The two chips alone add 8 pF (ADXL343, Table 11) + 10 pF max (ADT7410, Table 1).
* Interrupts reach the Feather only through solder jumpers, open as delivered: ADXL343 INT1 to D5
  (JP5), INT2 to D6 (JP6), ADT7410 INT to D10 (JP7), CT to D11 (JP8). The four are from the
  spec's seven general-purpose pins; D13 is avoided because the spec shares the user LED with it.
  Left open, the pins stay free for other wings (the spec expects only I2C wings to stack).

Supply current: ADXL343 140 uA typical at ODR >= 100 Hz, ADT7410 250 uA maximum while converting
(each data sheet's Table 1), plus 0.33 mA per I2C line while it is held low.
"""

from __future__ import annotations

from ..design import NC, Board, BringUp, BringUpTest, Part, Rail, bench_pad
from .owner import CONTACT, LICENCE, LICENCE_TERMS, OWNER

R0603 = "Resistor_SMD:R_0603_1608Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
JUMPER2_OPEN = "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm"
JUMPER2_BRIDGED = "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm"
JUMPER3 = "Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm"
ADXL343_DS = "ADI ADXL343 data sheet Rev. 0"
ADT7410_DS = "ADI ADT7410 data sheet Rev. C"


def res(ref, value, a, b, sch, desc):
    return Part(ref, "Device:R_Small", value, R0603, sch, {"1": a, "2": b}, fields={"Description": desc})


def cap(ref, value, a, b, sch, desc):
    return Part(ref, "Device:C_Small", value, C0603, sch, {"1": a, "2": b}, fields={"Description": desc})


def strap(ref, value, net, sch, desc):
    """A 3-pad solder jumper: 1-2 (GND) bridged as delivered, cut and bridge 2-3 for 3.3 V."""
    return Part(ref, "Jumper:SolderJumper_3_Bridged12", value, JUMPER3, sch, {"A": "GND", "C": net, "B": "+3V3"},
                fields={"Description": desc})


def link(ref, a, b, sch, desc):
    """A 2-pad solder jumper, open as delivered."""
    return Part(ref, "Jumper:SolderJumper_2_Open", "open", JUMPER2_OPEN, sch, {"A": a, "B": b},
                fields={"Description": desc})


# The Feather's header pins, by pin number from the USB end (Feather Specification, "Pin Naming").
# Pins this wing does not use are left unconnected.
FEATHER_16 = {2: "+3V3", 4: "GND"}                                  # 1 RST, 2 3V, 3 AREF, 4 GND, 5-10 A0-A5, ...
FEATHER_12 = {6: "D11", 7: "D10", 9: "D6", 10: "D5", 11: "I2C_SCL", 12: "I2C_SDA"}   # 1 BAT, 2 EN, 3 USB, 4 D13, ...

W, H = 50.8, 22.86                         # 2.0 x 0.9 in
HEADER_16_PIN1 = (6.35, 21.59)             # centred 1.0 in from the left edge, 0.05 in from the bottom edge
HEADER_12_PIN1 = (16.51, 1.27)             # centred 1.2 in from the left edge, 0.8 in above the 16-pin strip
HOLES = [(2.54, 2.54), (48.26, 2.54), (2.54, 20.32), (48.26, 20.32)]   # 0.1 in in from each edge

PARTS = [
    # ---- Feather headers (male, on the back) ------------------------------------------------------
    Part("J1", "Connector_Generic:Conn_01x16", "Feather 16-pin", "Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical",
         (60, 130), {str(n): FEATHER_16.get(n, NC) for n in range(1, 17)}, side="B",
         fields={"Manufacturer": "Wurth Elektronik", "MPN": "61301611121",
                 "Description": "Pin header 1x16 2.54 mm, Feather 16-pin strip: 1 RST, 2 3V, 3 AREF, 4 GND, 5-10 A0-A5, "
                                "11 SCK, 12 MO, 13 MI, 14 RX, 15 TX, 16 free (Feather Specification)"}),
    Part("J2", "Connector_Generic:Conn_01x12", "Feather 12-pin", "Connector_PinHeader_2.54mm:PinHeader_1x12_P2.54mm_Vertical",
         (60, 200), {str(n): FEATHER_12.get(n, NC) for n in range(1, 13)}, side="B",
         fields={"Manufacturer": "Wurth Elektronik", "MPN": "61301211121",
                 "Description": "Pin header 1x12 2.54 mm, Feather 12-pin strip: 1 BAT, 2 EN, 3 USB, 4 D13, 5 D12, 6 D11, "
                                "7 D10, 8 D9, 9 D6, 10 D5, 11 SCL, 12 SDA (Feather Specification)"}),

    # ---- ADXL343 accelerometer, I2C 0x53 (0x1D) --------------------------------------------------
    Part("U1", "Sensor_Motion:ADXL343", "ADXL343", "Package_LGA:LGA-14_3x5mm_P0.8mm_LayoutBorder1x6y", (170, 120),
         {"1": "+3V3", "2": "GND", "3": NC, "4": "GND", "5": "GND", "6": "+3V3", "7": "+3V3",
          "8": "ACC_INT1", "9": "ACC_INT2", "10": NC, "11": NC, "12": "ACC_SDO", "13": "I2C_SDA", "14": "I2C_SCL"},
         fields={"Manufacturer": "Analog Devices", "MPN": "ADXL343BCCZ-RL7",
                 "Description": "3-axis accelerometer, I2C 0x53 (0x1D with ALT ADDRESS high); CS high selects I2C"}),
    Part("C1", "Device:C_Polarized_Small", "10u", "Capacitor_Tantalum_SMD:CP_EIA-3216-18_Kemet-A", (220, 112),
         {"1": "+3V3", "2": "GND"},
         fields={"Manufacturer": "KEMET", "MPN": "T491A106K016AT",
                 "Description": f"Capacitor 10 uF 16 V tantalum, case A 3216-18 (ADXL343 VS: {ADXL343_DS}, Power Supply "
                                "Decoupling p. 26, 10 uF tantalum with 0.1 uF ceramic; Table 1 test condition CS = 10 uF tantalum)"}),
    cap("C2", "100n", "+3V3", "GND", (232, 112),
        f"Capacitor 100 nF 16 V X7R 0603 (ADXL343 VS, the 0.1 uF ceramic beside C1: {ADXL343_DS}, p. 26)"),
    cap("C3", "100n", "+3V3", "GND", (244, 112),
        f"Capacitor 100 nF 16 V X7R 0603 (ADXL343 VDD I/O, CI/O = 0.1 uF ceramic: {ADXL343_DS}, p. 26)"),
    strap("JP3", "0x53", "ACC_SDO", (170, 155),
          f"ADXL343 ALT ADDRESS: 1-2 (as delivered) GND, 0x53; cut and bridge 2-3 (VDD I/O) for 0x1D ({ADXL343_DS}, p. 16)"),
    link("JP5", "ACC_INT1", "D5", (215, 140), "ADXL343 INT1 to Feather D5 (open as delivered: bridge to connect)"),
    link("JP6", "ACC_INT2", "D6", (215, 155), "ADXL343 INT2 to Feather D6 (open as delivered: bridge to connect)"),

    # ---- ADT7410 temperature sensor, I2C 0x48-0x4B ---------------------------------------------------
    Part("U2", "EoS_Sensors:ADT7410", "ADT7410", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", (170, 235),
         {"1": "I2C_SCL", "2": "I2C_SDA", "3": "TMP_A0", "4": "TMP_A1", "5": "TMP_INT", "6": "TMP_CT",
          "7": "GND", "8": "+3V3"},
         fields={"Manufacturer": "Analog Devices", "MPN": "ADT7410TRZ",
                 "Description": "16-bit digital temperature sensor, +-0.5 C, I2C 0x48 (A1 A0 = 00) to 0x4B"}),
    cap("C4", "100n", "+3V3", "GND", (210, 232),
        f"Capacitor 100 nF 16 V X7R 0603 (ADT7410 VDD, 0.1 uF ceramic at the pin: {ADT7410_DS}, Table 4 and p. 23)"),
    res("R3", "10k", "TMP_INT", "+3V3", (225, 232), f"Resistor 10 kohm 1% 0603 (ADT7410 INT pull-up to VDD: {ADT7410_DS}, p. 21)"),
    res("R4", "10k", "TMP_CT", "+3V3", (240, 232), f"Resistor 10 kohm 1% 0603 (ADT7410 CT pull-up to VDD: {ADT7410_DS}, p. 21)"),
    strap("JP2", "A0", "TMP_A0", (150, 275), f"ADT7410 A0: 1-2 (as delivered) GND; 2-3 for VDD (+1 on the address: {ADT7410_DS}, Table 20)"),
    strap("JP4", "A1", "TMP_A1", (185, 275), f"ADT7410 A1: 1-2 (as delivered) GND; 2-3 for VDD (+2 on the address: {ADT7410_DS}, Table 20)"),
    link("JP7", "TMP_INT", "D10", (215, 255), "ADT7410 INT to Feather D10 (open as delivered: bridge to connect)"),
    link("JP8", "TMP_CT", "D11", (215, 270), "ADT7410 CT to Feather D11 (open as delivered: bridge to connect)"),

    # ---- I2C pull-ups, removable ------------------------------------------------------------------------
    res("R1", "10k", "I2C_PU", "I2C_SDA", (300, 115),
        f"Resistor 10 kohm 1% 0603 (SDA pull-up: {ADT7410_DS}, p. 17, 10 kohm; checked against NXP UM10204 Rev. 7.0 section 7.1)"),
    res("R2", "10k", "I2C_PU", "I2C_SCL", (315, 115),
        f"Resistor 10 kohm 1% 0603 (SCL pull-up: {ADT7410_DS}, p. 17, 10 kohm; checked against NXP UM10204 Rev. 7.0 section 7.1)"),
    Part("JP1", "Jumper:SolderJumper_2_Bridged", "PU", JUMPER2_BRIDGED, (307, 140), {"A": "+3V3", "B": "I2C_PU"},
         fields={"Description": "I2C pull-ups R1 and R2 to 3.3 V: bridged as delivered; cut when the bus already has pull-ups"}),
]
# ---- Bench test pads (BENCH-READY C1): 3V3 and two GND, at the spots the bench-ready audit (g1, 24 Oct
# 2026) found free; the Feather's 3V and GND header pins (J1.2, J1.4) reach the same nets
PARTS += [
    bench_pad("TP1", "+3V3", "3V3", (45.07, 11.1), (150, 395)),
    bench_pad("TP2", "GND", "GND", (24.0, 18.0), (165, 395)),
    bench_pad("TP3", "GND", "GND", (38.5, 7.65), (180, 395)),
]
for i, _ in enumerate(HOLES):
    PARTS.append(Part(f"H{i + 1}", "Mechanical:MountingHole", "2.5mm", "MountingHole:MountingHole_2.5mm",
                      (60 + 20 * i, 360), {},
                      fields={"Description": "Mounting hole 2.5 mm, unplated (Feather Specification: 0.1 in holes at each corner)"}))

# Board placement: (x, y, rotation) in mm, origin top-left, USB end of the Feather on the left.
# The headers go on the back, placed by pin 1 (the footprint's origin); on the back, 270 degrees
# runs the pins in +x. ADT7410 on the left with its address jumpers; ADXL343 on the right, its
# decoupling beside its supply pins; the I2C pull-ups by the SCL/SDA end of the 12-pin strip.
PLACEMENT = {
    "J1": (HEADER_16_PIN1[0], HEADER_16_PIN1[1], 270), "J2": (HEADER_12_PIN1[0], HEADER_12_PIN1[1], 270),
    **{f"H{i + 1}": (x, y, 0) for i, (x, y) in enumerate(HOLES)},
    # ADT7410: C4 beside VDD and GND (pins 8, 7), the INT/CT pull-ups beside pins 5 and 6
    "U2": (16.0, 11.0, 0), "C4": (21.3, 9.73, 270), "R4": (24.4, 11.4, 0), "R3": (24.4, 13.6, 0),
    "JP2": (9.0, 11.6, 90), "JP4": (13.5, 16.6, 180),
    "JP8": (27.6, 5.6, 90), "JP7": (31.2, 5.6, 90),
    # ADXL343: C3 beside VDD I/O (pin 1), C2 and C1 beside VS (pin 6), JP3 beside SDO (pin 12)
    "U1": (37.5, 11.4, 0), "C3": (33.7, 9.2, 270), "C2": (33.7, 13.2, 90), "C1": (37.0, 17.0, 0),
    "JP3": (41.8, 10.0, 90), "JP6": (42.0, 15.2, 0), "JP5": (42.0, 18.5, 0),
    # I2C pull-ups and their jumper, below the SCL/SDA pins
    "R1": (46.6, 8.4, 90), "R2": (49.0, 8.4, 90), "JP1": (47.8, 12.8, 90),
    # bench test pads: 3V3 by the pull-ups, GND by the 16-pin strip and by the ADXL343
    "TP1": (45.07, 11.1, 0), "TP2": (24.0, 18.0, 0), "TP3": (38.5, 7.65, 0),
}
_unplaced = sorted({p.ref for p in PARTS} - set(PLACEMENT))
assert not _unplaced, f"parts without a board position: {_unplaced}"
for _p in PARTS:
    _p.pcb = PLACEMENT[_p.ref]

TEXTS = [
    # front: what each jumper does
    {"text": "EoS Motion Wing", "x": 8.4, "y": 5.6, "size": 0.8},
    {"text": "A0", "x": 9.0, "y": 8.5, "size": 0.8}, {"text": "A1", "x": 10.0, "y": 16.6, "size": 0.8},
    {"text": "ADR", "x": 41.8, "y": 6.9, "size": 0.8}, {"text": "PU", "x": 45.3, "y": 12.8, "size": 0.8},
    {"text": "D11", "x": 27.6, "y": 8.0, "size": 0.8}, {"text": "D10", "x": 31.2, "y": 8.0, "size": 0.8},
    {"text": "D6", "x": 45.0, "y": 15.2, "size": 0.8}, {"text": "D5", "x": 45.0, "y": 18.5, "size": 0.8},
    # back: designer and rights
    {"text": "EoS Motion Wing  rev A", "x": 25.4, "y": 9.5, "size": 1.0, "layer": "B_SilkS", "bold": True, "mirror": True},
    {"text": "(c) 2026 Kartikeydheer Srivastava", "x": 25.4, "y": 11.5, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    {"text": "All rights reserved", "x": 25.4, "y": 12.9, "size": 0.8, "layer": "B_SilkS", "mirror": True},
]

BOARD = Board(
    name="eos-motion-wing",
    title="EoS Motion Wing",
    revision="A",
    date="2026-10-12",
    company=OWNER,
    licence=LICENCE,
    contact=CONTACT,
    licence_terms=LICENCE_TERMS,
    credits=["FeatherWing outline, corner holes and header positions and pin order: facts from Adafruit's "
             "Feather Specification (learn.adafruit.com/adafruit-feather/feather-specification), used as dimensions only"],
    width=W,
    height=H,
    corner_radius=2.54,
    thickness=1.6,
    layers=2,
    parts=PARTS,
    power_nets={"GND": "power:GND", "+3V3": "power:+3V3"},
    flagged_nets=["GND", "+3V3"],
    headings=[((35, 95), "Feather headers (male, on the back)"), ((150, 95), "ADXL343 (I2C 0x53 / 0x1D)"),
              ((212, 97), "ADXL343 decoupling"), ((150, 145), "ADXL343 address"),
              ((200, 130), "Interrupts to the Feather (open jumpers)"), ((150, 210), "ADT7410 (I2C 0x48-0x4B)"),
              ((205, 212), "ADT7410 decoupling, INT/CT pull-ups"), ((140, 262), "ADT7410 address"),
              ((285, 95), "I2C pull-ups (cut JP1 to remove)"), ((40, 345), "Mounting holes"), ((35, 300), "Power nets")],
    power_block=(40.64, 315.0),
    notes=[((260, 320), "EoS Motion Wing, rev A. Designed by Kartikeydheer Srivastava.\n"
                       "Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved; see LICENSE.txt.\n"
                       "Outline, holes and headers from Adafruit's Feather Specification (dimensions only).\n"
                       "Values: ADI ADXL343 data sheet Rev. 0, ADI ADT7410 data sheet Rev. C, NXP UM10204 Rev. 7.0.\n"
                       "As delivered: pull-ups on (JP1), ADXL343 at 0x53 (JP3), ADT7410 at 0x48 (JP2, JP4),\n"
                       "interrupt jumpers JP5-JP8 open.")],
    netclasses={"Power": {"track": 0.25, "clearance": 0.15}},   # 3.3 V: narrow enough to enter the 0.8 mm-pitch LGA pads
    net_to_class={"+3V3": "Power"},
    # Bench data (BENCH-READY C): from the bench-ready audit g1 (24 Oct 2026), section 7
    rails=[
        Rail("+3V3", "the Feather's 3V pin (J1.2)", "3.3 V",
             "3.25-3.35 V: a bench supply set to 3.30 V (the wing has no regulator, so it reads its supply), or the "
             "host Feather's regulator, e.g. EoS Feather RP2040's AP2112K-3.3, 3.3 V +-1.5 % (Diodes DS39724 "
             "Rev. 2-2, AP2112-3.3 Electrical Characteristics, page 8)",
             ["TP1", "J1.2"], "> 100 kohm (no resistor to GND; the reading climbs while C1, 10 uF, charges)",
             link_note="No regulator on the wing, so no link: measure its current in series with the 3V pin, J1.2."),
        Rail("GND", "the Feather's GND pin (J1.4)", "0 V", "-", ["TP2", "TP3", "J1.4"], "-"),
    ],
    bringup=BringUp(
        supply="3.3 V on J1 pin 2 (3V) and pin 4 (GND), or the wing plugged onto a Feather",
        current_limit_ma=20,
        idle_current="about 0.25 mA",
        idle_source="ADT7410 converting from power-up, 210 uA typical and 250 uA maximum at 3.3 V (ADT7410 data "
                    "sheet Rev. C, Table 1, page 3, supply current); ADXL343 in standby from power-up; the sum is an "
                    "estimate",
        clock="N/A: the wing has no clock of its own; the ADXL343 and ADT7410 run on their internal oscillators.",
        programming="N/A: nothing on the wing is programmed; a Feather sets up both sensors over I2C.",
        tests=[
            BringUpTest("I2C", "Scan the bus from a Feather (CircuitPython or Arduino)", "finds 0x48 and 0x53 (jumpers as delivered)"),
            BringUpTest("ADXL343", "Read DEVID (register 0x00)", "0xE5"),
            BringUpTest("ADXL343", "Lay the wing flat, components up", "Z about +1 g, X and Y about 0 g"),
            BringUpTest("ADT7410", "Compare with a reference thermometer at room temperature", "within +-0.5 C (ADT7410 accuracy)"),
            BringUpTest("Address jumpers", "Cut JP3 1-2, bridge 2-3, power again", "ADXL343 answers at 0x1D"),
            BringUpTest("Interrupts", "Bridge JP5; enable the ADXL343 activity interrupt and tap the wing", "Feather D5 sees INT1"),
        ],
    ),
    temperature_range=(-40, 85, "U1", "ADXL343, rated -40 to +85 C; every other part is rated wider (ADT7410 -55 to "
                                     "+150 C, T491A -55 to +125 C, Wurth headers -40 to +105 C; parts.json, 24 Oct 2026)"),
    pin_labels={
        "J1": {"1": "RST", "2": "3V", "3": "AREF", "4": "GND", "5": "A0", "6": "A1", "7": "A2", "8": "A3", "9": "A4",
               "10": "A5", "11": "SCK", "12": "MO", "13": "MI", "14": "RX", "15": "TX"},
        "J2": {"1": "BAT", "2": "EN", "3": "USB", "4": "D13", "5": "D12", "6": "D11", "7": "D10", "8": "D9", "9": "D6",
               "10": "D5", "11": "SCL", "12": "SDA"},
    },
)
