"""Same-version decoding policy: configs record the library version that wrote them."""

from __future__ import annotations

import pathlib
import re

import pytest

import text_steganography
from text_steganography import (
    CodecConfig,
    ConfigError,
    DecodeStatus,
    MarkdownCarrier,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)
from text_steganography._version import __version__

COVER = " ".join(["word"] * 200)
OTHER = "0.0.0-older"


def space_config(**kwargs) -> CodecConfig:
    return CodecConfig(channels=[UnicodeSpaceChannel()], **kwargs)


def test_package_version_has_one_source_and_matches_pyproject():
    assert text_steganography.__version__ == __version__
    pyproject = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
    declared = re.search(r'^version = "([^"]+)"', pyproject.read_text(), re.M).group(1)
    assert declared == __version__


def test_new_configs_are_stamped_with_the_installed_version():
    assert space_config().to_dict()["created_with"] == __version__


def test_the_stamp_is_not_part_of_the_codec_identity():
    stamped = space_config()
    foreign = space_config(created_with=OTHER)
    unstamped = space_config(created_with=None)
    assert stamped.codec_id == foreign.codec_id == unstamped.codec_id
    # the plain space-only codec_id is unchanged since Phase 1
    assert stamped.codec_id == "84b50c4527a3ae7b"


def test_loaded_configs_keep_their_stamp_and_unstamped_ones_stay_unstamped():
    foreign = CodecConfig.from_dict(space_config(created_with=OTHER).to_dict())
    assert foreign.created_with == OTHER
    assert foreign.to_dict()["created_with"] == OTHER

    legacy = space_config().to_dict()
    del legacy["created_with"]
    loaded = CodecConfig.from_dict(legacy)
    assert loaded.created_with is None
    assert "created_with" not in loaded.to_dict()  # never invent provenance


def test_same_version_decoding_has_no_version_warning():
    codec = TextSteganographyCodec(space_config())
    stego = codec.encode(COVER, b"hi").text
    decoded = codec.decode(stego)
    assert decoded.payload == b"hi"
    assert not any("saved by text-steganography" in w for w in decoded.warnings)


def test_other_version_decoding_still_runs_but_warns():
    codec = TextSteganographyCodec(space_config(created_with=OTHER))
    stego = codec.encode(COVER, b"hi")
    assert any(f"guaranteed with version {OTHER}" in w for w in stego.warnings)
    decoded = codec.decode(stego.text)
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.warnings[0].startswith(f"configuration saved by text-steganography {OTHER}")


def test_changed_component_names_the_version_to_install():
    saved = CodecConfig(channels=[UnicodeSpaceChannel()], carrier=MarkdownCarrier()).to_dict()
    saved["carrier"]["version"] = "2"  # an older Markdown carrier layout
    saved["created_with"] = OTHER
    with pytest.raises(ConfigError, match=f"decode it with version {re.escape(OTHER)}"):
        CodecConfig.from_dict(saved)


def test_changed_component_without_a_foreign_stamp_keeps_the_plain_error():
    saved = CodecConfig(channels=[UnicodeSpaceChannel()], carrier=MarkdownCarrier()).to_dict()
    saved["carrier"]["version"] = "2"
    with pytest.raises(ConfigError) as caught:
        CodecConfig.from_dict(saved)
    assert "decode it with version" not in str(caught.value)


def test_stamp_must_be_a_string():
    saved = space_config().to_dict()
    saved["created_with"] = 1
    with pytest.raises(ConfigError, match="created_with"):
        CodecConfig.from_dict(saved)
