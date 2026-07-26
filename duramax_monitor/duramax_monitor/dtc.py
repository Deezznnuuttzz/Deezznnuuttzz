"""DTC (diagnostic trouble code) reading/clearing and freeze frame, per the
standard OBD-II spec (SAE J1979). These modes/encodings are universal.

Mode 03 - stored (confirmed) DTCs
Mode 07 - pending DTCs
Mode 0A - permanent DTCs (not clearable until conditions are met)
Mode 04 - clear all DTCs + reset readiness monitors
Mode 02 - freeze frame data (same PIDs as Mode 01, plus a frame number byte)
"""
from __future__ import annotations

from dataclasses import dataclass

from .adapter import Elm327Adapter, NoData
from .pids import STANDARD_PIDS, decode as decode_pid

_LETTER = {0b00: "P", 0b01: "C", 0b10: "B", 0b11: "U"}


@dataclass(frozen=True)
class Dtc:
    code: str  # e.g. "P0300"
    raw: bytes  # the 2 raw bytes


def decode_dtc_bytes(data: bytes) -> list[Dtc]:
    """Decode a stream of 2-byte-per-code DTC data (as returned by Mode 03/07/0A)
    into standard code strings like P0300, C0561, etc. A 0x0000 entry means
    "no code" padding and is skipped.
    """
    codes: list[Dtc] = []
    for i in range(0, len(data) - 1, 2):
        hi, lo = data[i], data[i + 1]
        if hi == 0 and lo == 0:
            continue
        letter = _LETTER[(hi >> 6) & 0b11]
        first_digit = (hi >> 4) & 0b11
        rest = f"{hi & 0x0F:01X}{lo:02X}"
        codes.append(Dtc(code=f"{letter}{first_digit}{rest}", raw=bytes([hi, lo])))
    return codes


def read_dtcs(adapter: Elm327Adapter, mode: int = 0x03) -> list[Dtc]:
    """mode: 0x03 stored, 0x07 pending, 0x0A permanent."""
    try:
        resp = adapter.query(mode)
    except NoData:
        return []
    # First byte of payload is "number of DTCs" for mode 03/07/0A responses
    # in some ELM327 firmwares, and pure DTC pairs in others; decode_dtc_bytes
    # tolerates either since a stray leading odd byte simply won't pair up
    # evenly - to be safe, try decoding from the natural start of the data.
    return decode_dtc_bytes(resp.data)


def clear_dtcs(adapter: Elm327Adapter) -> None:
    """Mode 04: clear all stored/pending DTCs AND reset all readiness
    monitors. This is a real, semi-destructive action on the vehicle -
    callers (CLI) should get explicit user confirmation before invoking
    this, since it will make emissions readiness monitors 'not ready'
    until enough drive cycles complete.
    """
    adapter.query(0x04)


@dataclass
class FreezeFrame:
    frame_number: int
    values: dict[str, float]


def read_freeze_frame(adapter: Elm327Adapter, frame_number: int = 0) -> FreezeFrame:
    """Read freeze frame data (Mode 02) for every standard PID we know how
    to decode. Freeze frame is only populated once a DTC has set; PIDs with
    no captured data will simply be absent from the result.
    """
    values: dict[str, float] = {}
    for pid, definition in STANDARD_PIDS.items():
        try:
            resp = adapter.query(0x02, pid, extra=f"{frame_number:02X}")
        except NoData:
            continue
        try:
            values[definition.name] = decode_pid(pid, resp.data)
        except (KeyError, ValueError):
            continue
    return FreezeFrame(frame_number=frame_number, values=values)
