"""Mode 22 PID sweep tool: helps you safely identify real enhanced PIDs on
your own truck instead of trusting unverified numbers from the internet.

Sends 0x22 requests for a range of candidate 16-bit local identifiers and
records the raw hex payload for each one that responds. It is read-only -
Mode 22 is a diagnostic *read* service, so this cannot command an actuator
or change ECU configuration. Still, sweeping many PIDs quickly can be
chatty on the bus, so this defaults to a conservative delay between
requests and is meant to be run with the engine idling/parked, not while
driving.

Workflow:
  1. Run a sweep and save the results to a CSV.
  2. Note which PIDs respond and with how many bytes.
  3. Change a known real-world condition (e.g. rev the engine, or watch the
     factory trans-temp gauge climb) and re-sweep - PIDs whose values move
     in a way that correlates with that change are good candidates for
     what you think they are.
  4. Only then add a verified entry to enhanced_pids.py / config.yaml.
"""
from __future__ import annotations

import csv
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from .adapter import Elm327Adapter, AdapterError, NoData

log = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    pid: int
    raw_bytes: bytes


def sweep(
    adapter: Elm327Adapter,
    start: int = 0x0000,
    end: int = 0xFFFF,
    delay: float = 0.05,
    on_progress=None,
) -> list[DiscoveryResult]:
    """Sweep Mode 22 PIDs in [start, end] inclusive. Returns only PIDs that
    produced a response (not NO DATA / error)."""
    results: list[DiscoveryResult] = []
    adapter.start_extended_session()
    try:
        for pid in range(start, end + 1):
            try:
                resp = adapter.query(0x22, pid)
                results.append(DiscoveryResult(pid=pid, raw_bytes=resp.data))
            except NoData:
                pass
            except AdapterError as exc:
                log.debug("PID 0x%04X errored: %s", pid, exc)
            if on_progress:
                on_progress(pid, len(results))
            time.sleep(delay)
    finally:
        adapter.stop_extended_session()
    return results


def write_results_csv(results: list[DiscoveryResult], path: str | Path) -> None:
    path = Path(path)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["pid_hex", "num_bytes", "raw_hex", "raw_as_uint_be"])
        for r in results:
            as_uint = int.from_bytes(r.raw_bytes, "big") if r.raw_bytes else ""
            writer.writerow([f"0x{r.pid:04X}", len(r.raw_bytes), r.raw_bytes.hex(), as_uint])
