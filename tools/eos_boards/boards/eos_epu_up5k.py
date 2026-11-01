"""EoS EPU Board: a Lattice iCE40UP5K board that runs the EPU RISC-V SoC, designed by Kartikeydheer Srivastava.

Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved: this design file is not under
the repository's MIT licence; see boards/eos/eos-epu-up5k/LICENSE.txt.

A 75 x 55 mm four-layer board: an iCE40UP5K-SG48 FPGA, a 16 MB SPI NOR configuration flash, a
12 MHz oscillator, an FTDI FT2232H USB bridge on a USB-C port (channel A programs the flash the way
Project IceStorm's iceprog and openFPGALoader expect, channel B is EPU's UART), a 5 V to 3.3 V buck
converter, a 1.2 V LDO and a load switch that bring the FPGA's supplies up in the order Lattice
asks for, two Digilent Pmod host ports, a 10-pin JTAG header for EPU's planned debug port, buttons,
LEDs and test points. It is EmbeddedOS's own board for EPU, in place of a bought iCE40 board; no
design file of any other iCE40 board, of Lattice's evaluation boards or of an FTDI module was
opened.

Where every value comes from (the documents named below, with their revisions):

* FPGA: Lattice iCE40 UltraPlus Family Data Sheet FPGA-DS-02008-2.4 (February 2025, "DS"), the
  iCE40UP5K pinout file Revision 1.1 (pin numbers), iCE40 Hardware Checklist FPGA-TN-02006-2.4
  ("HC"), iCE40 Programming and Configuration FPGA-TN-02001-3.5 ("TN1"), iCE40 sysCLOCK PLL
  Design and User Guide FPGA-TN-02052-1.4 ("PLL"), iCE40 LED Driver User Guide FPGA-TN-02021-1.5,
  Package Diagrams FPGA-DS-02053-8.8 (SG48: exposed pad 5.20-5.50 mm, nominal 5.35; KiCad's
  5.3 mm land).
  - Supplies: VCC 1.2 V (1.14-1.26 V), VCCIO_0/SPI_VCCIO1/VCCIO_2 3.3 V, VPP_2V5 on 3.3 V
    (2.30-3.46 V for master SPI configuration; DS Table 4.2). NVCM programming (VPP at most 3.0 V)
    is not possible on this board, and it is not needed: the FPGA configures from the flash.
  - Power-up order (DS 4.5, HC 2.3): VCC and VCCPLL first, then SPI_VCCIO1, then VPP_2V5, each
    after the one before has reached 0.5 V. Here the buck makes 3.3 V (+3V3_BUCK) for the 1.2 V LDO
    only; the 1.2 V rail (+1V2) drives the ON pin of a load switch that makes the board's 3.3 V
    rail (+3V3) from +3V3_BUCK. Everything on 3.3 V (all FPGA banks, VPP, the flash, the FT2232H,
    the oscillator) therefore comes up after VCC. Ramp rates 0.6-10 V/ms (DS Table 4.3): +1V2
    1.2 V in the LDO's 550 us start-up (TI SBVS320D, tSTR), about 2.2 V/ms; +3V3 at 1.9 V/ms
    (TPS22917 SRON 1900 (mV/us)pF / 1000 pF at VIN 3.6 V).
  - Decoupling (HC Table 2.2): 100 nF at each supply pin, 4.7 uF per supply group. VCCPLL (HC 2.2,
    PLL 5.2 Figure 5.4): 100 ohm from VCC, 4.7 uF (HC Table 2.2's value) and 100 nF at the pin;
    required "even if the PLL is not utilized". The SG48 has no GNDPLL pin (its PLL ground is the paddle).
  - CRESET_B: "a pure input with no internal pullup": 10 kohm to 3.3 V (TN1 5.1, HC Table 3.1). DS 4.6
    asks for CRESET_B low until every supply is valid, and the FPGA's own power-on reset trips far below
    the operating minimums (DS Table 4.4), so two TI TPS3808 supervisors (SBVS050N) hold it low:
    U11 (TPS3808G12, 1.12 V) watches +1V2 and drives U10's MR; U10 (TPS3808G33, 3.07 V) watches +3V3
    and drives CRESET_B, open drain, as TI's Figure 7-3. Both run from +3V3_BUCK, which is up before
    either monitored rail. CRESET_B is released 12-28 ms (CT open) after both rails are valid, and pulled
    low again within 20 us if either sags below its threshold (a brown-out). Thresholds, worst case over
    -40..85 C (+-1.25 %, hysteresis 1-2.5 %): +1V2 trips at 1.106-1.134 V (VCC minimum 1.14 V, DS
    Table 4.2) and releases by 1.162 V, under the LDO's 1.188 V minimum (1 %); +3V3 trips at
    3.03-3.11 V and releases by 3.19 V, under the rail's 3.22 V minimum (buck VFB 2 %, less the load
    switch's drop). The CRESET button is U10's MR, so one press gives one clean pulse (debounced by the
    20 ms delay); FT2232H ADBUS7 pulls CRESET_B directly through 1 kohm. With no capacitor on the node
    (about 20 pF), it falls in tens of nanoseconds, so openFPGALoader's flash commands, which follow
    the reset with no wait, reach a flash the FPGA has already let go.
  - CDONE: open drain with a weak pull-up; external pull-up at most 1 / (2 x f_config x C_CDONE)
    (TN1 5.1, HC Table 3.1): with the default master-SPI clock (at most 17 MHz, DS Table 4.24) and
    about 10 pF on the node, at most 2.9 kohm, so 2.2 kohm. The DONE LED's MOSFET gate hangs off
    it through 10 kohm, and the FT2232H reads it through 1 kohm, so neither loads the node.
  - SPI_SS_B 10 kohm pull-up (master mode) and SPI_SCK 10 kohm pull-up (HC Table 3.1).
  - Clock: 12 MHz on pin 35, IOT_46b_G0: a global input, and the PLL's input pin on this package
    (PLL 5.1.1 names pin 35 as the GPLL pin).
  - The flash may be left in deep power-down (TN1 9.4, and iceprog without -k): EPU's firmware must send
    0xAB (release power-down) before it reads the flash (EPU's flash boot is not yet implemented).
* Flash: Winbond W25Q128JVSIQ, 16 MB, SOIC-8 208 mil (W25Q128JV data sheet Revision F). It
  supports the 0x0B Fast Read and 0xAB/0xB9 commands the iCE40 uses (TN1 9.2). "IQ" parts have
  QE = 1 (7.1.4), so pins 3 and 7 are IO2/IO3: 10 kohm pull-ups hold them high in single-SPI use.
* FT2232H: FTDI DS_FT2232H Version 2.6 (FT_000061), LQFP-64. Bus-powered as its Figure 6.1:
  VPHY and VPLL each through a ferrite with 4.7 uF and 100 nF (Table 3.2 recommends an LC filter),
  3.3 uF minimum on VREGOUT (4.7 uF fitted), 100 nF on each VCORE and VCCIO pin, 12 kohm 1 % on
  REF, RESET# through 1 kohm to 3.3 V, TEST to ground, 93LC56B EEPROM with 10 kohm pull-ups on CS,
  CLK and DO and 2.2 kohm from DO to EEDATA (Table 3.4, Figure 6.1). The FT2232H is a fixed-function
  USB bridge, not a vendor debug probe.
  - Clock: 6.3 asks 12 MHz +-30 ppm (Table 6.1) and allows "a 12 MHz Oscillator ... the output of the
    oscillator would drive OSCI, and OSCO should be left unconnected". ECS-2520MVLC-120-CN-TR: +-25 ppm
    covering tolerance, temperature, supply, load and reflow, plus +-3 ppm first-year aging: +-28 ppm,
    -40 to +85 C, with no load-capacitor pulling term. A crystal's budget also needs its pullability,
    which the stocked +-10/+-10 ppm 12 MHz crystal (CTS 403C11A12M00000) does not publish.
  - EEPROM fitted (Microchip 93LC56B, DS21794G, 16-bit, SOT-23): blank, the FT2232H uses its
    default descriptors (section 7: VID 0403, PID 6010, both channels UART), which iceprog and
    openFPGALoader find without changes; programmed later, it gives each board a serial number.
  - Channel A pin roles from Project IceStorm's iceprog source (iceprog/mpsse.c and iceprog.c,
    commit e86829e, 2025-07-05): ADBUS0 SCK, ADBUS1 MOSI (to the flash's DI), ADBUS2 MISO (from the
    flash's DO), ADBUS4 CS, ADBUS6 CDONE (input), ADBUS7 CRESET; interface A, 6 MHz. openFPGALoader's
    "ice40_generic" board (src/board.hpp, commit 9f1b753) uses the same pins.
  - Each channel-A line meets the FPGA/flash nets through 1 kohm: with no MPSSE program running,
    channel A sits in its default UART mode (section 4.13) and drives TXD (ADBUS0), RTS# (ADBUS2)
    and DTR# (ADBUS4) (Table 3.x pin roles), the same nets the FPGA and the flash drive. 1 kohm keeps
    any such clash at 3.3 mA, under the FT2232H's 16 mA output rating (Table 5.1); 1 kohm x about
    10 pF is 10 ns against iceprog's 6 MHz clock.
  - Channel B: BDBUS0 (TXD) to EPU's uart_rx, BDBUS1 (RXD) from uart_tx.
* Power (USB VBUS, 5 V): HRO TYPE-C-31-M-12 as a sink, 5.1 kohm Rd on CC1 and CC2 (USB Type-C
  specification). TI TPD2EUSB30 (SLVSAC2G: 0.7 pF, IEC 61000-4-2 level 4, diodes to ground only) on
  D+ and D-, fit for the FT2232H's high-speed lines; Littelfuse SP0503BAHTG on CC1, CC2 and VBUS
  (diodes to ground only). Littelfuse 0805L075 polyfuse (0.75 A hold at 20 C, 0.57 A at 50 C,
  1.5 A trip, R1max 0.35 ohm).
  - Buck: TI TLV62569DBV (SLVSDG1C): 2.2 uH (Coilcraft XAL4020-222MEC, the part in TI's Table 3) and
    10 uF out (Table 4's recommended pair), 4.7 uF in (8.2.2.5). Laid out as TI's Figure 20 (10.1):
    C1 beside VIN with its ground pad joined to the GND pin under the body, the switch node a short
    top-layer stub to L1 with no via, the feedback divider on the side away from it. VOUT = 0.6 V x (1 + R1/R2) with
    R1 45.3 kohm and R2 10 kohm 0.1 %: 3.318 V; 68 pF feed-forward (TI recommends 6.8 pF with
    R2 = 100 kohm; the same R1 x C3 time constant with R1 ten times smaller).
  - 1.2 V: TI TLV75512PDBV (SBVS320D), 1 % accuracy, 1 uF in and out (at least 1 uF, 0.47 uF
    effective). A 0 ohm link (BENCH-READY C2) between it and the FPGA's VCC lets the core be
    checked unloaded and its current measured; the load switch's ON pin is on the FPGA side, so
    3.3 V stays off while the link is out.
  - Load switch: TI TPS22917DBV (SLVSDW8B): ON high at 1.0 V or more (VIH), CT 1000 pF, QOD to
    VOUT. It turns on about 2 ms after ON rises (tON 3.8 us/pF less tR 1.6 us/pF).
  - The 3.3 V pins on the Pmod, EXT and JTAG headers are outputs. The load switch blocks reverse current
    (SLVSDW8B 1), so 3.3 V fed into one would reach the FT2232H and the FPGA's banks but not the buck or
    the 1.2 V LDO: never power the board through them.
* Clock: ECS-2520MV-120-BN-TR, 12 MHz, +-50 ppm, -40 to +85 C, 1.6-3.6 V CMOS (ECS-2520MV data
  sheet, Rev. 2026); its tri-state pin to 3.3 V (active).
* Pmod: Digilent Pmod Interface Specification (revised October 28, 2020): 12-pin right-angle
  female host ports at the board edge, 0.9 in apart; pins 1-6 the row away from the edge; 3.3 V
  and up to about 100 mA per module (section 3); 200 ohm in series with each signal (section 2:
  "generally have ESD protection diodes and 200-ohm series resistors"): a TI TPD4E05U06 ESD array
  (SLVSBO7O: 0.5 pF, VRWM 5.5 V, IEC 61000-4-2 +-12 kV contact) on the socket side of each pair of rows,
  and one on the EXT header. Port A is Type 6A (I2C
  on pins 3-4, I2C pull-ups on the host, section 2), port B Type 2A (SPI on pins 1-4, INT pin 7,
  RESET pin 8, CS2/CS3 pins 9-10).
* JTAG: the Arm 10-pin 1.27 mm debug connector layout (VTref 1, TMS 2, GND 3, TCK 4, GND 5, TDO 6,
  key 7, TDI 8, GNDDetect 9, nRESET 10, KiCad's Conn_ARM_JTAG_SWD_10), Samtec FTSH-105-01-L-DV-K on
  Samtec's land pattern (EoS_Packages). nRESET is EPU's reset line. Its lines go straight to the FPGA,
  with no series resistor or ESD array: a keyed header for a debug probe's ribbon cable, not for hand-wired
  modules. The iCE40's own ESD rating is not published (DS 4.8: "Please contact Lattice").

EPU's ports (epu/fpga/ice40/epu_ice40_top.v) and the FPGA pins they use are in PIN_TABLE below;
the README's pin table and EPU's pin file are written from it.
"""

