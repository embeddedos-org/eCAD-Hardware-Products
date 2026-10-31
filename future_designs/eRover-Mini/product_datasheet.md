# 🚙 eRover-Mini — Concept Datasheet

> **Status:** Concept (chassis CAD + EoSim ROS-2 sim bridge landed; on-device micro-ROS path TBD)
> **Category:** Robotics, Education, Research
> **EmbeddedOS components:** eos (kernel + drivers), eAI (SLAM + object detection), EoSim (ROS-2 sim bridge), eNI (robot nodes), ebuild (cross-compile)
> **Note:** eIPC carries no ROS-2 role in the code (verified 2026-10-29: no `ros2`, `cmd_vel`, or `odom` hits in eIPC; the single `rcl` hit is a CSS file). Its transport role, if any, is unassigned.

## Tagline

$400 open-source autonomous research rover (TurtleBot alternative).

## Why this exists (donor pitch)

A TurtleBot 4 costs $3 K. eRover-Mini delivers comparable autonomy (SLAM + ROS-2 bridge + camera + LIDAR) for under $400, putting real mobile-robot research within reach of any teaching university or maker-space. One bench seats five rovers for the price of one commercial unit.

## Target users

Robotics students, teaching faculty, hackerspaces, after-school robotics clubs.

## Suggested donor tier

$2 K — equip a university robotics lab with 5 rovers for one term.

## Hardware sketch

- Raspberry Pi Compute Module 5 (host) + carrier PCB
- STM32G474 motion controller (motor PID + IMU integration)
- 4× 12 V DC motors + dual H-bridge driver (DRV8874)
- RPLIDAR A1M8 360° 2D LIDAR
- BNO086 9-DOF IMU
- IMX708 12 MP camera (Pi Camera Module 3)
- 7.4 V / 5200 mAh Li-ion + USB-C PD
- 3D-printed PETG chassis (open STEP file)

## EmbeddedOS stack

- eos (kernel + drivers)
- eAI (SLAM + object detection)
- EoSim (ROS-2 sim bridge, cmd_vel/odom)
- ebuild (cross-compile)

## BOM target

~$400

> Full BOM placeholder lives at [`bom.csv`](bom.csv). Schematics will be
> added under `kicad/` when the design graduates from concept to draft.

## Status

This page is a **concept-stage placeholder**. It exists so that donors,
contributors, and curators can browse the design as a real GitHub URL
before any silicon is committed.

To take this design to draft:

1. Open an issue on
   [embeddedos-org/eCAD-Hardware-Products](https://github.com/embeddedos-org/eCAD-Hardware-Products/issues/new)
   titled `[future_designs/eRover-Mini] graduate to draft`.
2. Stand up `kicad/erover_mini_schematic.kicad_sch` and start filling in
   the BOM at [`bom.csv`](bom.csv).
3. Cross-reference the eFab manifest if a curated stack profile makes
   sense (e.g. `eai-edge` for designs that lean on ENI + EIPC + eAI).

See the org-wide guide at
[`embeddedos-org/.github/CONTRIBUTING.md`](https://github.com/embeddedos-org/.github/blob/main/CONTRIBUTING.md).
