"""ELM327 protocol layer: initialization, sending AT/OBD commands, and
assembling multi-line CAN responses into clean hex byte strings.

A 2013 GM 1/2-3/4-ton truck (LML Duramax) speaks ISO 15765-4 CAN
(11-bit ID, 500 kbps), which is ELM327 protocol number 6. We request it
explicitly instead of relying on ATSP0 auto-detect so init is fast and
deterministic.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Optional

from .transport import Transport, open_transport

log = logging.getLogger(__name__)

_NOISE_LINES = {"OK", "SEARCHING...", "STOPPED", ""}


class AdapterError(RuntimeError):
    pass


class NoData(AdapterError):
    """Raised when the ECU has no data for the requested PID."""


@dataclass
class ObdResponse:
    mode: int
    pid: int
    data: bytes
    raw: str


class Elm327Adapter:
    def __init__(self, uri: str, timeout: float = 2.0, header: Optional[str] = None):
        self.uri = uri
        self.timeout = timeout
        self.transport: Transport = open_transport(uri, timeout=timeout)
        self._lock = threading.Lock()
        self._tester_present_thread: Optional[threading.Thread] = None
        self._tester_present_stop = threading.Event()
        self._header = header

    # -- low level -------------------------------------------------------
    def _send_raw(self, cmd: str, timeout: Optional[float] = None) -> str:
        with self._lock:
            self.transport.write(cmd + "\r")
            raw = self.transport.read_until_prompt(timeout or self.timeout)
        return raw

    def send_at(self, cmd: str) -> str:
        raw = self._send_raw(cmd)
        return self._clean(raw, echo_of=cmd)

    @staticmethod
    def _clean(raw: str, echo_of: Optional[str] = None) -> str:
        lines = [ln.strip() for ln in raw.replace("\r", "\n").split("\n")]
        lines = [ln for ln in lines if ln and ln != ">"]
        if echo_of and lines and lines[0].upper() == echo_of.upper():
            lines = lines[1:]
        return "\n".join(lines)

    # -- init --------------------------------------------------------------
    def connect(self) -> None:
        """Reset and configure the adapter for a GM CAN vehicle."""
        self.send_at("ATZ")
        time.sleep(0.5)
        self.send_at("ATE0")  # echo off
        self.send_at("ATL0")  # linefeeds off
        self.send_at("ATS0")  # spaces off (we re-space ourselves when parsing)
        self.send_at("ATH1")  # headers ON - we need to know which ECU answered
        self.send_at("ATSP6")  # ISO 15765-4 CAN 11bit/500kbps (2013 GM trucks)
        if self._header:
            self.set_header(self._header)

    def set_header(self, header: str) -> None:
        """Target a specific ECU, e.g. '7E0' for the engine control module."""
        self.send_at(f"ATSH{header}")
        self._header = header

    def close(self) -> None:
        self.stop_extended_session()
        self.transport.close()

    # -- standard Mode 01/02/03/04/07 + UDS Mode 22 requests ----------------
    def query(self, mode: int, pid: Optional[int] = None, extra: str = "") -> ObdResponse:
        """Send an OBD request and return the parsed response for the FIRST
        matching frame. Raises NoData if the ECU reports nothing.

        `pid` is encoded as a single byte for the standard Mode 01/02/09
        services, or as a 16-bit identifier for UDS Mode 0x22 (GM enhanced
        PIDs), per the respective specs.
        """
        cmd = f"{mode:02X}"
        if pid is not None:
            width = 4 if mode == 0x22 else 2
            cmd += f"{pid:0{width}X}"
        cmd += extra
        raw = self._send_raw(cmd)
        cleaned = self._clean(raw, echo_of=cmd)
        return self._parse_response(cleaned, mode, pid)

    def query_hex(self, hex_cmd: str) -> str:
        """Escape hatch: send a raw hex command string (e.g. for Mode 22
        enhanced PIDs you've verified yourself) and get back the cleaned,
        header-stripped hex payload lines."""
        raw = self._send_raw(hex_cmd)
        return self._clean(raw, echo_of=hex_cmd)

    def _parse_response(self, cleaned: str, mode: int, pid: Optional[int]) -> ObdResponse:
        if not cleaned:
            raise NoData(f"No response to mode {mode:02X} pid {pid}")
        upper = cleaned.upper()
        if "NO DATA" in upper:
            raise NoData(f"ECU reported NO DATA for mode {mode:02X} pid {pid}")
        if "UNABLE TO CONNECT" in upper or "BUS INIT" in upper:
            raise AdapterError(f"Adapter/bus error: {cleaned!r}")

        response_mode = mode + 0x40
        for line in cleaned.split("\n"):
            tokens = self._tokenize(line)
            if not tokens:
                continue
            # With headers on, a line looks like: 7E8 06 41 0C 1A F8 ...
            # Strip a plausible 3-byte (11-bit) or 4-byte (29-bit) header +
            # length byte if present by scanning for the response-mode byte.
            try:
                idx = tokens.index(f"{response_mode:02X}")
            except ValueError:
                continue
            payload = tokens[idx:]
            pid_width = 2 if mode == 0x22 else 1  # UDS Mode 22 uses a 2-byte identifier
            if len(payload) < 1 + pid_width:
                continue
            if pid is not None:
                resp_pid = int("".join(payload[1 : 1 + pid_width]), 16)
            else:
                resp_pid = 0
            data = bytes(int(b, 16) for b in payload[1 + pid_width :])
            return ObdResponse(mode=mode, pid=resp_pid, data=data, raw=cleaned)
        raise AdapterError(f"Could not parse response: {cleaned!r}")

    @staticmethod
    def _tokenize(line: str) -> list[str]:
        return re.findall(r"[0-9A-Fa-f]{2}", line)

    # -- UDS extended diagnostic session (needed for GM Mode 22 PIDs) -------
    def start_extended_session(self, keepalive_interval: float = 2.0) -> None:
        """Enter UDS extended diagnostic session (service 0x10 subfunction
        0x03) and start a background tester-present (0x3E 0x00) heartbeat so
        the ECU doesn't time out of the session. Required before most GM
        enhanced (Mode 22) PIDs will respond."""
        resp = self._send_raw("1003")
        cleaned = self._clean(resp, echo_of="1003")
        if "50 03" not in cleaned.upper().replace(" ", "") and "5003" not in cleaned.upper().replace(" ", ""):
            log.warning("Extended session may not have been accepted: %r", cleaned)

        self._tester_present_stop.clear()

        def _heartbeat():
            while not self._tester_present_stop.wait(keepalive_interval):
                try:
                    self._send_raw("3E00", timeout=1.0)
                except Exception:
                    pass

        self._tester_present_thread = threading.Thread(target=_heartbeat, daemon=True)
        self._tester_present_thread.start()

    def stop_extended_session(self) -> None:
        self._tester_present_stop.set()
        if self._tester_present_thread:
            self._tester_present_thread.join(timeout=1.0)
            self._tester_present_thread = None
