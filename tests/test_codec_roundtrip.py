from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from text_steganography import (
    CapacityError,
    CodecConfig,
    DecodeStatus,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)

_NBSP = "\u00a0"


def make_codec() -> TextSteganographyCodec:
    return TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()]))


def cover_with_words(n: int) -> str:
    return " ".join(["word"] * n)


def test_basic_round_trip():
    codec = make_codec()
    cover = cover_with_words(200)
    result = codec.encode(cover, b"hi")
    decoded = codec.decode(result.text)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == b"hi"
    assert decoded.integrity_valid is True


def test_encode_is_invisible_under_canonicalization():
    codec = make_codec()
    cover = cover_with_words(200)
    stego = codec.encode(cover, b"\x2a\x00\xff").text
    assert stego != cover  # something changed
    assert codec.canonicalize(stego) == cover  # but it canonicalizes back


def test_encode_is_deterministic():
    codec = make_codec()
    cover = cover_with_words(120)
    assert codec.encode(cover, b"ID").text == codec.encode(cover, b"ID").text


def test_round_trip_survives_config_serialization():
    original = CodecConfig(channels=[UnicodeSpaceChannel()])
    cover = cover_with_words(200)
    stego = TextSteganographyCodec(original).encode(cover, b"trace").text

    rebuilt = CodecConfig.from_dict(original.to_dict())
    decoded = TextSteganographyCodec(rebuilt).decode(stego)
    assert decoded.payload == b"trace"


def test_payload_too_large_raises():
    codec = make_codec()
    cover = cover_with_words(20)  # only 19 bits, far below the 72-bit frame floor
    with pytest.raises(CapacityError):
        codec.encode(cover, b"way too big for this")


def test_decoding_plain_text_is_invalid_not_a_crash():
    codec = make_codec()
    # unencoded text reads as all-zero symbols; the magic will not match
    decoded = codec.decode(cover_with_words(200))
    assert decoded.status is DecodeStatus.INVALID
    assert decoded.payload is None


def test_corrupted_stego_fails_integrity():
    codec = make_codec()
    cover = cover_with_words(200)
    stego = codec.encode(cover, b"secret").text
    # flip the first encoded no-break space back to a plain space, which lands
    # inside the frame and breaks the checksum
    idx = stego.index(_NBSP)
    damaged = stego[:idx] + " " + stego[idx + 1 :]
    decoded = codec.decode(damaged)
    # the guarantee: a broken frame is INVALID with no payload, never wrong bytes
    assert decoded.status is DecodeStatus.INVALID
    assert decoded.payload is None


@settings(max_examples=60, deadline=None)
@given(payload=st.binary(min_size=0, max_size=20))
def test_round_trip_property(payload: bytes):
    codec = make_codec()
    cover = cover_with_words(260)  # 259 bits, room for up to 23 payload bytes
    stego = codec.encode(cover, payload).text
    decoded = codec.decode(stego)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == payload
