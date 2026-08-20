from __future__ import annotations

from text_steganography import (
    CodecConfig,
    DecodeStatus,
    MarkdownCarrier,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)
from text_steganography.carriers import MarkdownCarrier as _MC

_NBSP = "\u00a0"

COVER = (
    "# My Heading Here\n\n"
    'Here is `inline code here` and a [link](http://example.com "a title with spaces").\n\n'
    "```\ncode fence with spaces\n```\n\n"
    "> a blockquote with words\n\n" + " ".join(["word"] * 250) + "\n"
)


def md_codec() -> TextSteganographyCodec:
    return TextSteganographyCodec(
        CodecConfig(channels=[UnicodeSpaceChannel()], carrier=MarkdownCarrier())
    )


def safe_prose(document: str) -> str:
    return "".join(document[s:e] for s, e in _MC().safe_spans(document))


def test_structural_regions_are_excluded_from_safe_prose():
    prose = safe_prose(COVER)
    assert "inline code here" not in prose  # inline code
    assert "a title with spaces" not in prose  # link title
    assert "code fence with spaces" not in prose  # fenced block
    assert "http://example.com" not in prose  # link destination


def test_round_trip_through_markdown():
    codec = md_codec()
    result = codec.encode(COVER, b"md")
    decoded = codec.decode(result.text)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == b"md"


def test_encoding_leaves_structure_byte_identical():
    stego = md_codec().encode(COVER, b"trace").text
    assert "`inline code here`" in stego  # inline code untouched
    assert '"a title with spaces"' in stego  # link title untouched
    assert "code fence with spaces" in stego  # fence content untouched
    assert "# M" in stego  # the space after the heading hash survives


def test_no_break_space_never_lands_in_code():
    stego = md_codec().encode(COVER, b"trace").text
    fence = stego[stego.index("code fence") : stego.index("with spaces") + len("with spaces")]
    assert _NBSP not in fence


def test_plain_and_markdown_disagree_on_capacity():
    plain = TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()]))
    # plain text would embed in code and structure; markdown protects them
    assert plain.analyze(COVER).total_sites > md_codec().analyze(COVER).total_sites


def test_config_round_trip_with_markdown_carrier():
    config = CodecConfig(channels=[UnicodeSpaceChannel()], carrier=MarkdownCarrier())
    restored = CodecConfig.from_dict(config.to_dict())
    assert restored.carrier.id == "carrier.markdown"
    assert restored.codec_id == config.codec_id
