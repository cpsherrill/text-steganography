"""A canonical-equivalence channel.

Some visible characters can be written two canonically equivalent ways: a single
precomposed code point, or a base letter followed by combining marks. An
accented ``e`` is either U+00E9, or U+0065 followed by U+0301. Both render the
same. This channel encodes a bit at each such character by choosing the
composed form (zero) or the decomposed form (one).

Only true canonical equivalence is used (NFC and NFD round-trip), never
compatibility equivalence, which can change meaning. Both composed and fully
decomposed normalization units are recognized, including Hangul. Units that
cannot be represented by one composed character are left alone. The canonical
form of each eligible site is its composed form.

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
    version = "2"
    length_preserving = False

    def _scan(self, text: str) -> Iterator[_Site]:
        # A normalization unit includes trailing combining marks and adjacent
        # starters that compose (notably Hangul L/V/T Jamo). Never encode a
        # prefix of a larger unit: decomposition would change its boundaries.
        i = 0
        while i < len(text):
            j = i + 1
            sequence = text[i:j]
            while j < len(text):
                extended = sequence + text[j]
                if (unicodedata.combining(text[j]) != 0
                        or len(unicodedata.normalize("NFC", extended)) == 1):
                    sequence = extended
                    j += 1
                else:
                    break
            composed = unicodedata.normalize("NFC", sequence)
            decomposed = unicodedata.normalize("NFD", sequence)
            if (len(composed) == 1 and len(decomposed) > 1
                    and sequence in (composed, decomposed)):
                yield (i, j, (composed, decomposed), int(sequence == decomposed))
            i = j

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