from __future__ import annotations

from ..design import NC, Board, Part, USB_C_EDGE
from .owner import CONTACT, LICENCE, LICENCE_TERMS, OWNER

R0402 = "Resistor_SMD:R_0402_1005Metric"
R0603 = "Resistor_SMD:R_0603_1608Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
LED0603 = "LED_SMD:LED_0603_1608Metric"
KMR2 = "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2"
RPACK = "Resistor_SMD:R_Array_Convex_4x0603"
TP = "TestPoint:TestPoint_Pad_D1.0mm"
PMOD_FP = "Connector_PinSocket_2.54mm:PinSocket_2x06_P2.54mm_Horizontal"

DS = "Lattice FPGA-DS-02008-2.4"
HC = "Lattice FPGA-TN-02006-2.4"
TN1 = "Lattice FPGA-TN-02001-3.5"
PLL = "Lattice FPGA-TN-02052-1.4"
FT = "FTDI DS_FT2232H v2.6"
PMOD = "Digilent Pmod Interface Specification (2020-10-28)"

# Part numbers: passives as the EoS boards' parts survey of 24 October 2026 (Murata, Samsung, Yageo, Panasonic; checked there).
C100N = ("Murata", "GRM155R71C104KA88D")       # 100 nF 16 V X7R 0402
C1U = ("Samsung Electro-Mechanics", "CL05A105KA5NQNC")   # 1 uF 25 V X5R 0402
C4U7 = ("Murata", "GRM188R61C475KE11D")        # 4.7 uF 16 V X5R 0603
C4U7_0805 = ("Murata", "GRM21BR71A475KE51L")   # 4.7 uF 10 V X7R 0805; Murata's named replacement for KA73L (to be discontinued)
C10U_0805 = ("Murata", "GRM21BR71A106KA73L")   # 10 uF 10 V X7R 0805, Murata DC-bias curve: 7.20 uF at 3.3 V, 25 C
C68P = ("Murata", "GRM1555C1H680JA01D")        # 68 pF 50 V C0G 0402
C1N = ("Murata", "GRM1555C1H102JA01D")         # 1 nF 50 V C0G 0402
YAGEO = {"5.1k": "RC0402FR-075K1L", "12k": "RC0402FR-0712KL", "1k": "RC0402FR-071KL", "2.2k": "RC0402FR-072K2L",
         "10k": "RC0402FR-0710KL", "100": "RC0402FR-07100RL", "680": "RC0402FR-07680RL", "750": "RC0402FR-07750RL",
         "4.7k": "RC0402FR-074K7L"}


def res(ref, value, a, b, sch, desc, rot=0):
    return Part(ref, "Device:R_Small", value, R0402, sch, {"1": a, "2": b},
                fields={"Manufacturer": "Yageo", "MPN": YAGEO[value], "Description": f"Resistor {value} 1% 0402 ({desc})"},
                sch_rotation=rot)


def cap(ref, value, a, b, sch, desc, mpn=C100N, fp=C0402, rot=0):
    return Part(ref, "Device:C_Small", value, fp, sch, {"1": a, "2": b},
                fields={"Manufacturer": mpn[0], "MPN": mpn[1], "Description": desc}, sch_rotation=rot)


def led(ref, colour, anode, cathode, sch, desc):
    mpn, ds = {"green": ("APTD1608LCGCK", "DSAO7432, VF 1.9 V typ at 2 mA"),
               "red": ("APTD1608LSURCK", "DSAO7433, VF 1.75 V typ at 2 mA"),
               "yellow": ("APTD1608LSYCK", "DSAO7434, VF 1.85 V typ at 2 mA")}[colour]
    return Part(ref, "Device:LED_Small", colour, LED0603, sch, {"A": anode, "K": cathode},
                fields={"Manufacturer": "Kingbright", "MPN": mpn, "Description": f"LED {colour} 0603 ({ds}): {desc}"})


def button(ref, value, net, sch, what):
    return Part(ref, "Switch:SW_Push", value, KMR2, sch, {"1": net, "2": "GND"},
                fields={"Manufacturer": "C&K", "MPN": "KMR221G LFS",
                        "Description": f"Tactile switch 4.2 x 2.8 mm, -40 to +85 C (C&K KMR2): {what}"})


def rpack(ref, nets, sch, what):
    """Bourns CAY16-201J4LF: four isolated 200 ohm resistors, convex, 3.2 x 1.6 mm, 0.8 mm pitch (Bourns
    CAT16/CAY16 data sheet), on KiCad's 4 x 0603 convex land. ``nets``: four (inner, outer) pairs."""
    pins = {}
    for k, (inner, outer) in enumerate(nets):
        pins[str(k + 1)] = inner
        pins[str(8 - k)] = outer
    return Part(ref, "Device:R_Pack04", "4x200", RPACK, sch, pins,
                fields={"Manufacturer": "Bourns", "MPN": "CAY16-201J4LF",
                        "Description": f"Resistor array 4 x 200 ohm 5% 1506 convex: series resistors, {what} ({PMOD} section 2)"})


def esd4(ref, nets, sch, what):
    """TI TPD4E05U06DQAR: four ESD diodes to ground, 0.5 pF, VRWM 5.5 V, IEC 61000-4-2 +-12 kV contact (SLVSBO7O).
    ``nets``: the four protected nets for pads 1, 2, 4 and 5. The NC pad opposite each (10, 9, 7, 6) carries the same
    net: TI's straight-through routing ("Used for optional straight-through routing", SLVSBO7O Table 4-2), so each
    line runs from the series resistor across the array to the connector."""
    a, b, c, d = nets
    return Part(ref, "Power_Protection:TPD4E05U06DQA", "TPD4E05U06", "Package_SON:USON-10_2.5x1.0mm_P0.5mm", sch,
                {"1": a, "10": a, "2": b, "9": b, "4": c, "7": c, "5": d, "6": d, "3": "GND", "8": "GND"},
                fields={"Manufacturer": "Texas Instruments", "MPN": "TPD4E05U06DQAR",
                        "Description": f"ESD array, 4 lines, 0.5 pF, VRWM 5.5 V, IEC 61000-4-2 +-12 kV contact, diodes to GND only, "
                                       f"-40 to +125 C (TI SLVSBO7O): {what}, on the connector side of the 200 ohm ({PMOD} section 2)"})


def tp(ref, net, sch, what):
    return Part(ref, "Connector:TestPoint", net, TP, sch, {"1": net},
                fields={"Description": f"Test pad 1.0 mm, {what} (BENCH-READY C1)"})


