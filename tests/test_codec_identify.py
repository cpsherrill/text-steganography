from __future__ import annotations

from text_steganography import (
    CodecConfig,
    RepetitionCode,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)


_SPACE = "\u0020"
_NBSP = "\u00a0"


def make_codec(repeat: int = 1) -> TextSteganographyCodec:
    ecc = RepetitionCode(repeat=repeat) if repeat > 1 else None
    kwargs = {"channels": [UnicodeSpaceChannel()]}
    if ecc is not None:
        kwargs["error_correction"] = ecc
    return TextSteganographyCodec(CodecConfig(**kwargs))


def cover(n: int) -> str:
    return " ".join(["word"] * n)


def test_identify_pins_the_true_source():
    codec = make_codec()
    text = cover(200)
    recipients = [b"\x00\x01", b"\x00\x02", b"\x00\x03", b"\x2a\x2a"]
    stego = codec.encode(text, recipients[2]).text  # give recipient #2 their copy

    result = codec.identify(stego, recipients)
    assert result.unique is True
    assert result.best().payload == recipients[2]
    assert result.consistent[0].contradictions == 0


def test_identify_ranks_wrong_candidates_by_distance():
    codec = make_codec()
    text = cover(200)
    candidates = [b"AA", b"AB", b"ZZ"]
    stego = codec.encode(text, b"AA").text
    result = codec.identify(stego, candidates)
    # the true payload is the unique consistent one and ranks first
    assert result.best().payload == b"AA"
    assert result.ambiguity == 1
    # every other candidate contradicts at least one observed bit
    assert all(m.contradictions > 0 for m in result.ranked if m.payload != b"AA")


def test_identify_still_works_when_decode_would_not():
    # Corrupt a couple of sites so the frame's CRC fails: decode gives no
    # payload, but identify can still single out the closest source.
    codec = make_codec()
    text = cover(200)
    true_payload = b"\x11\x22"
    others = [b"\x99\x88", b"\x77\x66"]
    stego = codec.encode(text, true_payload).text

    # The 2-byte payload frames to 11 bytes = 88 bits, so its CRC lives in
    # sites 56..87. Flipping two of those breaks the checksum without moving
    # the true payload far in Hamming distance.
    sites = UnicodeSpaceChannel().discover_sites(stego)
    damaged = stego
    for site in sites[56:58]:
        i = site.start
        replacement = _NBSP if damaged[i] == _SPACE else _SPACE
        damaged = damaged[:i] + replacement + damaged[i + 1 :]

    assert codec.decode(damaged).payload is None  # decode cannot recover it
    result = codec.identify(damaged, [true_payload, *others])
    # the true payload is still the closest by distance, even though the
    # checksum failed and decode returned nothing
    assert result.best().payload == true_payload
    assert result.best().contradictions < result.ranked[1].contradictions


def test_preflight_reports_distinct_fitting_fingerprints():
    codec = make_codec()
    text = cover(300)
    recipients = [bytes([0, i]) for i in range(1, 21)]  # 20 two-byte tokens
    report = codec.preflight(text, recipients)
    assert report.count == 20
    assert report.all_fit is True
    assert report.all_distinct is True
    assert report.ok is True
    assert report.min_pairwise_distance is not None and report.min_pairwise_distance >= 1


def test_preflight_flags_oversized_set():
    codec = make_codec()
    text = cover(30)  # tiny capacity
    report = codec.preflight(text, [b"way too big to fit here at all"])
    assert report.all_fit is False
    assert report.ok is False


def test_encode_many_produces_one_stego_per_payload():
    codec = make_codec()
    text = cover(300)
    recipients = [bytes([0, i]) for i in range(1, 6)]
    results = codec.encode_many(text, recipients)
    assert len(results) == 5
    # each decodes back to its own recipient
    for payload, result in zip(recipients, results):
        assert codec.decode(result.text).payload == payload
