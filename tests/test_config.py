from __future__ import annotations

from typing import Dict, List, Optional

import pytest

from text_steganography.channels.base import (
    BaseChannel,
    ChannelContext,
    build_channel,
    register_channel,
)
from text_steganography.config import (
    CodecConfig,
    FramingConfig,
    PackingMode,
    RepertoirePolicy,
)
from text_steganography.errors import ConfigError
from text_steganography.models import (
    ChannelMetadata,
    EmbeddingSite,
    Invariant,
    Observation,
    Risk,
)


@register_channel
class _ToyChannel(BaseChannel):
    """A minimal registered channel used only by the configuration tests."""

    id = "test.toy"
    version = "1"

    def __init__(self, radix: int = 2) -> None:
        self.radix = radix

    def discover_sites(self, text, context=None) -> List[EmbeddingSite]:
        return []

    def observe(self, text, context=None) -> List[Observation]:
        return []

    def canonicalize(self, text: str) -> str:
        return text

    def metadata(self) -> ChannelMetadata:
        return ChannelMetadata(self.id, self.version, Invariant.CANONICAL_TEXT, Risk.LOW, "toy")

    def params(self) -> Dict[str, object]:
        return {"radix": self.radix}


def test_codec_id_is_stable_and_serializable():
    config = CodecConfig(channels=[_ToyChannel(radix=4)])
    first = config.codec_id
    restored = CodecConfig.from_dict(config.to_dict())
    assert restored.codec_id == first
    assert restored.channels[0].params() == {"radix": 4}


def test_codec_id_changes_with_parameters():
    a = CodecConfig(channels=[_ToyChannel(radix=2)])
    b = CodecConfig(channels=[_ToyChannel(radix=4)])
    assert a.codec_id != b.codec_id


def test_codec_id_changes_with_repertoire():
    base = CodecConfig(channels=[_ToyChannel()])
    opened = CodecConfig(
        channels=[_ToyChannel()],
        repertoire=RepertoirePolicy(allow_cross_script=True),
    )
    assert base.codec_id != opened.codec_id


def test_defaults_are_conservative():
    policy = RepertoirePolicy()
    assert policy.scripts == ("Latin",)
    assert policy.allow_cross_script is False
    assert policy.allow_bidi_controls is False
    assert policy.allow_joiners is False


def test_packing_default_is_power_of_two():
    assert CodecConfig(channels=[_ToyChannel()]).packing is PackingMode.POWER_OF_TWO


def test_build_channel_rejects_unknown_id():
    with pytest.raises(ConfigError):
        build_channel("test.does-not-exist", "1", {})


def test_build_channel_rejects_version_mismatch():
    with pytest.raises(ConfigError):
        build_channel("test.toy", "999", {})


def test_register_channel_rejects_blank_id():
    with pytest.raises(ConfigError):

        @register_channel
        class _Blank(BaseChannel):
            id = ""
            version = "1"

            def discover_sites(self, text, context=None):
                return []

            def observe(self, text, context=None):
                return []

            def canonicalize(self, text):
                return text

            def metadata(self):
                return ChannelMetadata(self.id, self.version, Invariant.CANONICAL_TEXT, Risk.LOW, "")