# ---- EPU's ports and the FPGA pins they use (the pin table; README and .pcf are written from it) --------------
# (package pin, Lattice pin name, net, EPU signal or reserved use, where it goes)
PIN_TABLE = [
    (35, "IOT_46b_G0", "CLK12", "clk", "12 MHz oscillator X1 (global input, GPLL pin)"),
    (9, "IOB_16a", "RST_N", "rst_btn_n", "RESET button SW2, JTAG J2 pin 10; 10 kohm pull-up, 100 nF"),
    (10, "IOB_18a", "BOOT_SEL", "boot_sel", "BOOT jumper JP1 (open = 1, fitted = 0); 10 kohm pull-up"),
    (6, "IOB_13b", "UART_RX", "uart_rx", "FT2232H BDBUS0 (channel B TXD)"),
    (4, "IOB_8a", "UART_TX", "uart_tx", "FT2232H BDBUS1 (channel B RXD)"),
    (43, "IOT_49a", "LED0", "gpio[0]", "LED D3 (green), boot ROM heartbeat"),
    (42, "IOT_51a", "LED1", "gpio[1]", "LED D4 (green)"),
    (38, "IOT_50b", "LED2", "gpio[2]", "LED D5 (green)"),
    (37, "IOT_45a_G1", "LED3", "gpio[3]", "LED D6 (green)"),
    (11, "IOB_20a", "BTN0", "gpio[4]", "USER button SW3; 10 kohm pull-up"),
    (21, "IOB_23b", "PMODB_7", "gpio[5]", "Pmod B pin 7 (INT) via 200 ohm"),
    (20, "IOB_25b_G3", "PMODB_8", "gpio[6]", "Pmod B pin 8 (RESET) via 200 ohm"),
    (36, "IOT_48b", "PMODA_1", "gpio[7]", "Pmod A pin 1 (INT) via 200 ohm"),
    (15, "IOB_34a_SPI_SCK", "FLASH_SCK", "spi_sck", "flash CLK; Pmod B pin 4 via 200 ohm; FT2232H ADBUS0 via 1 kohm"),
    (14, "IOB_32a_SPI_SO", "FLASH_MOSI", "spi_mosi", "flash DI; Pmod B pin 2 via 200 ohm; FT2232H ADBUS1 via 1 kohm"),
    (17, "IOB_33b_SPI_SI", "FLASH_MISO", "spi_miso", "flash DO; Pmod B pin 3 via 200 ohm; FT2232H ADBUS2 via 1 kohm"),
    (16, "IOB_35b_SPI_SS", "FLASH_CS", "spi_cs_n[0]", "flash /CS; FT2232H ADBUS4 via 1 kohm; 10 kohm pull-up"),
    (23, "IOT_37a", "PMODB_1", "spi_cs_n[1]", "Pmod B pin 1 (CS) via 200 ohm; 10 kohm pull-up"),
    (44, "IOB_3b_G6", "JTAG_TCK", "reserved: JTAG TCK", "JTAG J2 pin 4 (a global input)"),
    (45, "IOB_5b", "JTAG_TMS", "reserved: JTAG TMS", "JTAG J2 pin 2"),
    (46, "IOB_0a", "JTAG_TDI", "reserved: JTAG TDI", "JTAG J2 pin 8"),
    (47, "IOB_2a", "JTAG_TDO", "reserved: JTAG TDO", "JTAG J2 pin 6"),
    (28, "IOT_41a", "I2C_SCL", "reserved: I2C SCL", "Pmod A pin 3 via 200 ohm; 4.7 kohm pull-up"),
    (26, "IOT_39a", "I2C_SDA", "reserved: I2C SDA", "Pmod A pin 4 via 200 ohm; 4.7 kohm pull-up"),
    (32, "IOT_43a", "PMODA_2", "reserved: GPIO", "Pmod A pin 2 via 200 ohm"),
    (34, "IOT_44b", "PMODA_7", "reserved: GPIO", "Pmod A pin 7 via 200 ohm"),
    (31, "IOT_42b", "PMODA_8", "reserved: GPIO", "Pmod A pin 8 via 200 ohm"),
    (27, "IOT_38b", "PMODA_9", "reserved: GPIO", "Pmod A pin 9 via 200 ohm"),
    (25, "IOT_36b", "PMODA_10", "reserved: GPIO", "Pmod A pin 10 via 200 ohm"),
    (19, "IOB_29b", "PMODB_9", "reserved: GPIO (Pmod CS2)", "Pmod B pin 9 via 200 ohm"),
    (18, "IOB_31b", "PMODB_10", "reserved: GPIO (Pmod CS3)", "Pmod B pin 10 via 200 ohm"),
    (13, "IOB_24a", "BTN1", "reserved: GPIO", "USER2 button SW4; 10 kohm pull-up"),
    (48, "IOB_4a", "EXT0", "reserved: GPIO", "EXT header J5 pin 2 via 200 ohm"),
    (2, "IOB_6a", "EXT1", "reserved: GPIO", "EXT header J5 pin 3 via 200 ohm"),
    (3, "IOB_9b", "EXT2", "reserved: GPIO", "EXT header J5 pin 4 via 200 ohm"),
    (12, "IOB_22a", "EXT3", "reserved: GPIO", "EXT header J5 pin 5 via 200 ohm"),
    (39, "RGB0", "RGB0_K", "reserved: LED sink", "red LED D7 via 100 ohm (SB_RGBA_DRV or SB_IO_OD)"),
    (40, "RGB1", "RGB1_K", "reserved: LED sink", "green LED D8 via 100 ohm"),
    (41, "RGB2", "RGB2_K", "reserved: LED sink", "yellow LED D9 via 100 ohm"),
]
FPGA_IO = {str(pin): net for pin, _, net, _, _ in PIN_TABLE}

