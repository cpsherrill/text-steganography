from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from text_steganography.errors import FramingError
from text_steganography.payload.framing import (
    MAGIC,
    OVERHEAD_BYTES,
    Frame,
    frame,
    framed_bit_length,
    unframe,
)


@given(st.binary(max_size=256))
def test_frame_round_trip(payload: bytes):
    parsed = unframe(frame(payload))
    assert parsed.payload == payload
    assert parsed.integrity_valid is True
    assert parsed.version == 1


def test_frame_overhead_is_nine_bytes():
    assert len(frame(b"")) == OVERHEAD_BYTES
    assert framed_bit_length(0) == OVERHEAD_BYTES * 8
    assert framed_bit_length(3) == (OVERHEAD_BYTES + 3) * 8


def test_frame_starts_with_magic():
    assert frame(b"hi").startswith(MAGIC)


def test_unframe_detects_corruption_without_raising():
    good = bytearray(frame(b"payload"))
    good[OVERHEAD_BYTES] ^= 0xFF  # flip a payload byte, leaving the CRC stale
    parsed = unframe(bytes(good))
    assert parsed.integrity_valid is False


def test_unframe_rejects_short_buffer():
    with pytest.raises(FramingError):
        unframe(b"\x00\x01\x02")


def test_unframe_rejects_bad_magic():
    buffer = bytearray(frame(b"data"))
    buffer[0] ^= 0xFF
    with pytest.raises(FramingError):
        unframe(bytes(buffer))


def test_unframe_rejects_truncation():
    full = frame(b"a longer payload")
    with pytest.raises(FramingError):
        unframe(full[:-2])  # drop part of the CRC trailer
