"""The embedding planner.

Given a configuration and a cover text, the planner asks every channel for its
sites, checks that no two channels claim overlapping spans, and returns an
ordered plan. Silent overlaps would make capacity estimates and decoding
unreliable, so an overlap is a hard error rather than a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

from ..carriers.spans import site_in_spans
from ..errors import ConflictError
from ..models import EmbeddingSite
from .site_ordering import PlannedSite, order_sites

if TYPE_CHECKING:
    from ..config import CodecConfig


@dataclass
class EmbeddingPlan:
    """The ordered sites for one cover text under one configuration."""

    cover_text: str
    planned_sites: List[PlannedSite]
    warnings: List[str] = field(default_factory=list)

    @property
    def capacity_bits(self) -> int:
        return sum(planned.width for planned in self.planned_sites)


def _detect_conflicts(sites: List[EmbeddingSite]) -> None:
    spans = sorted(
        (site.start, site.end, site.channel_id) for site in sites if site.end > site.start
    )
    for (start_a, end_a, channel_a), (start_b, end_b, channel_b) in zip(spans, spans[1:]):
        if start_b < end_a:
            raise ConflictError(
                f"channels {channel_a!r} and {channel_b!r} claim overlapping spans "
                f"[{start_a},{end_a}) and [{start_b},{end_b})"
            )


def build_plan(config: "CodecConfig", text: str) -> EmbeddingPlan:
    """Discover and order every site for ``text`` under ``config``.

    Sites are restricted to the carrier's safe spans, so channels never touch a
    tag, an attribute, a URL, or code. The plain-text carrier reports the whole
    document, leaving discovery unrestricted.
    """
    spans = config.carrier.safe_spans(text)
    per_channel: List[List[EmbeddingSite]] = []
    all_sites: List[EmbeddingSite] = []
    for channel in config.channels:
        sites = [
            site
            for site in channel.discover_sites(text)
            if site_in_spans(site.start, site.end, spans)
        ]
        per_channel.append(sites)
        all_sites.extend(sites)
    _detect_conflicts(all_sites)
    return EmbeddingPlan(cover_text=text, planned_sites=order_sites(per_channel))