PARTS = [
    # ---- USB-C, ESD, CC, fuse -------------------------------------------------------------------------------
    Part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
         (30, 60), {"VBUS": "VBUS", "GND": "GND", "CC1": "CC1", "CC2": "CC2", "D+": "USB_DP", "D-": "USB_DM",
                    "SBU1": NC, "SBU2": NC, "SHIELD": "GND"},
         fields={"Manufacturer": "Korean Hroparts", "MPN": "TYPE-C-31-M-12",
                 "Description": "USB-C 2.0 receptacle, 16 pins, 5 V sink: power, FT2232H channel A (programming) and B (UART)"}),
    res("R1", "5.1k", "CC1", "GND", (60, 45), "CC1 Rd: a USB Type-C sink"),
    res("R2", "5.1k", "CC2", "GND", (72, 45), "CC2 Rd: a USB Type-C sink"),
    Part("U1", "Power_Protection:TPD2EUSB30", "TPD2EUSB30", "Package_TO_SOT_SMD:Texas_DRT-3", (95, 60),
         {"1": "USB_DP", "2": "USB_DM", "3": "GND"},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPD2EUSB30DRTR",
                 "Description": "ESD protection D+/D-: 0.7 pF, IEC 61000-4-2 level 4, diodes to GND only (TI SLVSAC2G)"}),
    Part("U2", "Power_Protection:SP0503BAHT", "SP0503BAHTG", "Package_TO_SOT_SMD:SOT-143", (95, 85),
         {"1": "GND", "2": "CC1", "3": "CC2", "4": "VBUS"},
         fields={"Manufacturer": "Littelfuse", "MPN": "SP0503BAHTG",
                 "Description": "ESD protection CC1, CC2, VBUS: three diodes to GND, none to VBUS (Littelfuse SP05xxBA)"}),
    Part("F1", "Device:Polyfuse_Small", "750mA", "Fuse:Fuse_0805_2012Metric", (60, 80), {"1": "VBUS", "2": "VBUS_F"},
         fields={"Manufacturer": "Littelfuse", "MPN": "0805L075WR",
                 "Description": "PTC fuse 0.75 A hold (0.57 A at 50 C), 1.50 A trip, 6 V, R1max 0.35 ohm, 0805 (Littelfuse 0805L, revised 10/29/21)"}),

    # ---- 5 V -> 3.3 V buck (TLV62569) ---------------------------------------------------------------------------
    Part("U3", "Regulator_Switching:TLV62569DBV", "TLV62569", "Package_TO_SOT_SMD:SOT-23-5", (140, 60),
         {"EN": "VBUS_F", "GND": "GND", "SW": "SW_3V3", "VIN": "VBUS_F", "FB": "FB_3V3"},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TLV62569DBVR",
                 "Description": "Buck converter 2 A, 1.5 MHz, 2.5-5.5 V in (TI SLVSDG1C): 5 V to 3.3 V"}),
    cap("C1", "4.7u", "VBUS_F", "GND", (120, 75), "Capacitor 4.7 uF 10 V X7R 0805 (buck input, at VIN and GND: TI SLVSDG1C 8.2.2.5, 10.1)", C4U7_0805, C0805),
    Part("L1", "Device:L_Small", "2.2u", "Inductor_SMD:L_Coilcraft_XAL4020-XXX", (165, 55), {"1": "SW_3V3", "2": "+3V3_BUCK"},
         fields={"Manufacturer": "Coilcraft", "MPN": "XAL4020-222MEC",
                 "Description": "Inductor 2.2 uH, DCR 38.7 mohm max, Isat 5.6 A, -40 to +125 C (Coilcraft 806-1, packaging code C; TI SLVSDG1C Table 3 L1)"}),
    # buck output: two 10 uF in parallel, so that at 3.3 V Murata's small-signal curve (0.01 Vrms, BENCH-READY B2)
    # keeps TI's 5 uF effective minimum down to -30 C: 2 x 4.53 uF = 9.06 uF (Table 4 note 2)
    cap("C2", "10u", "+3V3_BUCK", "GND", (185, 75), "Capacitor 10 uF 10 V X7R 0805 (buck output, with C43: TI SLVSDG1C Table 4, 2.2 uH, 10-47 uF; >= 5 uF effective: 2 x 4.53 uF at 3.3 V, -30 C, 0.01 Vrms)", C10U_0805, C0805),
    cap("C43", "10u", "+3V3_BUCK", "GND", (193, 68), "Capacitor 10 uF 10 V X7R 0805 (buck output, in parallel with C2)", C10U_0805, C0805),
    Part("R3", "Device:R_Small", "45.3k", R0402, (165, 85), {"1": "+3V3_BUCK", "2": "FB_3V3"},
         fields={"Manufacturer": "Panasonic", "MPN": "ERA-2AEB4532X",
                 "Description": "Resistor 45.3 kohm 0.1% 0402 (R1: VOUT = 0.6 V x (1 + 45.3/10) = 3.318 V, TI SLVSDG1C Eq. 2)"}),
    Part("R4", "Device:R_Small", "10k", R0402, (165, 100), {"1": "FB_3V3", "2": "GND"},
         fields={"Manufacturer": "Panasonic", "MPN": "ERA-2AEB103X",
                 "Description": "Resistor 10 kohm 0.1% 0402 (R2, at most 200 kohm: TI SLVSDG1C 8.2.2.2)"}),
    cap("C3", "68p", "+3V3_BUCK", "FB_3V3", (180, 92), "Capacitor 68 pF C0G 0402 (feed-forward across R1: TI's 6.8 pF for R2 = 100 kohm, same R1 x C3)", C68P),

    # ---- 1.2 V LDO, core link, 3.3 V load switch -------------------------------------------------------------------
    Part("U4", "Regulator_Linear:TLV75512PDBV", "TLV75512P", "Package_TO_SOT_SMD:SOT-23-5", (215, 60),
         {"IN": "+3V3_BUCK", "GND": "GND", "EN": "+3V3_BUCK", "OUT": "+1V2_LDO", "4": NC},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TLV75512PDBVR",
                 "Description": "LDO 1.2 V 500 mA, 1% (TI SBVS320D): FPGA core VCC and VCCPLL"}),
    cap("C4", "1u", "+3V3_BUCK", "GND", (200, 80), "Capacitor 1 uF 25 V X5R 0402 (LDO input, at least 1 uF: TI SBVS320D 5.3)", C1U),
    cap("C5", "1u", "+1V2_LDO", "GND", (232, 80), "Capacitor 1 uF 25 V X5R 0402 (LDO output, at least 1 uF: TI SBVS320D 5.3)", C1U),
    Part("R5", "Device:R_Small", "0", R0603, (250, 60), {"1": "+1V2_LDO", "2": "+1V2"},
         fields={"Manufacturer": "Yageo", "MPN": "RC0603JR-070RL",
                 "Description": "Rail link 0 ohm 0603 (BENCH-READY C2): remove to check +1V2_LDO unloaded or to measure the FPGA core current"}),
    Part("U5", "Power_Management:TPS22917DBV", "TPS22917", "Package_TO_SOT_SMD:SOT-23-6", (285, 60),
         {"VIN": "+3V3_BUCK", "GND": "GND", "ON": "+1V2", "CT": "CT_3V3", "QOD": "QOD_3V3", "VOUT": "+3V3"},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPS22917DBVR",
                 "Description": f"Load switch 2 A, 80 mohm, ON high at 1.0 V (TI SLVSDW8B): +3V3 only after the FPGA core is up ({DS} 4.5)"}),
    cap("C6", "1n", "CT_3V3", "GND", (285, 85), "Capacitor 1 nF C0G 50 V 0402 (CT: tR 1.6 ms, 1.9 V/ms at 3.3 V, TI SLVSDW8B 7.6; >= 7 V rating, 7.3)", C1N),
    # 4.7 uF, not 10 uF (no data sheet asks for it). With the load switch on, the buck's output also carries every
    # +3V3 capacitor and, through FB1/FB2, C8-C11: 55.5 uF nominal, above the 10-47 uF of TI SLVSDG1C 8.2.2.5;
    # 28-35 uF effective at 3.3 V (Murata 0.01 Vrms curves, -30 to +80 C). See the README's Parts section.
    cap("C7", "4.7u", "+3V3", "GND", (305, 85), "Capacitor 4.7 uF 16 V X5R 0603 (3.3 V rail bulk after the load switch)", C4U7, C0603),
    res("R42", "100", "QOD_3V3", "+3V3", (285, 105), "QOD to VOUT through 100 ohm (TI SLVSDW8B 7.6, tFALL row): discharges +3V3 when +1V2 falls, so a quick re-plug repeats the power-up order"),

    # ---- FT2232H ------------------------------------------------------------------------------------------------------
    Part("U6", "Interface_USB:FT2232HL", "FT2232HL", "Package_QFP:LQFP-64_10x10mm_P0.5mm", (110, 200),
         {"1": "GND", "5": "GND", "11": "GND", "15": "GND", "25": "GND", "35": "GND", "47": "GND", "51": "GND",
          "10": "GND", "2": "FT_XI", "3": NC, "4": "+3V3_PHY", "6": "FT_REF", "7": "USB_DM", "8": "USB_DP",
          "9": "+3V3_PLLF", "12": "+1V8", "37": "+1V8", "64": "+1V8", "13": "GND", "14": "FT_RST_N",
          "16": "FT_SCK", "17": "FT_MOSI", "18": "FT_MISO", "19": NC, "20": "+3V3", "21": "FT_CS", "22": NC,
          "23": "FT_CDONE", "24": "FT_CRESET", "26": NC, "27": NC, "28": NC, "29": NC, "30": NC, "31": "+3V3",
          "32": NC, "33": NC, "34": NC, "36": NC, "38": "UART_RX", "39": "UART_TX", "40": NC, "41": NC,
          "42": "+3V3", "43": NC, "44": NC, "45": NC, "46": NC, "48": NC, "49": "+1V8", "50": "+3V3",
          "52": NC, "53": NC, "54": NC, "55": NC, "56": "+3V3", "57": NC, "58": NC, "59": NC, "60": NC,
          "61": "EE_DATA", "62": "EE_CLK", "63": "EE_CS"},
         fields={"Manufacturer": "FTDI", "MPN": "FT2232HL-REEL",
                 "Description": f"Dual high-speed USB to UART/MPSSE bridge, LQFP-64, -40 to +85 C ({FT}): A = flash programming, B = UART"}),
    Part("FB1", "Device:FerriteBead_Small", "220R", "Inductor_SMD:L_0603_1608Metric", (60, 150), {"1": "+3V3", "2": "+3V3_PHY"},
         fields={"Manufacturer": "Murata", "MPN": "BLM18PG221SN1D",
                 "Description": f"Ferrite bead 220 ohm at 100 MHz, 1.4 A, 0.10 ohm max, 0603 (Murata): VPHY filter ({FT} Table 3.2, Figure 6.1)"}),
    Part("FB2", "Device:FerriteBead_Small", "220R", "Inductor_SMD:L_0603_1608Metric", (60, 175), {"1": "+3V3", "2": "+3V3_PLLF"},
         fields={"Manufacturer": "Murata", "MPN": "BLM18PG221SN1D",
                 "Description": f"Ferrite bead 220 ohm at 100 MHz, 1.4 A, 0.10 ohm max, 0603 (Murata): VPLL filter ({FT} Table 3.2, Figure 6.1)"}),
    cap("C8", "4.7u", "+3V3_PHY", "GND", (75, 160), f"Capacitor 4.7 uF 16 V X5R 0603 (VPHY pin 4: {FT} Figure 6.1)", C4U7, C0603),
    cap("C9", "100n", "+3V3_PHY", "GND", (88, 160), f"Capacitor 100 nF X7R 0402 (VPHY pin 4: {FT} Figure 6.1)"),
    cap("C10", "4.7u", "+3V3_PLLF", "GND", (75, 185), f"Capacitor 4.7 uF 16 V X5R 0603 (VPLL pin 9: {FT} Figure 6.1)", C4U7, C0603),
    cap("C11", "100n", "+3V3_PLLF", "GND", (88, 185), f"Capacitor 100 nF X7R 0402 (VPLL pin 9: {FT} Figure 6.1)"),
    # VREGOUT: two 4.7 uF, so that at 1.8 V Murata's small-signal curve keeps FTDI's 3.3 uF down to -30 C: 2 x 2.81 uF
    cap("C12", "4.7u", "+1V8", "GND", (150, 150), f"Capacitor 4.7 uF 16 V X5R 0603 (VREGOUT pin 49, with C44: at least 3.3 uF, {FT} Table 3.2; 2 x 2.81 uF at 1.8 V, -30 C, 0.01 Vrms)", C4U7, C0603),
    cap("C44", "4.7u", "+1V8", "GND", (198, 170), "Capacitor 4.7 uF 16 V X5R 0603 (VREGOUT, in parallel with C12)", C4U7, C0603),
    cap("C13", "100n", "+3V3", "GND", (162, 150), f"Capacitor 100 nF X7R 0402 (VREGIN pin 50: {FT} Figure 6.1)"),
    cap("C14", "100n", "+1V8", "GND", (174, 150), f"Capacitor 100 nF X7R 0402 (VCORE pin 12: {FT} Figure 6.1)"),
    cap("C15", "100n", "+1V8", "GND", (186, 150), f"Capacitor 100 nF X7R 0402 (VCORE pin 37: {FT} Figure 6.1)"),
    cap("C16", "100n", "+1V8", "GND", (198, 150), f"Capacitor 100 nF X7R 0402 (VCORE pin 64: {FT} Figure 6.1)"),
    cap("C17", "100n", "+3V3", "GND", (150, 170), f"Capacitor 100 nF X7R 0402 (VCCIO pin 20: {FT} Figure 6.1)"),
    cap("C18", "100n", "+3V3", "GND", (162, 170), f"Capacitor 100 nF X7R 0402 (VCCIO pin 31: {FT} Figure 6.1)"),
    cap("C19", "100n", "+3V3", "GND", (174, 170), f"Capacitor 100 nF X7R 0402 (VCCIO pin 42: {FT} Figure 6.1)"),
    cap("C20", "100n", "+3V3", "GND", (186, 170), f"Capacitor 100 nF X7R 0402 (VCCIO pin 56: {FT} Figure 6.1)"),
    Part("R6", "Device:R_Small", "12k", R0402, (75, 210), {"1": "FT_REF", "2": "GND"},
         fields={"Manufacturer": "Yageo", "MPN": "RC0402FR-0712KL",
                 "Description": f"Resistor 12 kohm 1% 0402 (REF current reference: {FT} Table 3.3)"}),
    res("R7", "1k", "FT_RST_N", "+3V3", (75, 225), f"RESET# pull-up: {FT} Figure 6.1"),
    # FT2232H clock: a 12 MHz CMOS oscillator into OSCI, OSCO open (FTDI DS 6.3, the alternative to a crystal)
    Part("X2", "Oscillator:ECS-2520MV-xxx-xx", "12MHz", "Oscillator:Oscillator_SMD_ECS_2520MV-xxx-xx-4Pin_2.5x2.0mm", (60, 245),
         {"Tri-State": "+3V3", "GND": "GND", "OUT": "FT_XI", "VDD": "+3V3"},
         fields={"Manufacturer": "ECS", "MPN": "ECS-2520MVLC-120-CN-TR",
                 "Description": f"Oscillator 12 MHz CMOS, +-25 ppm (tolerance, temperature, supply, load, reflow) + 3 ppm first-year aging, -40 to +85 C, 1.8 mA max (ECS-2520MVLC Rev. 2022): FT2232H OSCI, {FT} Table 6.1 asks 12 MHz +-30 ppm"}),
    cap("C42", "100n", "+3V3", "GND", (45, 260), "Capacitor 100 nF X7R 0402 (FT2232H oscillator X2 VDD)"),
    Part("U7", "Memory_EEPROM:93LCxxBxxOT", "93LC56B", "Package_TO_SOT_SMD:SOT-23-6", (140, 290),
         {"DO": "EE_DO", "GND": "GND", "DI": "EE_DATA", "CLK": "EE_CLK", "CS": "EE_CS", "VCC": "+3V3"},
         fields={"Manufacturer": "Microchip", "MPN": "93LC56BT-I/OT",
                 "Description": f"2 kbit Microwire EEPROM, 16-bit, -40 to +85 C (Microchip DS21794G): FT2232H configuration ({FT} section 7); ships blank"}),
    res("R8", "2.2k", "EE_DO", "EE_DATA", (150, 255), f"EEPROM DO to EEDATA: {FT} Table 3.4"),
    res("R9", "10k", "EE_DO", "+3V3", (162, 255), f"EEPROM DO pull-up: {FT} Table 3.4"),
    res("R10", "10k", "EE_CS", "+3V3", (174, 255), f"EECS pull-up: {FT} Figure 6.1"),
    res("R11", "10k", "EE_CLK", "+3V3", (186, 255), f"EECLK pull-up: {FT} Figure 6.1"),
    # channel A to the configuration nets, through 1 kohm (see the module notes)
    res("R12", "1k", "FT_SCK", "FLASH_SCK", (150, 215), "ADBUS0 SCK (iceprog), series: UART-mode TXD clash limited to 3.3 mA"),
    res("R13", "1k", "FT_MOSI", "FLASH_MOSI", (162, 215), "ADBUS1 MOSI (iceprog), series"),
    res("R14", "1k", "FT_MISO", "FLASH_MISO", (174, 215), "ADBUS2 MISO (iceprog), series: UART-mode RTS# clash limited to 3.3 mA"),
    res("R15", "1k", "FT_CS", "FLASH_CS", (186, 215), "ADBUS4 CS (iceprog), series: UART-mode DTR# clash limited to 3.3 mA"),
    res("R16", "1k", "FT_CDONE", "CDONE", (198, 215), "ADBUS6 CDONE (iceprog input), series: keeps the FT2232H's pin off the CDONE node"),
    res("R17", "1k", "FT_CRESET", "CRESET_N", (210, 215), "ADBUS7 CRESET (iceprog, driven low only), series: low level 0.3 V with the 10 kohm pull-up"),

    # ---- iCE40UP5K -------------------------------------------------------------------------------------------------------
    Part("U8", "EoS_FPGA:ICE40UP5K-SG48", "iCE40UP5K", "Package_DFN_QFN:QFN-48-1EP_7x7mm_P0.5mm_EP5.3x5.3mm", (330, 220),
         {"VCC": "+1V2", "VCCPLL": "+1V2_PLL", "VCCIO_0": "+3V3", "SPI_VCCIO1": "+3V3", "VCCIO_2": "+3V3", "VPP_2V5": "+3V3",
          "GND": "GND", "CRESET_B": "CRESET_N", "CDONE": "CDONE", **FPGA_IO},
         fields={"Manufacturer": "Lattice", "MPN": "ICE40UP5K-SG48I",
                 "Description": f"iCE40 UltraPlus FPGA, 5,280 LUTs, 1 Mbit SPRAM, QFN-48 7 x 7 mm, industrial (TJ -40 to +100 C) ({DS})"}),
    cap("C23", "100n", "+3V3", "GND", (270, 160), f"Capacitor 100 nF X7R 0402 (VCCIO_2 pin 1: {HC} Table 2.2)"),
    cap("C24", "4.7u", "+3V3", "GND", (282, 160), f"Capacitor 4.7 uF 16 V X5R 0603 (VCCIO_2 group: {HC} Table 2.2)", C4U7, C0603),
    cap("C25", "100n", "+1V2", "GND", (294, 160), f"Capacitor 100 nF X7R 0402 (VCC pin 5: {HC} Table 2.2)"),
    cap("C26", "4.7u", "+1V2", "GND", (306, 160), f"Capacitor 4.7 uF 16 V X5R 0603 (VCC group: {HC} Table 2.2)", C4U7, C0603),
    cap("C27", "100n", "+1V2", "GND", (318, 160), f"Capacitor 100 nF X7R 0402 (VCC pin 30: {HC} Table 2.2)"),
    cap("C28", "100n", "+3V3", "GND", (330, 160), f"Capacitor 100 nF X7R 0402 (VCCIO_0 pin 33: {HC} Table 2.2)"),
    cap("C29", "4.7u", "+3V3", "GND", (342, 160), f"Capacitor 4.7 uF 16 V X5R 0603 (VCCIO_0 group: {HC} Table 2.2)", C4U7, C0603),
    cap("C30", "100n", "+3V3", "GND", (354, 160), f"Capacitor 100 nF X7R 0402 (SPI_VCCIO1 pin 22: {HC} Table 2.2)"),
    cap("C31", "4.7u", "+3V3", "GND", (366, 160), f"Capacitor 4.7 uF 16 V X5R 0603 (SPI_VCCIO1 group: {HC} Table 2.2)", C4U7, C0603),
    cap("C32", "100n", "+3V3", "GND", (378, 160), f"Capacitor 100 nF X7R 0402 (VPP_2V5 pin 24: {HC} Table 2.2)"),
    cap("C33", "4.7u", "+3V3", "GND", (390, 160), f"Capacitor 4.7 uF 16 V X5R 0603 (VPP_2V5 group: {HC} Table 2.2)", C4U7, C0603),
    res("R18", "100", "+1V2", "+1V2_PLL", (270, 280), f"VCCPLL filter RS: {PLL} Figure 5.4, {HC} Table 2.2"),
    cap("C34", "4.7u", "+1V2_PLL", "GND", (285, 280), f"Capacitor 4.7 uF 16 V X5R 0603 (VCCPLL CLF: {PLL} Figure 5.4; {HC} Table 2.2 value, 100 ohm x 4.7 uF = 0.47 ms)", C4U7, C0603),
    cap("C35", "100n", "+1V2_PLL", "GND", (300, 280), f"Capacitor 100 nF X7R 0402 (VCCPLL CHF at pin 29: {PLL} Figure 5.4)"),
    res("R19", "10k", "CRESET_N", "+3V3", (270, 300), f"CRESET_B pull-up: no internal pull-up ({TN1} 5.1, {HC} Table 3.1); the supervisor's open-drain RESET pull-up (TI SBVS050N 5: 10 kohm to 1 Mohm)"),
    # Supervisors (TI SBVS050N Figure 7-3: the 1.2 V monitor's RESET drives the 3.3 V monitor's MR): CRESET_B stays
    # low until +1V2 and +3V3 are both valid, and again whenever either sags ({DS} 4.6; BENCH-READY D5)
    Part("U10", "Power_Supervisor:TPS3808DBV", "TPS3808G33", "Package_TO_SOT_SMD:SOT-23-6", (232, 332),
         {"1": "CRESET_N", "2": "GND", "3": "MR_N", "4": NC, "5": "+3V3", "6": "+3V3_BUCK"},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPS3808G33DBVR",
                 "Description": "Supervisor, open-drain RESET, VIT 3.07 V +-1.25 % (-40..85 C), CT open = 20 ms (12-28 ms), MR 90 kohm pull-up (TI SBVS050N): CRESET_B from +3V3 and MR"}),
    Part("U11", "Power_Supervisor:TPS3808DBV", "TPS3808G12", "Package_TO_SOT_SMD:SOT-23-6", (232, 300),
         {"1": "MR_N", "2": "GND", "3": NC, "4": NC, "5": "+1V2", "6": "+3V3_BUCK"},
         fields={"Manufacturer": "Texas Instruments", "MPN": "TPS3808G12DBVR",
                 "Description": "Supervisor, open-drain RESET, VIT 1.12 V +-1.25 % (-40..85 C), CT open = 20 ms (TI SBVS050N): holds U10's MR low until +1V2 is valid"}),
    cap("C40", "100n", "+3V3_BUCK", "GND", (252, 325), "Capacitor 100 nF X7R 0402 (U10 VDD: TI SBVS050N 5, 0.1 uF at the pin)"),
    cap("C41", "100n", "+3V3_BUCK", "GND", (252, 293), "Capacitor 100 nF X7R 0402 (U11 VDD: TI SBVS050N 5, 0.1 uF at the pin)"),
    res("R20", "2.2k", "CDONE", "+3V3", (300, 300), f"CDONE pull-up: at most 1/(2 x 17 MHz x 10 pF) = 2.9 kohm ({TN1} 5.1)"),
    res("R21", "10k", "CDONE", "DONE_G", (315, 300), "DONE LED MOSFET gate resistor: keeps the gate's 50 pF off the CDONE node"),
    Part("Q1", "Transistor_FET:2N7002", "2N7002", "Package_TO_SOT_SMD:SOT-23", (330, 300), {"G": "DONE_G", "S": "GND", "D": "DONE_K"},
         fields={"Manufacturer": "Nexperia", "MPN": "2N7002,215",
                 "Description": "N-MOSFET 60 V 300 mA, VGS(th) 1-2.5 V, Ciss 50 pF max (Nexperia 2N7002 Rev. 7): lights DONE when CDONE is high"}),
    led("D2", "green", "DONE_A", "DONE_K", (345, 300), "DONE, lit once the FPGA has configured (CDONE high)"),
    res("R22", "680", "+3V3", "DONE_A", (360, 300), "DONE LED: (3.3 - 1.9) V / 680 ohm = 2.1 mA"),
    res("R23", "10k", "FLASH_CS", "+3V3", (270, 320), f"SPI_SS_B pull-up, master SPI mode ({HC} Table 3.1, {TN1} 9.3); also holds the flash deselected"),
    res("R24", "10k", "FLASH_SCK", "+3V3", (285, 320), f"SPI_SCK pull-up ({HC} Table 3.1)"),

    # ---- configuration flash -----------------------------------------------------------------------------------------------
    Part("U9", "Memory_Flash:W25Q128JVS", "W25Q128JVS", "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm", (430, 220),
         {"~{CS}": "FLASH_CS", "DO/IO_{1}": "FLASH_MISO", "~{WP}/IO_{2}": "FLASH_IO2", "GND": "GND",
          "DI/IO_{0}": "FLASH_MOSI", "CLK": "FLASH_SCK", "~{HOLD}/~{RESET}/IO_{3}": "FLASH_IO3", "VCC": "+3V3"},
         fields={"Manufacturer": "Winbond", "MPN": "W25Q128JVSIQ",
                 "Description": "128 Mbit SPI NOR flash, SOIC-8 208 mil, -40 to +85 C (W25Q128JV Rev. F): FPGA bitstream at 0, EPU firmware after it"}),
    cap("C37", "100n", "+3V3", "GND", (455, 210), "Capacitor 100 nF X7R 0402 (flash VCC)"),
    res("R25", "10k", "FLASH_IO2", "+3V3", (455, 230), "IO2 (/WP) pull-up: QE = 1 on IQ parts (W25Q128JV 7.1.4), unused in single SPI"),
    res("R26", "10k", "FLASH_IO3", "+3V3", (455, 245), "IO3 (/HOLD) pull-up: QE = 1 on IQ parts (W25Q128JV 7.1.4), unused in single SPI"),

    # ---- 12 MHz oscillator -----------------------------------------------------------------------------------------------------
    Part("X1", "Oscillator:ECS-2520MV-xxx-xx", "12MHz", "Oscillator:Oscillator_SMD_ECS_2520MV-xxx-xx-4Pin_2.5x2.0mm", (430, 160),
         {"Tri-State": "+3V3", "GND": "GND", "OUT": "CLK12", "VDD": "+3V3"},
         fields={"Manufacturer": "ECS", "MPN": "ECS-2520MV-120-BN-TR",
                 "Description": "Oscillator 12 MHz CMOS, +-50 ppm, -40 to +85 C, 6 mA max at 3.3 V (ECS-2520MV): EPU clk on pin 35"}),
    cap("C38", "100n", "+3V3", "GND", (455, 160), "Capacitor 100 nF X7R 0402 (oscillator VDD)"),

    # ---- LEDs: power, user (EPU gpio[0..3]), the RGB sinks -----------------------------------------------------------------
    led("D1", "red", "PWR_A", "GND", (520, 60), "power, on the 3.3 V rail"),
    res("R27", "750", "+3V3", "PWR_A", (505, 60), "power LED: (3.3 - 1.75) V / 750 ohm = 2.1 mA"),
    *[led(f"D{3 + i}", "green", f"LED{i}_A", "GND", (520, 90 + 15 * i), f"user LED {i}, EPU gpio[{i}]") for i in range(4)],
    *[res(f"R{28 + i}", "680", f"LED{i}", f"LED{i}_A", (505, 90 + 15 * i), f"user LED {i}: (3.3 - 1.9) V / 680 ohm = 2.1 mA") for i in range(4)],
    led("D7", "red", "RGB0_A", "RGB0_K", (520, 160), "on RGB0 (pin 39), a 24 mA open-drain sink"),
    led("D8", "green", "RGB1_A", "RGB1_K", (520, 175), "on RGB1 (pin 40), a 24 mA open-drain sink"),
    led("D9", "yellow", "RGB2_A", "RGB2_K", (520, 190), "on RGB2 (pin 41), a 24 mA open-drain sink"),
    res("R32", "100", "+3V3", "RGB0_A", (505, 160), "RGB0 LED: 15 mA max as open drain; 0.5 V headroom up to 10 mA as a current sink (FPGA-TN-02021 6)"),
    res("R33", "100", "+3V3", "RGB1_A", (505, 175), "RGB1 LED: 14 mA max as open drain; 0.5 V headroom up to 9 mA as a current sink (FPGA-TN-02021 6)"),
    res("R34", "100", "+3V3", "RGB2_A", (505, 190), "RGB2 LED: 14.5 mA max as open drain; 0.5 V headroom up to 9.5 mA as a current sink (FPGA-TN-02021 6)"),

    # ---- buttons, boot jumper ---------------------------------------------------------------------------------------------------
    button("SW1", "CRESET", "MR_N", (545, 60), "CRESET: U10's MR, so a press gives one clean 12-28 ms CRESET_B pulse after release (debounced); reconfigures the FPGA from the flash"),
    button("SW2", "RESET", "RST_N", (545, 85), "RESET: EPU reset (rst_btn_n)"),
    button("SW3", "USER", "BTN0", (545, 110), "USER: EPU gpio[4]"),
    button("SW4", "USER2", "BTN1", (545, 135), "USER2: FPGA pin 13, reserved"),
    res("R35", "10k", "RST_N", "+3V3", (565, 85), "rst_btn_n pull-up (EPU's top has no pull-up on it)"),
    cap("C39", "100n", "RST_N", "GND", (580, 85), "Capacitor 100 nF X7R 0402 (reset filter: 1 ms with 10 kohm, BENCH-READY D5; EPU synchronises it)"),
    res("R36", "10k", "BTN0", "+3V3", (565, 110), "BTN0 pull-up (EPU's gpio SB_IO has PULLUP = 0)"),
    res("R37", "10k", "BTN1", "+3V3", (565, 135), "BTN1 pull-up"),
    Part("JP1", "Jumper:Jumper_2_Open", "BOOT", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", (545, 165),
         {"A": "BOOT_SEL", "B": "GND"},
         fields={"Manufacturer": "Samtec", "MPN": "TSW-102-07-G-S",
                 "Description": "Header 1x2 2.54 mm: BOOT strap, open = boot_sel 1, shunt fitted = 0 (Samtec TSW)"}),
    res("R38", "10k", "BOOT_SEL", "+3V3", (565, 165), "boot_sel pull-up: reads 1 with the jumper open"),

    # ---- JTAG ---------------------------------------------------------------------------------------------------------------
    Part("J2", "Connector:Conn_ARM_JTAG_SWD_10", "JTAG", "EoS_Packages:Samtec_FTSH-105-xx-x-DV_2x05_P1.27mm_Vertical_SMD",
         (410, 290), {"VTref": "+3V3", "SWDIO/TMS": "JTAG_TMS", "GND": "GND", "SWCLK/TCK": "JTAG_TCK", "SWO/TDO": "JTAG_TDO",
                      "KEY": NC, "NC/TDI": "JTAG_TDI", "GNDDetect": "GND", "~{RESET}": "RST_N"},
         fields={"Manufacturer": "Samtec", "MPN": "FTSH-105-01-L-DV-K",
                 "Description": "JTAG header, Arm 10-pin 1.27 mm layout (VTref, TMS, TCK, TDO, TDI, nRESET): EPU's planned debug port"}),

    # ---- Pmod A (I2C + GPIO, Type 6A) and Pmod B (SPI, Type 2A) ------------------------------------------------------------------
    rpack("RN1", [("PMODA_1", "PA1"), ("PMODA_7", "PA7"), ("PMODA_2", "PA2"), ("PMODA_8", "PA8")], (470, 262), "Pmod A pins 1, 7, 2, 8"),
    rpack("RN2", [("I2C_SCL", "PA3"), ("PMODA_9", "PA9"), ("I2C_SDA", "PA4"), ("PMODA_10", "PA10")], (470, 292), "Pmod A pins 3, 9, 4, 10"),
    rpack("RN3", [("PMODB_1", "PB1"), ("PMODB_7", "PB7"), ("FLASH_MOSI", "PB2"), ("PMODB_8", "PB8")], (470, 330), "Pmod B pins 1, 7, 2, 8"),
    rpack("RN4", [("FLASH_MISO", "PB3"), ("PMODB_9", "PB9"), ("FLASH_SCK", "PB4"), ("PMODB_10", "PB10")], (470, 362), "Pmod B pins 3, 9, 4, 10"),
    # ESD arrays between the series resistors and the sockets, one per two socket rows (BENCH-READY D1)
    esd4("U12", ["PA1", "PA7", "PA2", "PA8"], (340, 62), "Pmod A pins 1, 7, 2, 8"),
    esd4("U13", ["PA3", "PA9", "PA4", "PA10"], (395, 62), "Pmod A pins 3, 9, 4, 10"),
    esd4("U14", ["PB1", "PB7", "PB2", "PB8"], (450, 62), "Pmod B pins 1, 7, 2, 8"),
    esd4("U15", ["PB3", "PB9", "PB4", "PB10"], (340, 105), "Pmod B pins 3, 9, 4, 10"),
    res("R39", "4.7k", "PA3", "+3V3", (500, 268), f"I2C SCL pull-up on the host ({PMOD} section 2)"),
    res("R40", "4.7k", "PA4", "+3V3", (500, 290), f"I2C SDA pull-up on the host ({PMOD} section 2)"),
    res("R41", "10k", "PMODB_1", "+3V3", (445, 328), "spi_cs_n[1] pull-up: the Pmod device stays deselected while the FPGA is unconfigured"),
    # Pmod pin n -> KiCad pad: pins 1-6 the row away from the edge (odd pads), pin 1 at the top end (see PLACEMENT)
    Part("J3", "Connector_Generic:Conn_02x06_Odd_Even", "PMOD A", PMOD_FP, (550, 275),
         {"11": "PA1", "9": "PA2", "7": "PA3", "5": "PA4", "3": "GND", "1": "+3V3",
          "12": "PA7", "10": "PA8", "8": "PA9", "6": "PA10", "4": "GND", "2": "+3V3"},
         fields={"Manufacturer": "Samtec", "MPN": "SSW-106-02-G-D-RA",
                 "Description": f"Pmod A host port, 2x6 2.54 mm right-angle socket: 1 INT (gpio[7]), 2 GPIO, 3 SCL, 4 SDA, 7-10 GPIO, 5/11 GND, 6/12 3.3 V ({PMOD} 5.5 Type 6A)"}),
    Part("J4", "Connector_Generic:Conn_02x06_Odd_Even", "PMOD B", PMOD_FP, (550, 345),
         {"11": "PB1", "9": "PB2", "7": "PB3", "5": "PB4", "3": "GND", "1": "+3V3",
          "12": "PB7", "10": "PB8", "8": "PB9", "6": "PB10", "4": "GND", "2": "+3V3"},
         fields={"Manufacturer": "Samtec", "MPN": "SSW-106-02-G-D-RA",
                 "Description": f"Pmod B host port, 2x6 2.54 mm right-angle socket: 1 CS (spi_cs_n[1]), 2 MOSI, 3 MISO, 4 SCK, 7 INT (gpio[5]), 8 RESET (gpio[6]), 9 CS2, 10 CS3 ({PMOD} 5.2 Type 2A)"}),

    # ---- EXT header -------------------------------------------------------------------------------------------------------------
    rpack("RN5", [("EXT0", "EXT0_P"), ("EXT1", "EXT1_P"), ("EXT2", "EXT2_P"), ("EXT3", "EXT3_P")], (400, 345), "EXT header"),
    esd4("U16", ["EXT3_P", "EXT2_P", "EXT1_P", "EXT0_P"], (395, 105), "EXT header pins 5, 4, 3, 2"),
    Part("J5", "Connector_Generic:Conn_01x06", "EXT", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", (425, 375),
         {"1": "+3V3", "2": "EXT0_P", "3": "EXT1_P", "4": "EXT2_P", "5": "EXT3_P", "6": "GND"},
         fields={"Manufacturer": "Samtec", "MPN": "TSW-106-07-G-S",
                 "Description": "Header 1x6 2.54 mm: 3.3 V (an output), EXT0-EXT3 (FPGA pins 48, 2, 3, 12 via 200 ohm, ESD array U16), GND (Samtec TSW)"}),

    # ---- test points ------------------------------------------------------------------------------------------------------------
    tp("TP1", "VBUS_F", (60, 330), "USB 5 V after the fuse"),
    tp("TP2", "+3V3_BUCK", (80, 330), "buck output"),
    tp("TP3", "+1V2_LDO", (100, 330), "1.2 V LDO output (regulator side of the R5 link)"),
    tp("TP4", "+3V3", (120, 330), "3.3 V main rail"),
    tp("TP5", "+1V8", (140, 330), "FT2232H core (its own regulator)"),
    tp("TP6", "+1V2_PLL", (160, 330), "FPGA VCCPLL"),
    tp("TP7", "GND", (180, 330), "ground near the input"),
    tp("TP8", "GND", (200, 330), "ground near the FPGA"),
]
HOLES = [(3.5, 3.5), (71.5, 3.5), (3.5, 51.5), (71.5, 51.5)]
for i, _ in enumerate(HOLES):
    PARTS.append(Part(f"H{i + 1}", "Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", (260 + 20 * i, 360), {},
                      fields={"Description": "Mounting hole 3.2 mm (M3), unplated"}))

