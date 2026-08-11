from __future__ import annotations

import unicodedata

from text_steganography import (
    ApostropheChannel,
    CodecConfig,
    Profile,
    UnicodeSpaceChannel,
    build_probe,
    get_profile,
    list_profiles,
    profile_from_probe,
)
from text_steganography.probe.model import SurvivalLabel


def config() -> CodecConfig:
    return CodecConfig(channels=[UnicodeSpaceChannel(), ApostropheChannel()])


def test_builtin_profiles_exist():
    names = list_profiles()
    assert "lossless" in names
    assert "unicode_nfkc" in names
    assert "plain_text_conservative" in names


def test_lossless_recommends_everything():
    profile = get_profile("lossless")
    assert profile.recommendation_for("whitespace.unicode_space") is SurvivalLabel.RECOMMENDED
    assert profile.warnings_for(config()) == []


def test_nfkc_profile_warns_about_the_space_channel():
    profile = get_profile("unicode_nfkc")
    warnings = profile.warnings_for(config())
    assert any("whitespace.unicode_space" in w and "unsupported" in w for w in warnings)
    # the apostrophe channel is fine under NFKC, so it should not warn
    assert not any("punctuation.apostrophe" in w for w in warnings)


def test_conservative_profile_flags_untested_unknown_channel():
    profile = get_profile("plain_text_conservative")
    # a channel the profile says nothing about is untested, not silently fine
    assert profile.recommendation_for("some.future.channel") is SurvivalLabel.UNTESTED


def test_profile_from_probe_matches_measurement():
    probe = build_probe(config())
    returned = unicodedata.normalize("NFKC", probe.stego)
    profile = profile_from_probe(
        "nfkc-measured",
        "NFKC path, measured",
        probe,
        returned,
        evidence="measured via NFKC round trip in tests",
    )
    assert profile.recommendation_for("whitespace.unicode_space") is SurvivalLabel.UNSUPPORTED
    assert profile.recommendation_for("punctuation.apostrophe") is SurvivalLabel.RECOMMENDED


def test_profile_serialization_round_trip():
    profile = get_profile("unicode_nfkc")
    restored = Profile.from_dict(profile.to_dict())
    assert restored.name == profile.name
    assert restored.recommendations == profile.recommendations
    assert restored.evidence == profile.evidence
