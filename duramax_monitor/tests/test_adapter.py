from duramax_monitor.adapter import Elm327Adapter
from duramax_monitor.transport import Transport


class ScriptedTransport(Transport):
    """Replays canned responses keyed by the exact command sent."""

    def __init__(self, script: dict[str, str]):
        self.script = script
        self.sent: list[str] = []
        self._last = ""

    def write(self, data: str) -> None:
        cmd = data.strip()
        self.sent.append(cmd)
        self._last = cmd

    def read_until_prompt(self, timeout: float) -> str:
        return self.script.get(self._last, "NO DATA") + "\r>"

    def close(self) -> None:
        pass


def _adapter_with(script: dict[str, str]) -> Elm327Adapter:
    adapter = Elm327Adapter.__new__(Elm327Adapter)  # bypass open_transport()
    adapter.uri = "test://"
    adapter.timeout = 1.0
    adapter.transport = ScriptedTransport(script)
    import threading

    adapter._lock = threading.Lock()
    adapter._tester_present_thread = None
    adapter._tester_present_stop = threading.Event()
    adapter._header = None
    return adapter


def test_query_rpm_with_headers():
    adapter = _adapter_with({"010C": "7E8 04 41 0C 1A F8"})
    resp = adapter.query(0x01, 0x0C)
    assert resp.data == bytes([0x1A, 0xF8])
    assert resp.pid == 0x0C


def test_query_no_headers():
    adapter = _adapter_with({"0105": "41 05 7B"})
    resp = adapter.query(0x01, 0x05)
    assert resp.data == bytes([0x7B])


def test_query_no_data_raises():
    from duramax_monitor.adapter import NoData

    adapter = _adapter_with({"010C": "NO DATA"})
    try:
        adapter.query(0x01, 0x0C)
        assert False, "expected NoData"
    except NoData:
        pass


def test_query_multiline_takes_first_matching_line():
    # If multiple lines come back (e.g. more than one ECU answers a
    # broadcast request), we take the first well-formed match.
    adapter = _adapter_with({"010C": "7E8 04 41 0C 1A F8\n7E9 04 41 0C 00 00"})
    resp = adapter.query(0x01, 0x0C)
    assert resp.data == bytes([0x1A, 0xF8])


def test_mode22_two_byte_pid_and_response():
    # UDS Mode 22 uses a 2-byte identifier; response echoes pid_hi, pid_lo
    # then data bytes - make sure they aren't mixed up.
    adapter = _adapter_with({"221234": "7E8 05 62 12 34 AA BB"})
    resp = adapter.query(0x22, 0x1234)
    assert resp.pid == 0x1234
    assert resp.data == bytes([0xAA, 0xBB])