W, H = 75.0, 55.0
FT_C = (25.0, 26.0)          # FT2232H centre (LQFP-64, courtyard +-6.7 mm)
FPGA_C = (48.0, 26.0)        # iCE40UP5K centre (QFN-48, courtyard -4.44..+4.10 mm)
PMOD_X = 62.0                # Pmod sockets: the far (pins 1-6) column; the mating face 12.57 mm further, 0.43 mm in from the edge
PMOD_A_Y = 22.5              # Pmod A: pin 6 (pad 1) at this y, pin 1 (pad 11) 12.7 mm above; Pmod B 0.9 in (22.86 mm) lower

# Board placement: (x, y, rotation) in mm, origin top-left. USB-C on the left edge, the FT2232H next to it
# (its DM/DP, pins 7/8, level with the receptacle's pair), the FPGA right of the FT2232H with its
# configuration-SPI side (pins 13-24) facing the flash below it, the Pmod ports on the right edge, LEDs,
# JTAG and the EXT header along the top, buttons along the bottom, power in the bottom-left corner.
# Decoupling capacitors sit just outside each chip's courtyard, in line with their pins, the supply pad
# toward the pin.
PLACEMENT = {
    **{f"H{i + 1}": (x, y, 0) for i, (x, y) in enumerate(HOLES)},
    # USB-C, ESD (D- above D+, as the FT2232H's DM/DP), CC resistors, fuse
    "J1": (USB_C_EDGE, 25.5, 270), "U1": (10.6, 25.5, 90), "R1": (9.6, 19.6, 0), "R2": (9.7, 27.9, 0),
    "U2": (10.6, 30.4, 0), "F1": (6.6, 33.8, 270),
    # power: buck, LDO, link, load switch in the bottom-left corner. The buck as TI SLVSDG1C Figure 20: U3 turned
    # so VIN (pin 4) and FB (pin 5) face left and SW (pin 3), GND (pin 2) and EN (pin 1) face right; C1 beside VIN
    # with its ground pad joined to pin 2 under the body; L1 right of SW, one short top-layer stub; C2 after L1;
    # the feedback divider below FB, on the side away from SW
    "U3": (8.0, 39.6, 180), "C1": (4.85, 39.6, 270), "L1": (12.5, 39.0, 0), "C2": (16.0, 39.0, 270), "C43": (18.0, 39.0, 270),
    "R4": (5.4, 42.6, 270), "R3": (6.4, 42.6, 90), "C3": (7.4, 42.6, 90),
    "U4": (10.6, 48.4, 0), "C4": (7.6, 45.6, 90), "C5": (13.6, 48.4, 90), "R5": (15.8, 48.4, 90),
    "U5": (20.6, 47.2, 0), "C6": (20.6, 43.6, 0), "C7": (24.0, 47.6, 90), "R42": (20.6, 50.4, 0),
    # supervisors right of the load switch, turned so VDD (pin 6) faces its capacitor on the left and the
    # 1.2 V monitor's RESET (pin 1) sits beside the 3.3 V monitor's MR (pin 3)
    "U11": (25.0, 39.9, 180), "C41": (22.4, 40.4, 90), "U10": (25.0, 43.8, 180), "C40": (22.4, 44.3, 90),
    # FT2232H. Its 12 MHz oscillator left of its top-left corner, the output pad toward OSCI (pin 2).
    # Under it, in pin order: VPHY (pin 4) filter run out to the left, REF (pin 6), the USB pair (7, 8),
    # VPLL (pin 9) filter, VCORE (pin 12), RESET# (pin 14) pull-up
    "U6": (FT_C[0], FT_C[1], 0),
    "X2": (16.4, 20.6, 0), "C42": (16.9, 18.3, 180),
    "C9": (17.0, 23.85, 180), "R6": (15.0, 24.5, 0), "FB1": (11.8, 23.5, 0), "C8": (11.8, 21.7, 180),
    "C11": (17.0, 26.88, 270), "FB2": (14.2, 26.9, 0), "C10": (14.2, 28.7, 0),
    "C14": (17.0, 28.45, 180), "R7": (17.0, 29.65, 180),
    # top: VCORE pin 64, VCCIO pin 56, VREGIN pin 50, VREGOUT pin 49, the EEPROM
    "C16": (21.25, 18.2, 90), "C20": (25.25, 18.2, 90), "C13": (28.25, 18.2, 90), "C12": (30.8, 17.6, 90), "C44": (32.3, 17.6, 90),
    "U7": (24.2, 14.0, 0), "R8": (20.6, 13.0, 90), "R9": (20.6, 15.4, 90), "R10": (27.6, 13.0, 90), "R11": (27.6, 15.4, 90),
    # right: VCCIO pin 42, VCORE pin 37; bottom: VCCIO pins 20 and 31, the channel-A series resistors
    "C19": (32.9, 25.25, 0), "C15": (32.9, 28.0, 0),
    "C17": (22.75, 33.8, 270), "C18": (28.25, 33.8, 270),
    "R12": (19.2, 36.3, 90), "R13": (20.4, 36.3, 90), "R14": (21.6, 36.3, 90), "R15": (24.0, 36.3, 90),
    "R16": (25.2, 36.3, 90), "R17": (26.4, 36.3, 90),
    # iCE40UP5K; left: VCCIO_2 pin 1, VCC pin 5; right: VCCIO_0 pin 33, VCC pin 30, VCCPLL pin 29 and its filter;
    # bottom: SPI_VCCIO1 pin 22, VPP pin 24
    "U8": (FPGA_C[0], FPGA_C[1], 0),
    "C23": (42.4, 23.25, 180), "C24": (40.0, 22.2, 90), "C25": (42.4, 25.25, 180), "C26": (40.0, 26.4, 90),
    "C28": (54.6, 23.0, 0), "C27": (54.0, 25.2, 90), "C35": (54.0, 27.2, 270), "C34": (56.4, 27.4, 270), "R18": (58.4, 26.6, 180),
    "C29": (57.6, 24.0, 90),
    "C30": (49.75, 31.2, 270), "C32": (51.2, 31.2, 270), "C31": (49.9, 33.6, 0), "C33": (53.2, 32.4, 90),
    # CRESET_B pull-up, CDONE pull-up, DONE LED, SPI pull-ups: between the two chips, below the UART lines
    "R19": (35.6, 30.4, 90), "R20": (38.0, 30.4, 90), "R21": (39.2, 30.4, 90),
    "Q1": (39.6, 33.8, 90), "D2": (36.2, 34.6, 90), "R22": (36.2, 37.6, 90),
    "R23": (42.6, 31.4, 90), "R24": (43.8, 31.4, 90),
    # flash below the FPGA's left half
    "U9": (42.0, 40.0, 0), "C37": (47.8, 38.1, 0), "R25": (36.6, 41.6, 90), "R26": (47.6, 41.6, 90),
    # 12 MHz oscillator above the FPGA's top-right corner, near pin 35
    "X1": (54.4, 20.4, 270), "C38": (57.0, 20.6, 90),
    # LEDs above the FPGA: user LEDs 0-1, the three RGB-sink LEDs, user LEDs 2-3; resistors under them
    "D3": (42.2, 14.4, 90), "D4": (44.0, 14.4, 90), "D9": (45.8, 14.4, 90), "D8": (47.6, 14.4, 90),
    "D7": (49.4, 14.4, 90), "D5": (51.2, 14.4, 90), "D6": (53.0, 14.4, 90),
    "R28": (42.2, 17.6, 90), "R29": (44.0, 17.6, 90), "R34": (45.8, 17.6, 90), "R33": (47.6, 17.6, 90),
    "R32": (49.4, 17.6, 90), "R30": (51.2, 17.6, 90), "R31": (53.0, 17.6, 90),
    "D1": (28.4, 41.0, 90), "R27": (28.4, 38.0, 90),
    # buttons and the boot jumper along the bottom edge, their pull-ups and the reset filter above them
    "SW1": (30.0, 51.6, 0), "SW2": (37.0, 51.6, 0), "SW3": (44.0, 51.6, 0), "SW4": (51.0, 51.6, 0),
    "R35": (36.4, 47.6, 90), "C39": (37.6, 47.6, 90), "R36": (44.0, 47.6, 90), "R37": (51.0, 47.6, 90),
    "JP1": (58.6, 51.6, 270), "R38": (57.6, 46.0, 0),
    # JTAG above the FPGA's top-left corner, EXT along the top edge left of it, its ESD array between the
    # series resistors and the header (the line to header pin 5 on the array's top row)
    "J2": (37.6, 11.0, 90), "RN5": (30.4, 9.0, 90), "J5": (14.6, 4.2, 90), "U16": (26.0, 8.8, 0),
    # Pmod ports on the right edge. Each pair of socket rows has a series-resistor array and, between it and the
    # socket, an ESD array: a line enters an array's left pad and leaves from the pad opposite, toward its socket
    # pin, in the socket's row order (inner pin, the outer pin passing between two inner pads, the next inner pin...)
    "J3": (PMOD_X, PMOD_A_Y, 180), "J4": (PMOD_X, PMOD_A_Y + 22.86, 180),
    "RN1": (56.6, 11.7, 0), "U12": (59.25, 11.7, 0), "RN2": (56.6, 16.8, 0), "U13": (59.25, 16.8, 0),
    "R39": (58.6, 20.0, 0), "R40": (58.6, 21.2, 0),
    "RN3": (56.6, 34.56, 0), "U14": (59.25, 34.56, 0), "RN4": (56.6, 39.65, 0), "U15": (59.25, 39.65, 0),
    "R41": (54.55, 33.4, 90),
    # test points: rails in the power corner, the FT2232H core and VCCPLL by their pins, ground at each end
    "TP1": (4.2, 36.0, 0), "TP2": (17.6, 43.8, 0), "TP3": (13.0, 52.6, 0), "TP4": (24.4, 52.0, 0),
    "TP5": (34.4, 17.6, 0), "TP6": (59.6, 29.4, 0), "TP7": (8.8, 52.8, 0), "TP8": (33.6, 34.6, 0),
}
_unplaced = sorted({p.ref for p in PARTS} - set(PLACEMENT))
assert not _unplaced, f"parts without a board position: {_unplaced}"
for _p in PARTS:
    _p.pcb = PLACEMENT[_p.ref]

