from duramax_monitor.dtc import decode_dtc_bytes


def test_p0300_random_misfire():
    # P0300: letter=P (00), first digit=0, rest=300
    # byte layout: hi = 00 000011 -> wait, encode manually via known mapping
    # P (00) with first_digit=3 -> hi upper 2 bits=00, next 2 bits=first digit(3)=11
    # hi = 0b00_11_0000 = 0x30, lo = 0x00 -> code "P3" + "000"? Let's verify via round trip instead.
    hi, lo = 0x03, 0x00
    codes = decode_dtc_bytes(bytes([hi, lo]))
    assert len(codes) == 1
    assert codes[0].code == "P0300"


def test_c1561_example():
    # C (01) first_digit=1 -> hi = 01_01_0101 = 0x55, rest = 0x61 -> "561"
    hi, lo = 0x55, 0x61
    codes = decode_dtc_bytes(bytes([hi, lo]))
    assert codes[0].code == "C1561"


def test_u_code():
    # U (11) first_digit=0 -> hi = 11_00_0001 = 0xC1
    hi, lo = 0xC1, 0x23
    codes = decode_dtc_bytes(bytes([hi, lo]))
    assert codes[0].code == "U0123"


def test_zero_padding_skipped():
    codes = decode_dtc_bytes(bytes([0x03, 0x00, 0x00, 0x00, 0x55, 0x61]))
    assert [c.code for c in codes] == ["P0300", "C1561"]


def test_empty_data():
    assert decode_dtc_bytes(b"") == []
