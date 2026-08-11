from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from text_steganography.core.bits import (
    bits_to_bytes,
    bits_to_int,
    bytes_to_bits,
    int_to_bits,
)


def test_bytes_to_bits_is_msb_first():
    assert bytes_to_bits(b"\x01") == [0, 0, 0, 0, 0, 0, 0, 1]
    assert bytes_to_bits(b"\x80") == [1, 0, 0, 0, 0, 0, 0, 0]
    assert bytes_to_bits(b"\xa5") == [1, 0, 1, 0, 0, 1, 0, 1]


@given(st.binary(max_size=64))
def test_bytes_bits_round_trip(data: bytes):
    assert bits_to_bytes(bytes_to_bits(data)) == data


def test_bits_to_bytes_rejects_ragged_input():
    with pytest.raises(ValueError):
        bits_to_bytes([1, 0, 1])


def test_int_to_bits_examples():
    assert int_to_bits(0, 3) == [0, 0, 0]
    assert int_to_bits(5, 3) == [1, 0, 1]
    assert int_to_bits(1, 1) == [1]


def test_int_to_bits_rejects_overflow_and_negative():
    with pytest.raises(ValueError):
        int_to_bits(4, 2)
    with pytest.raises(ValueError):
        int_to_bits(-1, 4)


@given(st.integers(min_value=0, max_value=2**16 - 1))
def test_int_bits_round_trip(value: int):
    width = max(1, value.bit_length())
    assert bits_to_int(int_to_bits(value, width)) == value
