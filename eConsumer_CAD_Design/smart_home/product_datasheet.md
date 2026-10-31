# Smart Home Devices — Product Datasheet
> **Revision:** v1.0 | **Date:** 2026-06-03 | **Status:** Design Phase

## Product Family

| Model | Type | Protocol | Standard |
|---|---|---|---|
| eHub-Pro | Smart home hub | Matter, Zigbee, Z-Wave, BLE | Matter 1.6.1 (target) |
| eThermostat | Smart thermostat | Wi-Fi, BLE | ENERGY STAR |
| eDoorbell | Video doorbell | Wi-Fi 6, BLE | FCC Part 15 |
| eCamera-Home | Indoor security camera | Wi-Fi 6 | FCC Part 15 |
| eSpeaker-AI | AI smart speaker | Wi-Fi 6, BLE | FCC Part 15 |

> Target versions (2026-10-30): Matter 1.6.1 and Thread 1.4 are design targets, not shipped stacks. See eNet's home-systems plan (target lock 2026-10-30, Refs eNet#7) and the eHub-Pro use-case spec (docs/ehub-pro-spec.md in eNet) for the system design. Zigbee 3.0 / Z-Wave 700 rows are unchanged datasheet facts, not stack commitments.

## Electrical Specifications — eHub-Pro
| Parameter | Specification |
|---|---|
| **CPU** | NXP i.MX 8M Mini (quad Cortex-A53) |
| **Protocols** | Matter 1.6.1 (target), Zigbee 3.0, Z-Wave 700, BLE 5.3, Wi-Fi 6, Thread 1.4 (border-router target) |
| **Memory** | 2GB LPDDR4 + 16GB eMMC |
| **Power** | 12VDC, 10W |
| **Connectivity** | GbE, USB 3.0 ×2, USB-C |
