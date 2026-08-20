from __future__ import annotations

import unicodedata

from text_steganography import (
    CanonicalUnicodeChannel,
    CodecConfig,
    DecodeStatus,
    TextSteganographyCodec,
)

_COMPOSED = "\u00e9"  # e with acute, one code point
_DECOMPOSED = "\u0065\u0301"  # e + combining acute, two code points


def make_codec() -> TextSteganographyCodec:
    return TextSteganographyCodec(CodecConfig(channels=[CanonicalUnicodeChannel()]))


def accented(n: int) -> str:
    # composed accented characters separated by spaces; each accent is a site
    return (_COMPOSED + " ") * n


def test_precomposed_characters_are_sites():
    channel = CanonicalUnicodeChannel()
    sites = channel.discover_sites("caf" + _COMPOSED)  # one accented character
    assert len(sites) == 1
    assert sites[0].variants[0] == _COMPOSED
    assert sites[0].variants[1] == _DECOMPOSED


def test_round_trip():
    codec = make_codec()
    cover = accented(120)
    result = codec.encode(cover, b"nf")
    decoded = codec.decode(result.text)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == b"nf"


def test_decomposed_form_is_longer_but_canonicalizes_back():
    codec = make_codec()
    cover = accented(120)
    stego = codec.encode(cover, b"trace").text
    assert len(stego) > len(cover)  # some characters decomposed
    assert codec.canonicalize(stego) == cover


def test_nfc_normalization_erases_the_signal():
    # the point of the channel's fragility: NFC recomposes everything
    codec = make_codec()
    cover = accented(120)
    stego = codec.encode(cover, b"trace").text
    assert unicodedata.normalize("NFC", stego) == cover
    decoded = codec.decode(unicodedata.normalize("NFC", stego))
    assert decoded.status is not DecodeStatus.SUCCESS


def test_observe_reads_a_decomposed_character_as_symbol_one():
    channel = CanonicalUnicodeChannel()
    observations = channel.observe("caf" + _DECOMPOSED)  # decomposed e-acute
    assert observations[-1].symbol == 1


def test_excerpt_alignment_is_refused():
    codec = make_codec()
    alignment = codec.align_excerpt(accented(120), "caf" + _COMPOSED)
    assert alignment.status == "unsupported"
