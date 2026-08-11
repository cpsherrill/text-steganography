"""Integrity helpers.

CRC-32 is used as a cheap, standard integrity check. It answers "did we
recover the intended frame?" It is not a message-authentication code and does
not defend against an adversary who can recompute it; keyed authentication is
a later, optional payload transform.
"""

from __future__ import annotations

import zlib


def crc32(data: bytes) -> int:
    """Return the CRC-32 of ``data`` as an unsigned 32-bit integer."""
    return zlib.crc32(data) & 0xFFFFFFFF
