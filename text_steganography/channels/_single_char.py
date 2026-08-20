"""A reusable base for single-character substitution channels.

Several channels work the same way: at certain positions a single character can
be swapped for a visually or typographically equivalent one, and the choice of
character is the symbol. Because every variant is exactly one code point long,
absolute offsets stay aligned between cover text and stegotext, and the k-th
site is trivially the same site on both sides.

A concrete channel sets ``variants`` (index is symbol value, ``variants[0]`` is
canonical), ``canonical``, implements :meth:`_eligible` to say which positions
qualify, and implements :meth:`metadata`.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import List, Optional, Tuple

from ..models import EmbeddingSite, Observation, ObservationState
from .base import BaseChannel, ChannelContext


class SingleCharSubstitutionChannel(BaseChannel):
    variants: Tuple[str, ...] = ()
    canonical: str = ""

    def __init__(self) -> None:
        self._variant_set = set(self.variants)

    @abstractmethod
    def _eligible(self, text: str, i: int) -> bool:
        """Whether position ``i`` qualifies as a site, given its neighbors."""

    def _is_site(self, text: str, i: int) -> bool:
        return (
            0 < i < len(text) - 1
            and text[i] in self._variant_set
            and self._eligible(text, i)
        )

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
                        variants=tuple(self.variants),
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
                        start=i,
                        end=i + 1,
                    )
                )
                ordinal += 1
        return observations

    def canonicalize(self, text: str) -> str:
        chars = list(text)
        for site in self.discover_sites(text):
            chars[site.start] = self.canonical
        return "".join(chars)
