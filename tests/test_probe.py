from __future__ import annotations

import unicodedata

from text_steganography import (
    ApostropheChannel,
    CodecConfig,
    UnicodeSpaceChannel,
    build_probe,
)
from text_steganography.probe import Probe, SurvivalLabel


def make_config() -> CodecConfig:
    return CodecConfig(channels=[UnicodeSpaceChannel(), ApostropheChannel()])


def test_identity_transport_is_fully_recommended():
    probe = build_probe(make_config())
    report = probe.evaluate(probe.stego)  # a lossless round trip
    assert report.overall_survival == 1.0
    for channel in report.per_channel:
        assert channel.label is SurvivalLabel.RECOMMENDED
        assert channel.substituted == 0


def test_probe_has_sites_for_each_channel():
    probe = build_probe(make_config())
    for channel_id, symbols in probe.expected.items():
        assert len(symbols) > 0, channel_id


def test_nbsp_stripping_transport_marks_space_channel_unsupported():
    probe = build_probe(make_config())
    # a transport that turns every no-break space back into a plain space
    stripped = probe.stego.replace("\u00a0", "\u0020")
    report = probe.evaluate(stripped)
    by_id = {c.channel_id: c for c in report.per_channel}
    space = by_id["whitespace.unicode_space"]
    assert space.label is SurvivalLabel.UNSUPPORTED
    assert space.survival_rate == 0.0
    # the apostrophe channel is untouched by this transport
    assert by_id["punctuation.apostrophe"].label is SurvivalLabel.RECOMMENDED


def test_nfc_transport_preserves_everything():
    probe = build_probe(make_config())
    returned = unicodedata.normalize("NFC", probe.stego)
    report = probe.evaluate(returned)
    assert report.overall_survival == 1.0


def test_probe_serialization_round_trip():
    probe = build_probe(make_config())
    restored = Probe.from_dict(probe.to_dict())
    assert restored.stego == probe.stego
    assert restored.expected == probe.expected
    # the restored probe evaluates identically
    assert restored.evaluate(probe.stego).overall_survival == 1.0


def test_summary_is_readable():
    probe = build_probe(make_config())
    summary = probe.evaluate(probe.stego).summary()
    assert "overall" in summary
    assert "recommended" in summary
