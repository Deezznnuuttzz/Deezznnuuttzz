"""Transport layer for talking to an ELM327-compatible OBD-II adapter.

Supports three transports:
  * serial://  - USB or Bluetooth-SPP adapter exposed as a serial port
                 (e.g. /dev/ttyUSB0, /dev/rfcomm0, COM5)
  * socket://  - WiFi ELM327 adapters that expose a raw TCP socket
                 (typically host 192.168.0.10 port 35000)
  * sim://     - built-in simulator, no hardware required. Useful for
                 developing/testing the rest of the pipeline (dashboard,
                 logging, alerts, CLI) before you're plugged into the truck.

All transports implement the same tiny interface: write(str) and
read_until_prompt() -> str, so the ELM327 protocol layer in adapter.py
doesn't need to know which one it's using.
"""
from __future__ import annotations

import random
import socket
import time
from abc import ABC, abstractmethod


class TransportError(RuntimeError):
    pass


class Transport(ABC):
    @abstractmethod
    def write(self, data: str) -> None:
        ...

    @abstractmethod
    def read_until_prompt(self, timeout: float) -> str:
        """Read until the ELM327 '>' prompt (end of response) or timeout."""

    def close(self) -> None:
        pass


class SerialTransport(Transport):
    def __init__(self, port: str, baudrate: int = 38400, timeout: float = 2.0):
        import serial  # pyserial; imported lazily so sim/socket modes don't need it

        self._ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)

    def write(self, data: str) -> None:
        self._ser.write(data.encode("ascii", errors="ignore"))

    def read_until_prompt(self, timeout: float) -> str:
        self._ser.timeout = timeout
        deadline = time.monotonic() + timeout
        buf = bytearray()
        while time.monotonic() < deadline:
            chunk = self._ser.read(1)
            if not chunk:
                continue
            buf += chunk
            if buf.endswith(b">"):
                break
        return buf.decode("ascii", errors="ignore")

    def close(self) -> None:
        try:
            self._ser.close()
        except Exception:
            pass


class SocketTransport(Transport):
    def __init__(self, host: str, port: int = 35000, timeout: float = 2.0):
        self._sock = socket.create_connection((host, port), timeout=timeout)
        self._sock.settimeout(timeout)

    def write(self, data: str) -> None:
        self._sock.sendall(data.encode("ascii", errors="ignore"))

    def read_until_prompt(self, timeout: float) -> str:
        self._sock.settimeout(timeout)
        deadline = time.monotonic() + timeout
        buf = bytearray()
        while time.monotonic() < deadline:
            try:
                chunk = self._sock.recv(256)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
            if buf.endswith(b">"):
                break
        return buf.decode("ascii", errors="ignore")

    def close(self) -> None:
        try:
            self._sock.close()
        except Exception:
            pass


class SimulatedTransport(Transport):
    """Fakes an ELM327 + a running Duramax so the rest of the app can be
    exercised without a truck or adapter plugged in.

    Only understands the small set of AT/OBD commands the adapter layer
    actually sends, and only for the standard Mode 01 PIDs (the ones this
    project ships verified formulas for). Anything else gets NO DATA, same
    as a real adapter would return for an unsupported PID.
    """

    def __init__(self, *_args, **_kwargs):
        self._t0 = time.monotonic()
        self._echo = True
        self._headers = False

    def write(self, data: str) -> None:
        self._last_cmd = data.strip().upper()

    def read_until_prompt(self, timeout: float) -> str:
        cmd = getattr(self, "_last_cmd", "")
        resp = self._handle(cmd)
        return resp + "\r>"

    def _handle(self, cmd: str) -> str:
        if cmd.startswith("AT"):
            if cmd == "ATZ":
                return "ELM327 v2.1 (SIMULATED)"
            if cmd == "ATE0":
                self._echo = False
                return "OK"
            if cmd == "ATH1":
                self._headers = True
                return "OK"
            if cmd.startswith("AT"):
                return "OK"
        if cmd.startswith("01"):
            pid = cmd[2:4]
            return self._mode01(pid)
        if cmd.startswith("03"):
            return "43 01 03 00"  # fake stored DTC: P0300
        if cmd.startswith("07"):
            return "NO DATA"
        if cmd.startswith("04"):
            return "44"
        return "NO DATA"

    def _mode01(self, pid: str) -> str:
        t = time.monotonic() - self._t0
        rpm = int(750 + 400 * max(0, __import__("math").sin(t / 3)))
        speed = int(max(0, 40 + 30 * __import__("math").sin(t / 10)))
        coolant = min(96, 20 + t * 2)  # warms up to ~96C then holds
        if pid == "00":
            return "41 00 BE 1F A8 13"  # supported PID bitmask (fake)
        if pid == "05":
            return f"41 05 {int(coolant) + 40:02X}"
        if pid == "0C":
            val = rpm * 4
            return f"41 0C {(val >> 8) & 0xFF:02X} {val & 0xFF:02X}"
        if pid == "0D":
            return f"41 0D {speed & 0xFF:02X}"
        if pid == "0F":
            return "41 0F 46"  # intake air temp
        if pid == "11":
            return "41 11 32"  # throttle position
        if pid == "2F":
            return "41 2F C8"  # fuel level
        if pid == "42":
            return "41 42 35 5C"  # control module voltage ~13.7V
        return "NO DATA"

    def close(self) -> None:
        pass


def open_transport(uri: str, timeout: float = 2.0) -> Transport:
    """Create the right Transport from a connection URI string.

    Examples: 'serial:///dev/ttyUSB0', 'serial://COM5', 'socket://192.168.0.10:35000',
    'sim://'
    """
    if uri.startswith("sim://"):
        return SimulatedTransport()
    if uri.startswith("serial://"):
        port = uri[len("serial://") :]
        return SerialTransport(port, timeout=timeout)
    if uri.startswith("socket://"):
        rest = uri[len("socket://") :]
        if ":" in rest:
            host, port_s = rest.split(":", 1)
            port = int(port_s)
        else:
            host, port = rest, 35000
        return SocketTransport(host, port, timeout=timeout)
    raise TransportError(
        f"Unrecognized connection URI {uri!r}. Use serial://<port>, "
        "socket://<host>:<port>, or sim:// for the simulator."
    )
