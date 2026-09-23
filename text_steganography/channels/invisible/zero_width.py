"""A zero-width insertion channel.

At each boundary between two letters, this channel either inserts an invisible
word joiner (U+2060) or does not. Present is a one, absent is a zero, so each
letter-letter boundary carries one bit. A word joiner has no width and does not
create a line-break opportunity, so nothing about the rendered text changes.

Unlike the substitution channels, this one changes the length of the text, so
it is not length-preserving. The main pipeline (analyze, encode, decode,
full-length identify) handles that fine because each call is internally
consistent: sites are defined on the base letters, which the insertions do not
disturb, so the k-th boundary is the same site whether or not a joiner sits in
it. Excerpt alignment, which relies on stable character offsets, cannot follow
this channel; align_excerpt reports that rather than guessing.

Invisible format characters are widely stripped by editors, chat platforms,
sanitizers, and normalizers, so this channel is fragile. It requires
RepertoirePolicy(allow_joiners=True) as well as selection in the channel list.
"""

from __future__ import annotations

from typing import List, Optional

from ...models import (
    ChannelMetadata,
    EmbeddingSite,
    Invariant,
    Observation,
    ObservationState,
    Risk,
)
from ..base import BaseChannel, ChannelContext, register_channel

_MARK = "\u2060"  # WORD JOINER: zero width, non-breaking


@register_channel
class ZeroWidthChannel(BaseChannel):
    id = "invisible.zero_width"
    version = "2"
    length_preserving = False
    required_permissions = ("allow_joiners",)

    def __init__(self) -> None:
        self.variants = ("", _MARK)

    def _scan(self, text: str):
        # Both discovery and observation consume the same boundary, including
        # any existing marks, so re-encoding replaces rather than skips them.
        for i, char in enumerate(text):
            if not char.isalpha():
                continue
            j = i + 1
            while j < len(text) and text[j] == _MARK:
                j += 1
            if j < len(text) and text[j].isalpha():
                yield i + 1, j

    def discover_sites(
        self, text: str, context: Optional[ChannelContext] = None
    ) -> List[EmbeddingSite]:
        return [EmbeddingSite(
            channel_id=self.id, ordinal=ordinal, start=start, end=end,
            variants=self.variants, canonical="",
        ) for ordinal, (start, end) in enumerate(self._scan(text))]

    def observe(
        self, text: str, context: Optional[ChannelContext] = None
    ) -> List[Observation]:
        return [Observation(
            channel_id=self.id, ordinal=ordinal, state=ObservationState.KNOWN,
            symbol=int(end > start), radix=2, raw=text[start:end],
            start=start, end=end,
        ) for ordinal, (start, end) in enumerate(self._scan(text))]

    def canonicalize(self, text: str) -> str:
        return text.replace(_MARK, "")

    def metadata(self) -> ChannelMetadata:
        return ChannelMetadata(
            channel_id=self.id,
            version=self.version,
            invariant=Invariant.RENDERED_TEXT,
            risk=Risk.HIGH,
            description=(
                "Encodes one bit at each letter-letter boundary by inserting or omitting "
                "an invisible word joiner (U+2060)."
            ),
            warnings=(
                "Invisible format characters are stripped by many editors, chat apps, "
                "sanitizers, and normalizers, which erases the signal.",
                "The channel changes the length of the text, so excerpt alignment is "
                "not available while it is enabled.",
            ),
        )
