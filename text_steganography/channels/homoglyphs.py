"""A cross-script homoglyph channel.

Some letters have look-alikes in another script that render identically in
almost every font. This channel encodes a bit at each such letter by choosing
between the Latin form and its Cyrillic twin: a Latin ``o`` (U+006F) or a
Cyrillic ``о`` (U+043E), and so on. The reader sees the same word; the code
points differ.

This is the highest-risk channel in the library and it is opt-in by the act of
adding it to a configuration. Cross-script text trips phishing and
spoofing detectors, breaks exact search and sorting, confuses screen readers,
and is often rejected or normalized. Its variants are still single code points,
so it is length-preserving and works with excerpt alignment and carriers, but
its risk metadata says plainly what it costs.

The channel claims every confusable character it knows, in either script, so a
cover text that already mixes scripts is not a good fit; use it on Latin text.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..models import (
    ChannelMetadata,
    EmbeddingSite,
    Invariant,
    Observation,
    ObservationState,
    Risk,
)
from .base import BaseChannel, ChannelContext, register_channel

# Latin letter -> its Cyrillic homoglyph. Every pair renders identically in
# common fonts. Written as escapes so the code points cannot drift.
_LATIN_TO_CYRILLIC = {
    "a": "\u0430",
    "c": "\u0441",
    "e": "\u0435",
    "o": "\u043e",
    "p": "\u0440",
    "x": "\u0445",
    "y": "\u0443",
    "A": "\u0410",
    "B": "\u0412",
    "C": "\u0421",
    "E": "\u0415",
    "H": "\u041d",
    "K": "\u041a",
    "M": "\u041c",
    "O": "\u041e",
    "P": "\u0420",
    "T": "\u0422",
    "X": "\u0425",
    "Y": "\u0423",
}

# Every variant character maps to its (Latin-first) variant tuple.
_CHAR_TO_VARIANTS: Dict[str, Tuple[str, str]] = {}
for _latin, _cyrillic in _LATIN_TO_CYRILLIC.items():
    _pair = (_latin, _cyrillic)
    _CHAR_TO_VARIANTS[_latin] = _pair
    _CHAR_TO_VARIANTS[_cyrillic] = _pair


@register_channel
class CyrillicHomoglyphChannel(BaseChannel):
    id = "homoglyph.cyrillic"
    version = "1"
    length_preserving = True

    def discover_sites(
        self, text: str, context: Optional[ChannelContext] = None
    ) -> List[EmbeddingSite]:
        sites: List[EmbeddingSite] = []
        ordinal = 0
        for i, char in enumerate(text):
            variants = _CHAR_TO_VARIANTS.get(char)
            if variants is None:
                continue
            sites.append(
                EmbeddingSite(
                    channel_id=self.id,
                    ordinal=ordinal,
                    start=i,
                    end=i + 1,
                    variants=variants,
                    canonical=variants[0],
                )
            )
            ordinal += 1
        return sites

    def observe(
        self, text: str, context: Optional[ChannelContext] = None
    ) -> List[Observation]:
        observations: List[Observation] = []
        ordinal = 0
        for i, char in enumerate(text):
            variants = _CHAR_TO_VARIANTS.get(char)
            if variants is None:
                continue
            symbol = variants.index(char)
            observations.append(
                Observation(
                    channel_id=self.id,
                    ordinal=ordinal,
                    state=ObservationState.KNOWN,
                    symbol=symbol,
                    radix=len(variants),
                    raw=char,
                    start=i,
                    end=i + 1,
                )
            )
            ordinal += 1
        return observations

    def canonicalize(self, text: str) -> str:
        chars = list(text)
        for i, char in enumerate(chars):
            variants = _CHAR_TO_VARIANTS.get(char)
            if variants is not None:
                chars[i] = variants[0]
        return "".join(chars)

    def metadata(self) -> ChannelMetadata:
        return ChannelMetadata(
            channel_id=self.id,
            version=self.version,
            invariant=Invariant.RENDERED_TEXT,
            risk=Risk.HIGH,
            description=(
                "Encodes one bit at each confusable letter by choosing between its "
                "Latin form and an identical-looking Cyrillic homoglyph."
            ),
            warnings=(
                "Mixed-script text triggers phishing and spoofing detectors and may be "
                "rejected outright.",
                "It breaks exact search, sorting, and word matching, and can mislead "
                "screen readers.",
                "Many systems normalize or strip cross-script confusables. This channel "
                "should be off in any conservative configuration.",
            ),
        )
