"""Deterministic site ordering.

Both encoding and decoding must enumerate sites in the same order. The order is
channel-major: configuration channel order first, then each channel's own scan
order (which is text position for the channels shipped so far). Two runs of the
same configuration over the same text therefore agree on every site's index.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from ..models import EmbeddingSite
from .symbol_packing import site_bit_width


@dataclass(frozen=True)
class PlannedSite:
    """A site paired with its channel's position and its bit width."""

    channel_index: int
    site: EmbeddingSite
    width: int


def order_sites(per_channel_sites: Sequence[Sequence[EmbeddingSite]]) -> List[PlannedSite]:
    """Flatten per-channel site lists into one channel-major ordering."""
    planned: List[PlannedSite] = []
    for channel_index, sites in enumerate(per_channel_sites):
        for site in sites:
            planned.append(PlannedSite(channel_index, site, site_bit_width(site.radix)))
    return planned
