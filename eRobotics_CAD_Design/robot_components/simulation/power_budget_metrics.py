#!/usr/bin/env python3
"""Machine-readable power-budget metrics for eServo-200 validation cases.

Wraps the component values from power_budget_sim.py and emits a single JSON
object on the last stdout line, as required by the python_control adapter.
No new engineering values are introduced: component powers, rated motor power,
and efficiency are identical to power_budget_sim.py.
"""

import json

components = {
    "STM32G474 MCU (FOC)": 0.08,
    "Lattice ECP5 FPGA": 0.5,
    "MOSFET gate driver": 0.02,
    "Current sense amp": 0.001,
    "GbE PHY (EtherCAT)": 0.18,
    "LDO regulator": 0.01,
}
total_electronics_w = round(sum(components.values()), 6)
motor_power_w = 200
efficiency = 0.95
input_power_w = motor_power_w / efficiency
bus_current_a_48v = input_power_w / 48.0

print(
    json.dumps(
        {
            "total_electronics_w": total_electronics_w,
            "motor_power_w": motor_power_w,
            "efficiency": efficiency,
            "input_power_w": round(input_power_w, 6),
            "bus_current_a_48v": round(bus_current_a_48v, 6),
        },
        sort_keys=True,
    )
)
