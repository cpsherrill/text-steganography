from __future__ import annotations

from text_steganography.core.symbol_packing import (
    pack_bits_into_symbols,
    site_bit_width,
    sites_consumed,
    total_capacity_bits,
)


def test_site_bit_width():
    assert site_bit_width(1) == 0
    assert site_bit_width(2) == 1
    assert site_bit_width(3) == 1  # power-of-two subset leaves one variant unused
    assert site_bit_width(4) == 2
    assert site_bit_width(8) == 3
    assert site_bit_width(16) == 4


def test_pack_bits_binary_sites():
    bits = [1, 0, 1, 1]
    assert pack_bits_into_symbols(bits, [1, 1, 1, 1]) == [1, 0, 1, 1]


def test_pack_bits_wide_sites():
    # two 2-bit sites consume 4 bits, MSB first
    assert pack_bits_into_symbols([1, 0, 1, 1], [2, 2]) == [0b10, 0b11]


def test_pack_bits_pads_when_stream_runs_out():
    assert pack_bits_into_symbols([1], [1, 1, 1]) == [1, 0, 0]


def test_total_capacity_bits():
    assert total_capacity_bits([1, 2, 1, 3]) == 7


def test_sites_consumed():
    assert sites_consumed([1, 1, 1, 1], 0) == 0
    assert sites_consumed([1, 1, 1, 1], 3) == 3
    assert sites_consumed([2, 2, 2], 3) == 2  # 3 bits spill into the second site
    assert sites_consumed([1, 1], 5) == 2  # more demand than capacity stops at the end
