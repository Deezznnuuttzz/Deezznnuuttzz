"""GM 'enhanced' (UDS Mode 22) PIDs for boost, EGT, transmission temp,
DPF/DEF, etc. on the 2013 Duramax LML.

IMPORTANT - read before you fill this in
=========================================
Unlike the Mode 01 PIDs in pids.py, these are NOT part of the public OBD-II
standard. They are manufacturer-specific 16-bit "Local Identifiers" that
vary by ECU calibration, and the byte-scaling formula for each one is
whatever GM's engineers chose. There is no single authoritative public list
we can safely hardcode here: values circulated in enthusiast forums/Torque
plugins are frequently calibration-specific, sometimes wrong, and get
attributed to the wrong PID number.

This module intentionally ships EMPTY of guessed values. Do not add an
entry here unless you've verified it yourself, e.g. by:
  1. Using the `discover` CLI command (see discovery.py) to sweep a range
     of Mode 22 PIDs on your actual truck and log the raw responses.
  2. Cross-referencing candidate PIDs against a second source you trust
     (a licensed EFILive/HP Tuners PID database, your adapter vendor's own
     GM-specific PID list, etc.) - don't trust a single forum post.
  3. Confirming the decoded value against a known-good reference at the
     same moment (e.g. the factory Driver Information Center trans-temp
     readout, a physical boost gauge, a second scan tool) before you rely
     on it for anything that matters (e.g. towing EGT limits).

Once verified, add entries to ENHANCED_PIDS below, e.g.:

    ENHANCED_PIDS[0x1234] = EnhancedPid(
        pid=0x1234,
        name="turbo_boost",
        unit="kPa",
        decode=lambda d: (d[0] << 8 | d[1]) * 0.1 - 100,
        description="Verified against a mechanical boost gauge on 2026-01-01",
    )

Also usable via config.yaml (see config.example.yaml) so you don't have to
edit source to add PIDs you've discovered.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# GM engine ECUs generally require an extended UDS diagnostic session
# (service 0x10 subfunction 0x03) before they'll answer Mode 22 requests;
# see Elm327Adapter.start_extended_session(). The ECU is usually addressed
# directly (header 7E0 request / 7E8 response) rather than the functional
# broadcast address (7DF) used for standard Mode 01 PIDs.
ENGINE_ECU_HEADER = "7E0"


@dataclass(frozen=True)
class EnhancedPid:
    pid: int  # 16-bit Mode 22 local identifier
    name: str
    unit: str
    decode: Callable[[bytes], float]
    description: str = ""


# Deliberately empty - see module docstring. Populate from your own
# verified findings or via config.yaml's `enhanced_pids:` section.
ENHANCED_PIDS: dict[int, EnhancedPid] = {}


def load_from_config(entries: list[dict]) -> dict[int, EnhancedPid]:
    """Build an ENHANCED_PIDS-style dict from config.yaml entries of the form:

        enhanced_pids:
          - pid: 0x1234
            name: turbo_boost
            unit: kPa
            formula: "(b[0] << 8 | b[1]) * 0.1 - 100"

    `formula` is evaluated with `b` bound to the response bytes (a `bytes`
    object). Only basic arithmetic on `b` is expected; this is a convenience
    for pasting in values you've already verified, not a general scripting
    interface.
    """
    result: dict[int, EnhancedPid] = {}
    for entry in entries:
        pid = entry["pid"] if isinstance(entry["pid"], int) else int(entry["pid"], 0)
        formula = entry["formula"]

        def make_decoder(expr: str) -> Callable[[bytes], float]:
            code = compile(expr, "<enhanced_pid_formula>", "eval")

            def _decode(b: bytes) -> float:
                return eval(code, {"__builtins__": {}}, {"b": b})

            return _decode

        result[pid] = EnhancedPid(
            pid=pid,
            name=entry["name"],
            unit=entry.get("unit", ""),
            decode=make_decoder(formula),
            description=entry.get("description", ""),
        )
    return result
