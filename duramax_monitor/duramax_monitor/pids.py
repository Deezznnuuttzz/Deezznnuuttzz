"""Standard (SAE J1979 / Mode 01) OBD-II PID definitions.

These are part of the public OBD-II standard, so unlike GM's proprietary
enhanced PIDs (see enhanced_pids.py) the PID numbers and scaling formulas
here are universal across manufacturers/model years and safe to trust as-is.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Pid:
    pid: int
    name: str
    unit: str
    min_bytes: int
    decode: Callable[[bytes], float]
    description: str = ""


def _u8(data: bytes) -> int:
    return data[0]


def _u16(data: bytes) -> int:
    return (data[0] << 8) | data[1]


STANDARD_PIDS: dict[int, Pid] = {
    0x04: Pid(0x04, "engine_load", "%", 1, lambda d: _u8(d) * 100 / 255, "Calculated engine load"),
    0x05: Pid(0x05, "coolant_temp", "C", 1, lambda d: _u8(d) - 40, "Engine coolant temperature"),
    0x0A: Pid(0x0A, "fuel_pressure", "kPa", 1, lambda d: _u8(d) * 3, "Fuel pressure (gauge)"),
    0x0B: Pid(0x0B, "intake_map", "kPa", 1, lambda d: _u8(d), "Intake manifold absolute pressure"),
    0x0C: Pid(0x0C, "rpm", "rpm", 2, lambda d: _u16(d) / 4, "Engine RPM"),
    0x0D: Pid(0x0D, "speed", "km/h", 1, lambda d: _u8(d), "Vehicle speed"),
    0x0E: Pid(0x0E, "timing_advance", "deg", 1, lambda d: (_u8(d) - 128) / 2, "Timing advance"),
    0x0F: Pid(0x0F, "intake_air_temp", "C", 1, lambda d: _u8(d) - 40, "Intake air temperature"),
    0x10: Pid(0x10, "maf", "g/s", 2, lambda d: _u16(d) / 100, "Mass air flow rate"),
    0x11: Pid(0x11, "throttle_pos", "%", 1, lambda d: _u8(d) * 100 / 255, "Throttle position"),
    0x1F: Pid(0x1F, "run_time", "s", 2, lambda d: _u16(d), "Run time since engine start"),
    0x21: Pid(0x21, "distance_mil", "km", 2, lambda d: _u16(d), "Distance traveled with MIL on"),
    0x2F: Pid(0x2F, "fuel_level", "%", 1, lambda d: _u8(d) * 100 / 255, "Fuel tank level input"),
    0x31: Pid(0x31, "distance_clear", "km", 2, lambda d: _u16(d), "Distance since codes cleared"),
    0x33: Pid(0x33, "baro_pressure", "kPa", 1, lambda d: _u8(d), "Barometric pressure"),
    0x3C: Pid(0x3C, "cat_temp_b1s1", "C", 2, lambda d: _u16(d) / 10 - 40, "Catalyst temp bank1 sensor1"),
    0x42: Pid(0x42, "control_module_voltage", "V", 2, lambda d: _u16(d) / 1000, "Control module voltage"),
    0x43: Pid(0x43, "absolute_load", "%", 2, lambda d: _u16(d) * 100 / 255, "Absolute load value"),
    0x46: Pid(0x46, "ambient_air_temp", "C", 1, lambda d: _u8(d) - 40, "Ambient air temperature"),
    0x5C: Pid(0x5C, "engine_oil_temp", "C", 1, lambda d: _u8(d) - 40, "Engine oil temperature"),
    0x5E: Pid(0x5E, "fuel_rate", "L/h", 2, lambda d: _u16(d) / 20, "Engine fuel rate"),
}


def decode(pid: int, data: bytes) -> float:
    definition = STANDARD_PIDS.get(pid)
    if definition is None:
        raise KeyError(f"No standard PID definition for 0x{pid:02X}")
    if len(data) < definition.min_bytes:
        raise ValueError(
            f"PID 0x{pid:02X} ({definition.name}) expected >= {definition.min_bytes} "
            f"bytes, got {len(data)}: {data.hex()}"
        )
    return definition.decode(data)


def supported_pids_from_bitmask(data: bytes, base_pid: int) -> list[int]:
    """Decode the response to PID 0x00/0x20/0x40/... (a 4-byte bitmask of
    which of the next 32 PIDs are supported) into a list of PID numbers."""
    if len(data) < 4:
        raise ValueError(f"Expected 4 bytes for supported-PID bitmask, got {data.hex()}")
    value = int.from_bytes(data[:4], "big")
    supported = []
    for i in range(32):
        if value & (1 << (31 - i)):
            supported.append(base_pid + i + 1)
    return supported
