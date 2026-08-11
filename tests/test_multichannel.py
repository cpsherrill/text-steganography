from __future__ import annotations

from text_steganography import (
    ApostropheChannel,
    CodecConfig,
    DecodeStatus,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)


def make_codec() -> TextSteganographyCodec:
    return TextSteganographyCodec(
        CodecConfig(channels=[UnicodeSpaceChannel(), ApostropheChannel()])
    )


def two_channel_cover() -> str:
    # each "it's" carries one apostrophe bit; each gap carries one space bit
    return " ".join(["it's"] * 100)


def test_both_channels_contribute_capacity():
    report = make_codec().analyze(two_channel_cover())
    by_id = {c.channel_id: c for c in report.per_channel}
    assert by_id["whitespace.unicode_space"].sites == 99
    assert by_id["punctuation.apostrophe"].sites == 100
    assert report.realizable_packed_bits == 199


def test_multichannel_round_trip():
    codec = make_codec()
    cover = two_channel_cover()
    stego = codec.encode(cover, b"two channels").text
    decoded = codec.decode(stego)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == b"two channels"


def test_multichannel_encode_is_invisible_under_canonicalization():
    codec = make_codec()
    cover = two_channel_cover()
    stego = codec.encode(cover, b"trace-77").text
    assert stego != cover
    assert codec.canonicalize(stego) == cover


def test_channel_order_changes_codec_id():
    a = CodecConfig(channels=[UnicodeSpaceChannel(), ApostropheChannel()])
    b = CodecConfig(channels=[ApostropheChannel(), UnicodeSpaceChannel()])
    assert a.codec_id != b.codec_id
