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
sanitizers, and normalizers, so this channel is fragile. It is opt-in by the
act of adding it to a configuration.
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
    version = "1"
    length_preserving = False

    def __init__(self) -> None:
        self.variants = ("", _MARK)

    def discover_sites(
        self, text: str, context: Optional[ChannelContext] = None
    ) -> List[EmbeddingSite]:
        sites: List[EmbeddingSite] = []
        ordinal = 0
        for i in range(1, len(text)):
            if text[i - 1].isalpha() and text[i].isalpha():
                sites.append(
                    EmbeddingSite(
                        channel_id=self.id,
                        ordinal=ordinal,
                        start=i,
                        end=i,  # a zero-width insertion point
                        variants=self.variants,
                        canonical="",
                    )
                )
                ordinal += 1
        return sites

    def observe(
        self, text: str, context: Optional[ChannelContext] = None
    ) -> List[Observation]:
        observations: List[Observation] = []
        ordinal = 0
        prev_was_letter = False
        mark_since_prev = False
        for i, char in enumerate(text):
            if char == _MARK:
                mark_since_prev = True
                continue
            if char.isalpha():
                if prev_was_letter:
                    symbol = 1 if mark_since_prev else 0
                    observations.append(
                        Observation(
                            channel_id=self.id,
                            ordinal=ordinal,
                            state=ObservationState.KNOWN,
                            symbol=symbol,
                            radix=2,
                            raw=_MARK if symbol else "",
                            start=i,
                            end=i,
                        )
                    )
                    ordinal += 1
                prev_was_letter = True
                mark_since_prev = False
            else:
                prev_was_letter = False
                mark_since_prev = False
        return observations

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
