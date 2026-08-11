from __future__ import annotations

import unicodedata

from text_steganography import (
    CodecConfig,
    DecodeStatus,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)


def make_codec() -> TextSteganographyCodec:
    return TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()]))


def cover() -> str:
    return " ".join(["word"] * 200)


def test_nfc_preserves_the_space_channel():
    # A no-break space has only a compatibility decomposition, so canonical
    # (NFC) normalization leaves it, and the watermark, intact.
    codec = make_codec()
    stego = codec.encode(cover(), b"data").text
    normalized = unicodedata.normalize("NFC", stego)
    decoded = codec.decode(normalized)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == b"data"


def test_nfkc_erases_the_space_channel():
    # Compatibility (NFKC) normalization maps a no-break space to a plain
    # space, which flattens every symbol to zero and destroys the signal.
    codec = make_codec()
    stego = codec.encode(cover(), b"data").text
    normalized = unicodedata.normalize("NFKC", stego)
    decoded = codec.decode(normalized)
    assert decoded.status is not DecodeStatus.SUCCESS
    assert decoded.payload is None
