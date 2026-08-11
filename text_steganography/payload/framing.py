"""Payload framing: ``length_crc_v1``.

The frame wraps arbitrary payload bytes with just enough structure to decode
them back out and to notice damage:

    magic (2 bytes, "ST")
    frame version (1 byte)
    payload length (2 bytes, big-endian, in bytes)
    payload bytes
    CRC-32 (4 bytes, big-endian, over everything before it)

Fixed overhead is nine bytes. The length field lets the decoder learn how many
payload bytes to read without any external manifest, and the CRC lets it tell
a real recovery from a plausible-looking accident.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import FramingError
from .integrity import crc32

MAGIC = b"ST"
FRAME_VERSION = 1
HEADER_LEN = 5  # magic(2) + version(1) + length(2)
TRAILER_LEN = 4  # crc32
OVERHEAD_BYTES = HEADER_LEN + TRAILER_LEN  # 9
OVERHEAD_BITS = OVERHEAD_BYTES * 8  # 72
MAX_PAYLOAD_BYTES = 0xFFFF


@dataclass(frozen=True)
class Frame:
    """A parsed frame."""

    version: int
    payload: bytes
    integrity_valid: bool


def frame(payload: bytes, *, version: int = FRAME_VERSION) -> bytes:
    """Wrap ``payload`` into a ``length_crc_v1`` frame."""
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise FramingError(
            f"payload of {len(payload)} bytes exceeds the {MAX_PAYLOAD_BYTES}-byte frame limit"
        )
    if not 0 <= version <= 0xFF:
        raise FramingError("frame version must fit in one byte")
    body = MAGIC + bytes([version]) + len(payload).to_bytes(2, "big") + payload
    return body + crc32(body).to_bytes(4, "big")


def unframe(data: bytes) -> Frame:
    """Parse a frame produced by :func:`frame`.

    Raises :class:`FramingError` when the buffer cannot be a frame at all
    (bad magic, too short, truncated). A buffer that is structurally a frame
    but fails its checksum is returned with ``integrity_valid=False`` rather
    than raised, so callers can decide how to treat it.
    """
    if len(data) < OVERHEAD_BYTES:
        raise FramingError(f"buffer of {len(data)} bytes is too short to be a frame")
    if data[0:2] != MAGIC:
        raise FramingError("frame magic not found")
    version = data[2]
    length = int.from_bytes(data[3:5], "big")
    payload_end = HEADER_LEN + length
    if len(data) < payload_end + TRAILER_LEN:
        raise FramingError("frame is truncated: length field exceeds available bytes")
    payload = data[HEADER_LEN:payload_end]
    stored_crc = int.from_bytes(data[payload_end : payload_end + TRAILER_LEN], "big")
    actual_crc = crc32(data[:payload_end])
    return Frame(version=version, payload=payload, integrity_valid=(stored_crc == actual_crc))


def framed_bit_length(payload_len: int) -> int:
    """Total frame size in bits for a payload of ``payload_len`` bytes."""
    return (OVERHEAD_BYTES + payload_len) * 8
