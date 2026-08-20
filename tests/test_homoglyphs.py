from __future__ import annotations

from text_steganography import (
    CodecConfig,
    CyrillicHomoglyphChannel,
    DecodeStatus,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
    inspect_text,
)
from text_steganography.models import Risk

_CYRILLIC_O = "\u043e"  # U+043E


def make_codec() -> TextSteganographyCodec:
    return TextSteganographyCodec(CodecConfig(channels=[CyrillicHomoglyphChannel()]))


def prose(n: int) -> str:
    # every a/c/e/o/p/x/y is a confusable, so this is dense with sites
    return " ".join(["category people example economy"] * n)


def test_every_confusable_letter_is_a_site():
    channel = CyrillicHomoglyphChannel()
    # c, o, c, o, a  -> five sites in "cocoa"
    assert len(channel.discover_sites("cocoa")) == 5


def test_round_trip():
    codec = make_codec()
    cover = prose(30)
    result = codec.encode(cover, b"\x2a\x2a")
    decoded = codec.decode(result.text)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == b"\x2a\x2a"


def test_encoding_is_invisible_under_canonicalization():
    codec = make_codec()
    cover = prose(30)
    stego = codec.encode(cover, b"trace").text
    assert stego != cover  # some letters became Cyrillic
    assert codec.canonicalize(stego) == cover  # and canonicalize restores them


def test_stego_actually_mixes_scripts():
    codec = make_codec()
    stego = codec.encode(prose(30), b"trace").text
    # the whole point: an observer inspecting the bytes sees mixed scripts
    report = inspect_text(stego)
    assert report.mixed_scripts is True
    assert _CYRILLIC_O in stego


def test_observe_reads_cyrillic_as_symbol_one():
    channel = CyrillicHomoglyphChannel()
    observations = channel.observe("c" + _CYRILLIC_O + "de")  # o replaced by Cyrillic
    by_ordinal = {o.ordinal: o.symbol for o in observations}
    # sites are c(0), о(1), e(2): the Cyrillic o reads as symbol 1
    assert by_ordinal[1] == 1


def test_metadata_is_high_risk():
    assert CyrillicHomoglyphChannel().metadata().risk is Risk.HIGH


def test_composes_with_other_channels():
    codec = TextSteganographyCodec(
        CodecConfig(channels=[UnicodeSpaceChannel(), CyrillicHomoglyphChannel()])
    )
    cover = prose(30)
    stego = codec.encode(cover, b"both").text
    assert codec.decode(stego).payload == b"both"
