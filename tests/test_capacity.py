from __future__ import annotations

import pytest

from text_steganography import (
    CapacityError,
    CodecConfig,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)


def make_codec() -> TextSteganographyCodec:
    return TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()]))


def cover_with_words(n: int) -> str:
    return " ".join(["word"] * n)


def test_capacity_matches_site_count():
    codec = make_codec()
    report = codec.analyze(cover_with_words(100))  # 99 inter-word spaces
    assert report.total_sites == 99
    assert report.realizable_packed_bits == 99
    assert report.per_channel[0].channel_id == "whitespace.unicode_space"
    assert report.per_channel[0].sites == 99


def test_overhead_is_reported_separately():
    report = make_codec().analyze(cover_with_words(100))
    assert report.framing_overhead_bits == 40
    assert report.integrity_overhead_bits == 32
    assert report.ecc_overhead_bits == 0


def test_usable_capacity_subtracts_overhead():
    # 99 bits realizable, minus 72 bits overhead, is 27 bits, floored to 3 bytes
    report = make_codec().analyze(cover_with_words(100))
    assert report.usable_payload_bytes == 3
    assert report.usable_payload_bits == 24
    assert report.max_distinct_payloads == 2**24


def test_low_capacity_text_reports_nothing_usable():
    report = make_codec().analyze(cover_with_words(20))  # 19 bits, below the frame floor
    assert report.usable_payload_bytes == 0
    assert report.max_distinct_payloads == 0


def test_analyze_and_encode_agree_on_the_limit():
    codec = make_codec()
    cover = cover_with_words(100)
    usable = codec.analyze(cover).usable_payload_bytes
    # a payload at the reported limit fits
    codec.encode(cover, b"\x00" * usable)
    # one byte over the reported limit does not
    with pytest.raises(CapacityError):
        codec.encode(cover, b"\x00" * (usable + 1))
