from __future__ import annotations

from text_steganography import (
    CodecConfig,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)


def make_codec() -> TextSteganographyCodec:
    return TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()]))


def distinct_cover(n: int = 300) -> str:
    # distinct words so any multi-word excerpt occurs exactly once
    return " ".join(f"w{i}" for i in range(n))


def test_excerpt_aligns_uniquely():
    codec = make_codec()
    cover = distinct_cover()
    stego = codec.encode(cover, b"\x05").text
    excerpt = stego[40:700]

    alignment = codec.align_excerpt(cover, excerpt)
    assert alignment.status == "aligned"
    assert alignment.aligned is True
    assert alignment.offset == 40
    assert alignment.mapped_sites > 0
    assert alignment.occurrences == 1


def test_identify_traces_an_excerpt_to_its_recipient():
    codec = make_codec()
    cover = distinct_cover()
    recipients = [bytes([n]) for n in range(30)]
    copies = codec.encode_many(cover, recipients)
    excerpt = copies[17].text[40:700]  # a middle slice of recipient 17's copy

    result = codec.identify(excerpt, recipients, cover_text=cover)
    assert result.unique is True
    assert result.best().payload == bytes([17])


def test_excerpt_carries_partial_evidence():
    codec = make_codec()
    cover = distinct_cover()
    recipients = [bytes([n]) for n in range(30)]
    stego = codec.encode(cover, bytes([3])).text
    excerpt = stego[40:400]

    result = codec.identify(excerpt, recipients, cover_text=cover)
    # some evidence, but less than a full copy would give
    assert 0 < result.known_bits < result.observed_bits


def test_unrelated_text_is_not_found():
    codec = make_codec()
    alignment = codec.align_excerpt(distinct_cover(), "nothing here matches the cover at all")
    assert alignment.status == "not_found"
    assert alignment.slots is None


def test_repetitive_cover_is_ambiguous():
    codec = make_codec()
    repetitive = " ".join(["word"] * 300)
    alignment = codec.align_excerpt(repetitive, "word word")
    assert alignment.status == "ambiguous"
    assert alignment.occurrences > 1


def test_full_copy_aligns_at_offset_zero():
    codec = make_codec()
    cover = distinct_cover()
    stego = codec.encode(cover, b"\x09").text
    alignment = codec.align_excerpt(cover, stego)
    assert alignment.status == "aligned"
    assert alignment.offset == 0
    # a full copy maps every site
    assert alignment.mapped_sites == alignment.global_capacity


def test_cover_text_none_is_unchanged_full_length_path():
    codec = make_codec()
    cover = " ".join(["word"] * 200)
    recipients = [b"\x00\x01", b"\x00\x02", b"\x00\x03"]
    stego = codec.encode(cover, recipients[1]).text
    result = codec.identify(stego, recipients)  # no cover_text
    assert result.unique is True
    assert result.best().payload == recipients[1]
