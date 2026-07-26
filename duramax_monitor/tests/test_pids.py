from duramax_monitor.pids import STANDARD_PIDS, decode, supported_pids_from_bitmask


def test_rpm_decode():
    # 0x1AF8 / 4 = 1726.0
    assert decode(0x0C, bytes([0x1A, 0xF8])) == 1726.0


def test_coolant_temp_decode():
    assert decode(0x05, bytes([0x7B])) == 83  # 123 - 40


def test_speed_decode():
    assert decode(0x0D, bytes([0x50])) == 80


def test_voltage_decode():
    # 0x355C = 13660 -> 13.66V
    value = decode(0x42, bytes([0x35, 0x5C]))
    assert abs(value - 13.66) < 1e-9


def test_fuel_level_decode():
    assert abs(decode(0x2F, bytes([0xC8])) - (200 * 100 / 255)) < 1e-9


def test_decode_unknown_pid_raises():
    try:
        decode(0x9999, bytes([0x00]))
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_decode_insufficient_bytes_raises():
    try:
        decode(0x0C, bytes([0x1A]))  # rpm needs 2 bytes
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_supported_pids_bitmask():
    # bitmask 0xFFFFFFFF -> all 32 PIDs after base supported
    data = bytes([0xFF, 0xFF, 0xFF, 0xFF])
    supported = supported_pids_from_bitmask(data, base_pid=0x00)
    assert supported == list(range(1, 33))


def test_supported_pids_bitmask_partial():
    # Only the highest bit (PID 0x01) set
    data = bytes([0x80, 0x00, 0x00, 0x00])
    supported = supported_pids_from_bitmask(data, base_pid=0x00)
    assert supported == [1]


def test_every_standard_pid_has_a_name_and_unit():
    for pid, definition in STANDARD_PIDS.items():
        assert definition.pid == pid
        assert definition.name
        assert isinstance(definition.unit, str)
