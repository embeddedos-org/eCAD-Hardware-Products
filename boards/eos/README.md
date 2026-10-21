# EmbeddedOS development boards

Original boards designed by Kartikeydheer Srivastava, all rights reserved (see [Licence](#licence)).
Each board is written as a design file in [tools/eos_boards/boards](../../tools/eos_boards/boards). One command builds the
board's schematic, layout, routing, checks and fabrication outputs; see
[tools/eos_boards/README.md](../../tools/eos_boards/README.md).

| Board | What it is | Layers | ERC | DRC errors | Unconnected | Parity |
|---|---|---|---|---|---|---|
| [EoS Learn RP2350](eos-learn-rp2350) | RP2350A teaching board; Raspberry Pi's own core layout, reproduced to the nanometre | 4 | 0 | 0 | 0 | 0 |
| [EoS Sense Cape](eos-sense-cape) | Sensor cape for PocketBeagle; fit checked pin for pin against PocketBeagle's board file | 2 | 0 | 0 | 0 | 0 |
| [EoS Probe S3](eos-probe-s3) | ESP32-S3 SWD/JTAG + UART debug probe, 1.65–5.5 V targets | 2 | 0 | 0 | 0 | 0 |
| [EoS CM5 Base](eos-cm5-base) | Raspberry Pi CM5 carrier: USB-C power, Gigabit Ethernet, USB 2.0 host, microSD, 40-pin GPIO; connectors checked pad for pad against the CM5 | 4 | 0 | 0 | 0 | 0 |
| [EoS CM4 Base](eos-cm4-base) | Raspberry Pi CM4 carrier: USB-C power, one USB 2.0 port switched between USB-C (device) and USB-A (host), Gigabit Ethernet, microSD, 40-pin GPIO | 4 | 0 | 0 | 0 | 0 |
| [EoS Motion Wing](eos-motion-wing) | FeatherWing: ADXL343 accelerometer and ADT7410 temperature sensor on I2C, address and interrupt jumpers | 2 | 0 | 0 | 0 | 0 |
| [EoS ESP32 DevKit](eos-esp32-devkit) | ESP32-WROOM-32E board: USB-C, CP2102N USB-UART with auto-program, 3.3 V 1 A, DevKitC V4 header grid | 2 | 0 | 0 | 0 | 0 |
| [EoS ATmega328P Board](eos-atmega328p-board) | ATmega328P board that fits Uno R3 shields: USB-C, CH340C USB-UART with Ioff buffers, ICSP header | 2 | 0 | 0 | 0 | 0 |
| [EoS MSP430G2 Board](eos-msp430g2-board) | MSP430G2553 (DIP-20, socketed) board that takes 20-pin BoosterPacks; Spy-Bi-Wire header | 2 | 0 | 0 | 0 | 0 |
| [EoS TM4C123 Board](eos-tm4c123-board) | TM4C123GH6PM board that takes 40-pin BoosterPacks: USB device port, CP2102N USB-UART, SWD | 2 | 0 | 0 | 0 | 0 |
| [EoS KL25 Board](eos-kl25-board) | NXP KL25Z (MKL25Z128VLK4) board that fits Uno R3 shields: USB device port, accelerometer, SWD | 2 | 0 | 0 | 0 | 0 |
| [EoS STM32 64](eos-stm32-64) | STM32F411RE board in the 64-pin Nucleo format: morpho and Uno headers, 7-12 V buck, SWD | 2 | 0 | 0 | 0 | 0 |
| [EoS LPC55S69 Board](eos-lpc55s69-board) | NXP LPC55S69 (dual Cortex-M33) board that fits Uno R3 shields: two USB-C ports, power mux, SWD | 4 | 0 | 0 | 0 | 0 |
| [EoS KE16Z Board](eos-ke16z-board) | NXP KE16Z (MKE16Z64VLF4) board that fits Uno R3 shields: CP2102N USB-UART, CAN pins, SWD | 2 | 0 | 0 | 0 | 0 |
| [EoS RA2E1 Board](eos-ra2e1-board) | Renesas RA2E1 board that fits Uno R3 shields: two Pmod headers, CP2102N on the boot UART, SWD | 2 | 0 | 0 | 0 | 0 |
| [EoS F280049C Board](eos-f280049c-board) | TI TMS320F280049C (C2000) board with two 40-pin BoosterPack sites, four layers: CP2102N USB-UART, JTAG | 4 | 0 | 0 | 0 | 0 |
| [EoS RA4M2 Board](eos-ra4m2-board) | Renesas RA4M2 board that fits Uno R3 shields: SPI and I2C Pmod ports, 40-pin GPIO header, USB device, CP2102N, SWD | 2 | 0 | 0 | 0 | 0 |
| [EoS RL78G13 Board](eos-rl78g13-board) | Renesas RL78/G13 (R5F100LEAFB) stick board: two 30-pin headers 25.4 mm apart, USB-C serial port, TOOL0 debug | 2 | 0 | 0 | 0 | 0 |
| [EoS TM4C1294 Board](eos-tm4c1294-board) | TI TM4C1294NCPDT board with two 40-pin BoosterPack sites, a 98-hole breakout and 10/100 Ethernet, six layers: USB device port, CP2102N USB-UART, SWD/JTAG | 6 | 0 | 0 | 0 | 0 |

Each board folder contains:

- the KiCad project;
- Gerbers and drill files;
- BOM and pick-and-place files;
- a STEP model;
- the schematic as a PDF;
- renders;
- `build-report.json`, which records the check counts.

The KiCad projects open in KiCad 10 or later; the boards are saved in KiCad 10's format.
The Gerbers, drill files, BOM, STEP and PDF need no KiCad at all.

None of these boards has been manufactured or tested on the bench. Each README says what was
checked and what was not.

## Licence

These boards are **not open source**, and they are **not** under the MIT licence that
covers this repository's own code. They are Copyright (c) 2026 Kartikeydheer Srivastava, all
rights reserved. Each board's `LICENSE.txt` has the full terms. In short:

- **Anyone** may view them, download or clone this repository, open the files to look at them
  and run its tests. Copying or changing the designs, making boards from them or selling them
  needs Kartikeydheer Srivastava's written permission, which may be given for a fee. To ask,
  write to kartikeydheer@gmail.com.
- **EmbeddedOS (EoS) Research Foundation** may, free of charge, publish them and its own
  changed versions for viewing, change them for its own projects, and make and lend boards for
  its own development, research, teaching and demonstrations. It may not sell boards or pass
  the designs on. Kartikeydheer Srivastava can withdraw this permission with 30 days' notice
  by email or letter.
- **Third-party material** keeps its own licence: Raspberry Pi's RP2350A core layout (MIT) on
  EoS Learn RP2350, and footprints, symbols and 3D models from KiCad's libraries. Each board's
  `LICENSE.txt` lists what it uses.

What the licence covers:

- every board folder here, except the generic libraries copied into a board's
  `hardware/symbols/` and `hardware/footprints/EoS_Packages.pretty`, which are MIT like the
  generator that writes them;
- in `tools/eos_boards`: the boards' design files `boards/eos_*.py`, `boards/owner.py`, the
  licence terms `boards/licence_terms.txt`, and the footprint library drawn for the module
  carriers, `footprints/EoS_Connectors.pretty`.

The rest of `tools/eos_boards` (the generator, the reference extractors, `symbols/` and
`footprints/generate.py` with the `EoS_Packages.pretty` it writes) and its tests stay under the
repository's MIT licence.
