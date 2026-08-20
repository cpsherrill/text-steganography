"""A canonical-equivalence channel.

Some visible characters can be written two canonically equivalent ways: a single
precomposed code point, or a base letter followed by combining marks. An
accented ``e`` is either U+00E9, or U+0065 followed by U+0301. Both render the
same. This channel encodes a bit at each such character by choosing the
composed form (zero) or the decomposed form (one).

Only true canonical equivalence is used (NFC and NFD round-trip), never
compatibility equivalence, which can change meaning. The channel assumes the
cover is in composed (NFC) form, which nearly all text is; its canonical form is
the composed one.

The decomposed form is longer than the composed one, so this channel is not
length-preserving. The main pipeline handles that; excerpt alignment does not,
and align_excerpt reports "unsupported" when it is enabled. The channel is
highly fragile: any NFC normalization step anywhere in the path erases every
decomposed choice, which is exactly why it is a good teaching example of why
transport matters.
"""

from __future__ import annotations

import unicodedata
from typing import Iterator, List, Optional, Tuple

from ..models import (
    ChannelMetadata,
    EmbeddingSite,
    Invariant,
    Observation,
    ObservationState,
    Risk,
)
from .base import BaseChannel, ChannelContext, register_channel

# (start, end, (composed, decomposed), current_symbol)
_Site = Tuple[int, int, Tuple[str, str], int]


@register_channel
class CanonicalUnicodeChannel(BaseChannel):
    id = "unicode.canonical"
    version = "1"
    length_preserving = False

    def _scan(self, text: str) -> Iterator[_Site]:
        n = len(text)
        i = 0
        while i < n:
            char = text[i]
            decomposed = unicodedata.normalize("NFD", char)
            if len(decomposed) > 1 and unicodedata.normalize("NFC", decomposed) == char:
                # a precomposed character sitting in composed form (symbol 0)
                yield (i, i + 1, (char, decomposed), 0)
                i += 1
                continue
            if (
                unicodedata.combining(char) == 0
                and i + 1 < n
                and unicodedata.combining(text[i + 1]) > 0
            ):
                j = i + 1
                while j < n and unicodedata.combining(text[j]) > 0:
                    j += 1
                sequence = text[i:j]
                composed = unicodedata.normalize("NFC", sequence)
                if len(composed) == 1 and unicodedata.normalize("NFD", composed) == sequence:
                    # a base plus combining marks in decomposed form (symbol 1)
                    yield (i, j, (composed, sequence), 1)
                    i = j
                    continue
            i += 1

    def discover_sites(
        self, text: str, context: Optional[ChannelContext] = None
    ) -> List[EmbeddingSite]:
        sites: List[EmbeddingSite] = []
        for ordinal, (start, end, variants, _symbol) in enumerate(self._scan(text)):
            sites.append(
                EmbeddingSite(
                    channel_id=self.id,
                    ordinal=ordinal,
                    start=start,
                    end=end,
                    variants=variants,
                    canonical=variants[0],
                )
            )
        return sites

    def observe(
        self, text: str, context: Optional[ChannelContext] = None
    ) -> List[Observation]:
        observations: List[Observation] = []
        for ordinal, (start, end, variants, symbol) in enumerate(self._scan(text)):
            observations.append(
                Observation(
                    channel_id=self.id,
                    ordinal=ordinal,
                    state=ObservationState.KNOWN,
                    symbol=symbol,
                    radix=2,
                    raw=text[start:end],
                    start=start,
                    end=end,
                )
            )
        return observations

    def canonicalize(self, text: str) -> str:
        result: List[str] = []
        last = 0
        for start, end, variants, _symbol in self._scan(text):
            result.append(text[last:start])
            result.append(variants[0])
            last = end
        result.append(text[last:])
        return "".join(result)

    def metadata(self) -> ChannelMetadata:
        return ChannelMetadata(
            channel_id=self.id,
            version=self.version,
            invariant=Invariant.CANONICAL_TEXT,
            risk=Risk.HIGH,
            description=(
                "Encodes one bit at each precomposed character by choosing its composed "
                "or canonically-equivalent decomposed form."
            ),
            warnings=(
                "Any NFC normalization on the path recomposes every character and erases "
                "the whole signal; this channel only survives transports known not to "
                "normalize.",
                "The channel changes the length of the text, so excerpt alignment is not "
                "available while it is enabled.",
            ),
        )
