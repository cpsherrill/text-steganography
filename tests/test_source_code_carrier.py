from __future__ import annotations

import pytest

from text_steganography import (
    CodecConfig,
    DecodeStatus,
    SourceCodeCarrier,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)

_NBSP = "\u00a0"

PY_COVER = (
    "# a header comment with several words here to give the encoder room to work\n"
    'x = "a string with spaces that must not change at all"  # trailing comment words\n'
    "def greet(name):  # another comment with more and more words padding it out here\n"
    '    return f"hello there {name}"\n' + "# " + " ".join(["word"] * 200) + "\n"
)

C_COVER = (
    "// a line comment with lots of words here to give the encoder plenty of room\n"
    'const char *s = "a // b string, definitely not a comment here";  /* block words too */\n'
    "int main(void) { return 0; } // trailing comment with a few words at the end here\n"
    + "// " + " ".join(["word"] * 200) + "\n"
)


def codec(language: str) -> TextSteganographyCodec:
    return TextSteganographyCodec(
        CodecConfig(
            channels=[UnicodeSpaceChannel()],
            carrier=SourceCodeCarrier.for_language(language),
        )
    )


def test_python_round_trip_and_string_is_untouched():
    c = codec("python")
    stego = c.encode(PY_COVER, b"py").text
    decoded = c.decode(stego)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == b"py"
    # the string literal keeps its exact spaces; nothing structural moved
    assert '"a string with spaces that must not change at all"' in stego
    assert "def greet(name):" in stego


def test_c_round_trip_and_slashes_in_a_string_are_not_a_comment():
    c = codec("c")
    stego = c.encode(C_COVER, b"cc").text
    decoded = c.decode(stego)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == b"cc"
    # the // inside the string is content, not a comment, so the string is intact
    assert '"a // b string, definitely not a comment here"' in stego
    assert "int main(void) { return 0; }" in stego


def test_no_break_space_only_appears_in_comments():
    c = codec("python")
    stego = c.encode(PY_COVER, b"xy").text
    # every no-break space must sit on a line that has a comment
    for line in stego.splitlines():
        if _NBSP in line:
            assert "#" in line


def test_file_without_comments_has_no_capacity():
    c = codec("c")
    assert c.analyze("int x = 1; int y = 2;").total_sites == 0


def test_unknown_language_raises():
    with pytest.raises(ValueError):
        SourceCodeCarrier.for_language("cobol")


def test_config_round_trip_with_source_carrier():
    config = CodecConfig(
        channels=[UnicodeSpaceChannel()], carrier=SourceCodeCarrier.for_language("python")
    )
    restored = CodecConfig.from_dict(config.to_dict())
    assert restored.carrier.id == "carrier.source_code"
    assert restored.carrier.params()["line_comment"] == "#"
    assert restored.codec_id == config.codec_id
