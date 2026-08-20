from __future__ import annotations

from text_steganography import (
    CodecConfig,
    DecodeStatus,
    TextSteganographyCodec,
    ZeroWidthChannel,
)

_MARK = "\u2060"  # U+2060 word joiner


def make_codec() -> TextSteganographyCodec:
    return TextSteganographyCodec(CodecConfig(channels=[ZeroWidthChannel()]))


def prose(n: int) -> str:
    return " ".join(["consideration"] * n)  # long words = many letter boundaries


def test_sites_are_letter_boundaries():
    channel = ZeroWidthChannel()
    # "abc de" -> boundaries a-b, b-c, d-e = 3 (the space breaks the run)
    assert len(channel.discover_sites("abc de")) == 3


def test_round_trip():
    codec = make_codec()
    cover = prose(20)
    result = codec.encode(cover, b"zw")
    decoded = codec.decode(result.text)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == b"zw"


def test_encoding_changes_length_but_canonicalizes_back():
    codec = make_codec()
    cover = prose(20)
    stego = codec.encode(cover, b"trace").text
    assert len(stego) > len(cover)  # joiners were inserted
    assert _MARK in stego
    assert codec.canonicalize(stego) == cover  # removing them restores the cover


def test_the_mark_is_invisible_to_the_reader():
    # stripping the joiners yields exactly the original words
    codec = make_codec()
    cover = prose(10)
    stego = codec.encode(cover, b"x").text
    assert stego.replace(_MARK, "") == cover


def test_excerpt_alignment_is_refused_for_length_changing_channels():
    codec = make_codec()
    cover = prose(20)
    alignment = codec.align_excerpt(cover, "consideration")
    assert alignment.status == "unsupported"
    assert alignment.slots is None


def test_full_length_identify_still_works():
    codec = make_codec()
    cover = prose(20)
    recipients = [bytes([n]) for n in range(8)]
    stego = codec.encode(cover, recipients[5]).text
    result = codec.identify(stego, recipients)  # full-length, no cover_text
    assert result.best().payload == recipients[5]