# Laid before the autorouter, in this order, and locked (pcb_build.py place).
# * USB: each line from the receptacle's B-row contact (D- above D+, as the FT2232H's DM/DP) to its ESD pad,
#   the A-row contacts joined to them, then on to pins 7 and 8.
# * The 3.3 V buck as TI SLVSDG1C 10.1 and Figure 20 (see PLACEMENT), its power lines wider than their class.
# * The FT2232H oscillator's output to OSCI (pin 2), and its decoupling capacitor; the supervisors' chain
#   (U11 RESET to U10 MR) and their decoupling capacitors.
# * The FPGA clock: oscillator output to pin 35.
# * Decoupling: each capacitor at its pin, its supply pad toward the pin, joined by a short line.
# * The FT2232H's ground pins 10 (AGND) and 11, between the VPLL and VCORE lines, to C11's ground pad and its via:
#   in full build 2 they sat in a top-layer ground fragment with no via (frag.py).
# * spi_cs_n[1] (pin 23) down between the capacitors of pins 22 and 24 to its pull-up: in full build 1 their
#   fan-out vias boxed it in and no router run or repair could reach it.
# * VCCPLL as PLL 5.2 asks: "a single wire from the FPGA pin to the high frequency capacitor (CHF), then to the
#   low frequency capacitor (CLF), through the series resistor (RS)".
PRIORITY = [
    (("J1", "B6"), ("U1", "1")), (("J1", "B7"), ("U1", "2")),
    (("J1", "A6"), ("J1", "B6"), "join"), (("J1", "A7"), ("J1", "B7"), "join"),
    (("U1", "2"), ("U6", "7")), (("U1", "1"), ("U6", "8")),
    # buck (TI SLVSDG1C 10.1): VIN from C1, C1's ground under the body to pin 2, the switch node to L1 on the top
    # layer, L1 to C2, then the feedback node below FB
    (("U3", "4"), ("C1", "1"), 0.6), (("U3", "2"), ("C1", "2"), 0.5), (("U3", "3"), ("L1", "1"), 0.6),
    (("L1", "2"), ("C2", "1"), 0.6), (("C43", "1"), ("C2", "1"), 0.6), (("U3", "5"), ("R3", "2")), (("R4", "1"), ("R3", "2"), "join"),
    (("C3", "2"), ("R3", "2"), "join"), (("U3", "1"), ("C1", "1"), "join"),
    (("X2", "3"), ("U6", "2")), (("X2", "4"), ("C42", "1")),
    (("U11", "1"), ("U10", "3")), (("U10", "6"), ("C40", "1")), (("U11", "6"), ("C41", "1")),
    # Every protected line crosses its ESD array straight from the diode pad (1, 2, 4, 5) to the no-connect pad
    # opposite (10, 9, 7, 6), laid first, so the line has to pass the diode pad: in full build 8 EXT2_P reached
    # the no-connect pad from both sides and left its diode pad on a 5.7 mm branch (verification V-1)
    # The EXT header's four lines: in full builds 5 and 6 the autorouter hung one or two of them on a branch off the
    # array. Resistor side first, innermost first (RN5's pad 8 nearest the array), so the four nest without
    # crossing and reach the no-connect pads from the resistor side: in full build 9, laid after the header side,
    # EXT1_P went under the array on the bottom layer and joined the header-side track before its diode pad
    (("RN5", "8"), ("U16", "6")), (("RN5", "7"), ("U16", "7")), (("RN5", "6"), ("U16", "9")), (("RN5", "5"), ("U16", "10")),
    *[((u, d), (u, n)) for u in ("U12", "U13", "U14", "U15", "U16") for d, n in (("1", "10"), ("2", "9"), ("4", "7"), ("5", "6"))],
    (("U16", "1"), ("J5", "5")), (("U16", "2"), ("J5", "4")), (("U16", "4"), ("J5", "3")), (("U16", "5"), ("J5", "2")),
    (("X1", "3"), ("U8", "35")), (("X1", "1"), ("X1", "4")),
    (("U8", "23"), ("R41", "1")),
    (("U6", "4"), ("C9", "1")), (("U6", "9"), ("C11", "1")), (("U6", "11"), ("C11", "2")), (("U6", "10"), ("U6", "11")), (("U6", "12"), ("C14", "1")), (("U6", "37"), ("C15", "1")),
    (("U6", "42"), ("C19", "1")), (("U6", "20"), ("C17", "1")), (("U6", "31"), ("C18", "1")), (("U6", "49"), ("C12", "1")), (("C44", "1"), ("C12", "1")),
    (("U6", "50"), ("C13", "1")), (("U6", "56"), ("C20", "1")), (("U6", "64"), ("C16", "1")),
    (("U8", "1"), ("C23", "1")), (("U8", "5"), ("C25", "1")), (("U8", "30"), ("C27", "1")), (("U8", "33"), ("C28", "1")),
    (("U8", "22"), ("C30", "1")), (("U8", "24"), ("C32", "1")), (("U9", "8"), ("C37", "1")),
    (("U8", "29"), ("C35", "1")), (("C35", "1"), ("C34", "1")), (("C34", "1"), ("R18", "2")),
    # Pmod B pins 7 and 8 (gpio[5], gpio[6]) from FPGA pins 21 and 20 to RN3, after the decoupling lines: in full
    # builds 6 and 7 the autorouter's first run left one of them open between the bank-1 capacitors' vias
    (("U8", "21"), ("RN3", "2")), (("U8", "20"), ("RN3", "4")),
]

