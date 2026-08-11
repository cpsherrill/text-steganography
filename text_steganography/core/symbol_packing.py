"""Power-of-two symbol packing.

A site with ``m`` variants can carry ``floor(log2(m))`` bits by using only the
largest power-of-two subset of its variants. A site with two variants carries
one bit, four carries two, eight carries three; a three-variant site carries
one bit and leaves a variant unused. This is the simple, easy-to-reason-about
packing mode. Denser mixed-radix packing is left for a later phase.
"""

from __future__ import annotations

from typing import List, Sequence

from .bits import bits_to_int


def site_bit_width(radix: int) -> int:
    """Number of whole bits a site of the given radix carries."""
    if radix < 2:
        return 0
    return radix.bit_length() - 1


def total_capacity_bits(widths: Sequence[int]) -> int:
    """Sum of per-site bit widths."""
    return sum(widths)


def pack_bits_into_symbols(bits: Sequence[int], widths: Sequence[int]) -> List[int]:
    """Map a bit stream onto one symbol per site.

    Bits are consumed most-significant-first in ``widths`` order. When the bit
    stream runs out, remaining sites take symbol ``0``, which every channel
    treats as its canonical (unchanged) form, so unused sites leave no trace.
    """
    symbols: List[int] = []
    pos = 0
    for width in widths:
        if width == 0:
            symbols.append(0)
            continue
        chunk = list(bits[pos : pos + width])
        if len(chunk) < width:
            chunk += [0] * (width - len(chunk))
        symbols.append(bits_to_int(chunk))
        pos += width
    return symbols


def sites_consumed(widths: Sequence[int], need_bits: int) -> int:
    """How many leading sites are needed to hold ``need_bits`` bits."""
    used = 0
    accumulated = 0
    for width in widths:
        if accumulated >= need_bits:
            break
        accumulated += width
        used += 1
    return used
