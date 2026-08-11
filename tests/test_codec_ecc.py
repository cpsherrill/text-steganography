from __future__ import annotations

import pytest

from text_steganography import (
    CapacityError,
    CodecConfig,
    DecodeStatus,
    RepetitionCode,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)

_SPACE = "\u0020"
_NBSP = "\u00a0"


def make_codec(repeat: int) -> TextSteganographyCodec:
    return TextSteganographyCodec(
        CodecConfig(
            channels=[UnicodeSpaceChannel()],
            error_correction=RepetitionCode(repeat=repeat),
        )
    )


def cover(n: int) -> str:
    return " ".join(["word"] * n)


def flip_site(text: str, j: int) -> str:
    """Toggle the j-th space site between a plain and a no-break space."""
    site = UnicodeSpaceChannel().discover_sites(text)[j]
    i = site.start
    replacement = _NBSP if text[i] == _SPACE else _SPACE
    return text[:i] + replacement + text[i + 1 :]


def test_ecc_round_trip():
    codec = make_codec(3)
    stego = codec.encode(cover(400), b"trace").text
    decoded = codec.decode(stego)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == b"trace"


def test_ecc_corrects_a_flipped_copy():
    codec = make_codec(3)
    stego = codec.encode(cover(400), b"hi").text
    damaged = flip_site(stego, 0)  # corrupt one of three copies of the first bit
    decoded = codec.decode(damaged)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == b"hi"
    assert decoded.corrected_errors >= 1


def test_ecc_beyond_correction_power_fails_cleanly():
    codec = make_codec(3)
    stego = codec.encode(cover(400), b"hi").text
    damaged = flip_site(flip_site(stego, 0), 1)  # corrupt two of three copies
    decoded = codec.decode(damaged)
    assert decoded.status is not DecodeStatus.SUCCESS
    assert decoded.payload is None


def test_no_ecc_codec_id_is_still_stable():
    # the Phase 1 value; the ECC field must not perturb a no-ECC config
    assert CodecConfig(channels=[UnicodeSpaceChannel()]).codec_id == "84b50c4527a3ae7b"


def test_ecc_changes_codec_id_and_serializes():
    base = CodecConfig(channels=[UnicodeSpaceChannel()])
    with_ecc = CodecConfig(
        channels=[UnicodeSpaceChannel()], error_correction=RepetitionCode(repeat=3)
    )
    assert base.codec_id != with_ecc.codec_id
    data = with_ecc.to_dict()
    assert data["error_correction"]["id"] == "ecc.repetition"
    assert data["error_correction"]["params"] == {"repeat": 3}
    assert CodecConfig.from_dict(data).codec_id == with_ecc.codec_id


def test_ecc_reduces_usable_capacity():
    report = make_codec(3).analyze(cover(300))  # 299 sites
    assert report.usable_payload_bytes == 3  # 299 // 3 = 99 message bits, minus 72
    assert report.ecc_overhead_bits == 198


def test_ecc_rejects_oversized_payload():
    codec = make_codec(3)
    text = cover(300)
    usable = codec.analyze(text).usable_payload_bytes
    codec.encode(text, b"\x00" * usable)  # the reported limit fits
    with pytest.raises(CapacityError):
        codec.encode(text, b"\x00" * (usable + 1))
