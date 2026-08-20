from __future__ import annotations

from text_steganography import (
    CodecConfig,
    DecodeStatus,
    HtmlCarrier,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)


def html_codec() -> TextSteganographyCodec:
    return TextSteganographyCodec(
        CodecConfig(channels=[UnicodeSpaceChannel()], carrier=HtmlCarrier())
    )


def plain_codec() -> TextSteganographyCodec:
    return TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()]))


# An attribute with spaces that must never be touched, plus a body with capacity.
COVER = (
    '<a title="keep these spaces intact">home</a> <p>'
    + " ".join(["word"] * 200)
    + "</p>"
)


def test_round_trip_inside_html():
    codec = html_codec()
    result = codec.encode(COVER, b"hi")
    decoded = codec.decode(result.text)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == b"hi"


def test_tags_and_attributes_are_untouched():
    stego = html_codec().encode(COVER, b"payload!").text
    assert 'title="keep these spaces intact"' in stego  # attribute spaces intact
    assert "</a>" in stego and "<p>" in stego and "</p>" in stego


def test_html_carrier_sees_fewer_sites_than_plain():
    # plain text would embed in the attribute spaces too; the html carrier won't
    assert plain_codec().analyze(COVER).total_sites > html_codec().analyze(COVER).total_sites


def test_carrier_changes_codec_id_but_plain_stays_stable():
    assert html_codec().codec_id != plain_codec().codec_id
    # a plain space-only config is byte-identical to before carriers existed
    assert plain_codec().codec_id == "84b50c4527a3ae7b"


def test_config_serialization_round_trip_with_carrier():
    config = CodecConfig(channels=[UnicodeSpaceChannel()], carrier=HtmlCarrier())
    restored = CodecConfig.from_dict(config.to_dict())
    assert restored.carrier.id == "carrier.html"
    assert restored.codec_id == config.codec_id
