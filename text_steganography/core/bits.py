"""Bit-level helpers.

Bits are represented as plain lists of ``0`` and ``1`` ints. Within a byte and
within an integer field the convention is most-significant-bit first, so the
on-the-wire order matches how the numbers read on paper.
"""

from __future__ import annotations

from typing import List, Sequence


def bytes_to_bits(data: bytes) -> List[int]:
    """Expand bytes to a flat MSB-first bit list."""
    bits: List[int] = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits


def bits_to_bytes(bits: Sequence[int]) -> bytes:
    """Pack an MSB-first bit list back into bytes.

    The length must be a multiple of eight.
    """
    if len(bits) % 8 != 0:
        raise ValueError(f"bit count {len(bits)} is not a multiple of 8")
    out = bytearray()
    for i in range(0, len(bits), 8):
        value = 0
        for j in range(8):
            value = (value << 1) | (bits[i + j] & 1)
        out.append(value)
    return bytes(out)


def int_to_bits(value: int, width: int) -> List[int]:
    """Represent a non-negative integer as ``width`` MSB-first bits."""
    if value < 0:
        raise ValueError("value must be non-negative")
    if width < 0:
        raise ValueError("width must be non-negative")
    if value >= (1 << width):
        raise ValueError(f"value {value} does not fit in {width} bits")
    return [(value >> shift) & 1 for shift in range(width - 1, -1, -1)]


def bits_to_int(bits: Sequence[int]) -> int:
    """Interpret an MSB-first bit list as a non-negative integer."""
    value = 0
    for bit in bits:
        value = (value << 1) | (bit & 1)
    return value
