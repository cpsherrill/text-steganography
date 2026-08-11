"""The Unicode-space channel.

At each single inter-word space, this channel chooses between an ordinary space
(U+0020) and a no-break space (U+00A0). The two render at the same width in
almost every font, so the choice is invisible to a reader, and it carries one
bit per eligible space.

A site is a space variant with a non-whitespace character on each side. That
definition is the same during encoding and decoding, so the k-th site found in
the cover text is the k-th site found in the stegotext even though no offsets
are stored. Runs of two or more spaces and leading or trailing spaces are
skipped, because they are ambiguous under collapsing transports.

This is the conservative starter channel. It is not robust: many editors and
platforms normalize a no-break space back to a plain space, which silently
erases the bit. That is a property of the transport, not a defect here, and
the compatibility work in a later phase is where it gets measured.
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

_SPACE = "\u0020"
_NBSP = "\u00a0"


@register_channel
class UnicodeSpaceChannel(BaseChannel):
    id = "whitespace.unicode_space"
    version = "1"

    def __init__(self) -> None:
        self.variants = (_SPACE, _NBSP)
        self.canonical = _SPACE
        self._variant_set = set(self.variants)

    def _is_site(self, text: str, i: int) -> bool:
        if not 0 < i < len(text) - 1:
            return False
        if text[i] not in self._variant_set:
            return False
        return not text[i - 1].isspace() and not text[i + 1].isspace()

    def discover_sites(
        self, text: str, context: Optional[ChannelContext] = None
    ) -> List[EmbeddingSite]:
        sites: List[EmbeddingSite] = []
        ordinal = 0
        for i in range(len(text)):
            if self._is_site(text, i):
                sites.append(
                    EmbeddingSite(
                        channel_id=self.id,
                        ordinal=ordinal,
                        start=i,
                        end=i + 1,
                        variants=self.variants,
                        canonical=self.canonical,
                    )
                )
                ordinal += 1
        return sites

    def observe(
        self, text: str, context: Optional[ChannelContext] = None
    ) -> List[Observation]:
        observations: List[Observation] = []
        ordinal = 0
        for i in range(len(text)):
            if self._is_site(text, i):
                char = text[i]
                symbol: Optional[int]
                try:
                    symbol = self.variants.index(char)
                    state = ObservationState.KNOWN
                except ValueError:
                    symbol = None
                    state = ObservationState.ERASED
                observations.append(
                    Observation(
                        channel_id=self.id,
                        ordinal=ordinal,
                        state=state,
                        symbol=symbol,
                        radix=len(self.variants),
                        raw=char,
                    )
                )
                ordinal += 1
        return observations

    def canonicalize(self, text: str) -> str:
        chars = list(text)
        for site in self.discover_sites(text):
            chars[site.start] = self.canonical
        return "".join(chars)

    def metadata(self) -> ChannelMetadata:
        return ChannelMetadata(
            channel_id=self.id,
            version=self.version,
            invariant=Invariant.RENDERED_TEXT,
            risk=Risk.MEDIUM,
            description=(
                "Encodes one bit at each single inter-word space by choosing between "
                "a regular space and a no-break space."
            ),
            warnings=(
                "A no-break space prevents line wrapping at that position, which can "
                "change how a paragraph lays out.",
                "Many editors, chat platforms, and normalizers convert no-break spaces "
                "back to regular spaces, which erases the encoded bit.",
            ),
        )