TEXTS = [
    # front, 0.8 mm: rail names at the test pads (BENCH-READY C1), Pmod pin 1, buttons, jumper, LEDs, headers (A4)
    {"text": "5V", "x": 5.7, "y": 36.0, "size": 0.8}, {"text": "3V3B", "x": 17.0, "y": 45.2, "size": 0.8},
    {"text": "1V2", "x": 13.0, "y": 54.0, "size": 0.8}, {"text": "GND", "x": 8.8, "y": 54.1, "size": 0.8},
    {"text": "3V3", "x": 24.4, "y": 53.6, "size": 0.8}, {"text": "1V8", "x": 34.4, "y": 19.2, "size": 0.8},
    {"text": "1V2P", "x": 59.4, "y": 30.8, "size": 0.8}, {"text": "GND", "x": 33.6, "y": 36.1, "size": 0.8},
    {"text": "PMOD A", "x": 62.4, "y": 7.4, "size": 0.8}, {"text": "1", "x": 60.5, "y": 9.8, "size": 0.8},
    {"text": "PMOD B", "x": 63.4, "y": 30.2, "size": 0.8}, {"text": "1", "x": 60.5, "y": 32.66, "size": 0.8},
    {"text": "CRESET", "x": 30.0, "y": 49.15, "size": 0.8}, {"text": "RESET", "x": 37.0, "y": 49.15, "size": 0.8},
    {"text": "USER", "x": 44.0, "y": 49.15, "size": 0.8}, {"text": "USER2", "x": 51.0, "y": 49.15, "size": 0.8},
    {"text": "BOOT", "x": 57.3, "y": 49.2, "size": 0.8},
    {"text": "0", "x": 42.2, "y": 12.2, "size": 0.8}, {"text": "1", "x": 44.0, "y": 12.2, "size": 0.8},
    {"text": "Y", "x": 45.8, "y": 12.2, "size": 0.8}, {"text": "G", "x": 47.6, "y": 12.2, "size": 0.8},
    {"text": "R", "x": 49.4, "y": 12.2, "size": 0.8}, {"text": "2", "x": 51.2, "y": 12.2, "size": 0.8},
    {"text": "3", "x": 53.0, "y": 12.2, "size": 0.8},
    {"text": "PWR", "x": 28.4, "y": 43.8, "size": 0.8}, {"text": "DONE", "x": 36.2, "y": 32.5, "size": 0.8},
    {"text": "JTAG", "x": 37.6, "y": 6.4, "size": 0.8}, {"text": "EXT", "x": 11.0, "y": 4.2, "size": 0.8},
    {"text": "3V3 PINS ARE OUTPUTS", "x": 50.0, "y": 8.4, "size": 0.8},
    {"text": "3V3", "x": 14.6, "y": 6.4, "size": 0.8}, {"text": "0", "x": 17.14, "y": 6.4, "size": 0.8},
    {"text": "1", "x": 19.68, "y": 6.4, "size": 0.8}, {"text": "2", "x": 22.22, "y": 6.4, "size": 0.8},
    {"text": "3", "x": 24.76, "y": 6.4, "size": 0.8}, {"text": "GND", "x": 27.3, "y": 6.4, "size": 0.8},
    # back: designer and rights
    {"text": "EoS EPU Board  rev A", "x": 37.5, "y": 24.0, "size": 1.0, "layer": "B_SilkS", "bold": True, "mirror": True},
    {"text": "(c) 2026 Kartikeydheer Srivastava", "x": 37.5, "y": 26.0, "size": 0.8, "layer": "B_SilkS", "mirror": True},
    {"text": "All rights reserved", "x": 37.5, "y": 27.4, "size": 0.8, "layer": "B_SilkS", "mirror": True},
]

