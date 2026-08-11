from __future__ import annotations

from typing import List, Optional

import pytest

from text_steganography.channels.base import (
    BaseChannel,
    ChannelContext,
    register_channel,
)
from text_steganography.config import CodecConfig
from text_steganography.core.planner import build_plan
from text_steganography.errors import ConflictError
from text_steganography.models import (
    ChannelMetadata,
    EmbeddingSite,
    Invariant,
    Observation,
    Risk,
)


class _FixedSpanChannel(BaseChannel):
    """A test channel that always claims one fixed span."""

    _span = (0, 1)

    def discover_sites(self, text, context=None) -> List[EmbeddingSite]:
        start, end = self._span
        if len(text) < end:
            return []
        return [
            EmbeddingSite(
                channel_id=self.id,
                ordinal=0,
                start=start,
                end=end,
                variants=("a", "b"),
                canonical="a",
            )
        ]

    def observe(self, text, context=None) -> List[Observation]:
        return []

    def canonicalize(self, text: str) -> str:
        return text

    def metadata(self) -> ChannelMetadata:
        return ChannelMetadata(self.id, self.version, Invariant.CANONICAL_TEXT, Risk.LOW, "")


@register_channel
class _SpanA(_FixedSpanChannel):
    id = "test.span_a"
    version = "1"
    _span = (0, 3)


@register_channel
class _SpanB(_FixedSpanChannel):
    id = "test.span_b"
    version = "1"
    _span = (1, 4)  # overlaps [0, 3)


@register_channel
class _SpanC(_FixedSpanChannel):
    id = "test.span_c"
    version = "1"
    _span = (5, 7)  # disjoint from span A


def test_overlapping_spans_raise_conflict():
    config = CodecConfig(channels=[_SpanA(), _SpanB()])
    with pytest.raises(ConflictError):
        build_plan(config, "abcdefgh")


def test_disjoint_spans_are_fine():
    config = CodecConfig(channels=[_SpanA(), _SpanC()])
    plan = build_plan(config, "abcdefgh")
    assert len(plan.planned_sites) == 2