BOARD = Board(
    name="eos-epu-up5k",
    title="EoS EPU Board",
    revision="A",
    date="2026-10-30",
    company=OWNER,
    licence=LICENCE,
    contact=CONTACT,
    licence_terms=LICENCE_TERMS,
    credits=["Pmod host port pinout, spacing and orientation: facts from Digilent's Pmod Interface Specification "
             "(revised October 28, 2020), used as a published specification only",
             "FT2232H channel A pin roles: from Project IceStorm's iceprog source (ISC licence) and openFPGALoader's "
             "board table (Apache-2.0), used as facts only; no code copied"],
    width=W,
    height=H,
    corner_radius=1.0,
    thickness=1.6,
    layers=4,
    planes=[("GND", "In1.Cu"), ("+3V3", "In2.Cu")],
    fanout_avoid=[FPGA_C, FT_C],
    # X1's tri-state pad joins its VDD pad by a priority route, not by a plane via of its own: in place-only run 6
    # that via's stub crossed the ground pad's via beside it
    no_fanout=["X1"],
    # U3's ground pin gets its plane via under the body (TI SLVSDG1C Figure 20) before the priority routes take
    # that space; in place-only run 7 it got none and reached the plane only through C1's via
    fanout_first=["U3"],
    fanout_pads={"X1": ["2", "4"]},
    local_footprints=["EoS_Packages"],
    rules={"via": 0.45, "drill": 0.2, "min_via": 0.45, "min_drill": 0.2,
           "track": 0.127, "clearance": 0.127, "min_clearance": 0.127},
    parts=PARTS,
    priority_routes=PRIORITY,
    # no other signal on the bottom layer under the FT2232H's oscillator or the FPGA's (BENCH-READY D6)
    router_keepouts=[(14.6, 18.8, 18.2, 22.4, "B.Cu"), (52.6, 18.6, 56.4, 22.4, "B.Cu"),
                     # no bottom-layer copper round the EXT ESD array, so each EXT line reaches it on the top layer
                     # from its own side (header left, resistor right): in place-only run 15 EXT0_P's header-side
                     # route crossed the array's no-connect pad and dropped to the bottom layer beside it
                     (24.6, 7.0, 28.4, 10.6, "B.Cu")],
    power_nets={"GND": "power:GND", "+3V3": "power:+3V3", "+1V2": "power:+1V2", "+1V8": "power:+1V8", "VBUS": "power:VBUS"},
    # nets whose supply pins are fed through a passive part (fuse, link, ferrite, filter resistor) or from
    # an inductor; +1V2_LDO, +1V8 and +3V3 have a regulator or switch output pin of their own
    flagged_nets=["GND", "VBUS", "VBUS_F", "+3V3_BUCK", "+1V2", "+1V2_PLL", "+3V3_PHY"],
    headings=[((30, 35), "USB-C, ESD, CC, fuse"), ((120, 35), "5 V to 3.3 V buck, 1.2 V LDO, core link, 3.3 V load switch"),
              ((60, 135), "FT2232H: A = iceprog flash programming, B = EPU UART"), ((270, 135), "iCE40UP5K decoupling, VCCPLL filter"),
              ((270, 265), "Configuration: CRESET_B, CDONE, DONE LED, SPI pull-ups"), ((215, 280), "Supervisors: CRESET_B"),
              ((325, 35), "ESD arrays: Pmod A, Pmod B, EXT"), ((410, 135), "12 MHz oscillator"),
              ((410, 195), "Configuration flash"), ((495, 35), "LEDs"), ((545, 35), "Buttons, BOOT jumper"),
              ((385, 262), "JTAG (EPU debug, reserved)"), ((455, 245), "Pmod A (I2C + GPIO), Pmod B (SPI)"),
              ((385, 332), "EXT header"), ((40, 315), "Test points"), ((250, 345), "Mounting holes")],
    power_block=(40.64, 360.0),
    notes=[((300, 390), "EoS EPU Board, rev A. Designed by Kartikeydheer Srivastava.\n"
                       "Copyright (c) 2026 Kartikeydheer Srivastava. All rights reserved; see LICENSE.txt.\n"
                       "Values: Lattice FPGA-DS-02008-2.4, FPGA-TN-02006-2.4, FPGA-TN-02001-3.5, FPGA-TN-02052-1.4;\n"
                       "FTDI DS_FT2232H v2.6; TI SLVSDG1C, SBVS320D, SLVSDW8B, SLVSAC2G, SBVS050N, SLVSBO7O; ECS-2520MVLC;\n"
                       "Winbond W25Q128JV Rev. F;\n"
                       "Digilent Pmod Interface Specification (2020); iceprog (IceStorm) for FT2232H channel A pin roles.")],
    netclasses={
        "Power": {"track": 0.4, "clearance": 0.15},     # VBUS, the buck's switch node and output
        "Supply": {"track": 0.3, "clearance": 0.15},    # rails into SOT-23 and 0603/0402 parts
        "Fine": {"track": 0.25, "clearance": 0.15},     # supplies that enter the 0.5 mm-pitch QFN and LQFP pads
        "USB": {"track": 0.3, "clearance": 0.15},    # 55 ohm single-ended on JLC04161H-7628 (README)
    },
    net_to_class={"VBUS": "Power", "VBUS_F": "Power", "SW_3V3": "Power", "+3V3_BUCK": "Power",
                  "+1V2_LDO": "Supply", "+1V2": "Fine", "+1V2_PLL": "Fine", "+1V8": "Fine", "+3V3_PHY": "Fine",
                  "+3V3_PLLF": "Fine", "USB_DP": "USB", "USB_DM": "USB"},
)
