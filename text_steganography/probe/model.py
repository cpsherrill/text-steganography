"""Data model for the transport probe.

A probe is a diagnostic stegotext with a known symbol at every site. After it
travels through a real transport (an email path, a chat client, a CMS editor)
the returned text is compared site by site against what was sent, which
measures what that transport actually preserves rather than what a table
guesses it preserves.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SurvivalLabel(str, Enum):
    """A channel's measured fitness for a transport, coarsely bucketed."""

    RECOMMENDED = "recommended"
    CONDITIONAL = "conditional"
    FRAGILE = "fragile"
    UNSUPPORTED = "unsupported"
    UNTESTED = "untested"


def label_for(rate: Optional[float]) -> SurvivalLabel:
    """Bucket a survival rate into a label."""
    if rate is None:
        return SurvivalLabel.UNTESTED
    if rate >= 0.999:
        return SurvivalLabel.RECOMMENDED
    if rate >= 0.75:
        return SurvivalLabel.CONDITIONAL
    if rate > 0.0:
        return SurvivalLabel.FRAGILE
    return SurvivalLabel.UNSUPPORTED


@dataclass(frozen=True)
class ChannelSurvival:
    """How one channel fared through a transport."""

    channel_id: str
    expected_sites: int
    observed_sites: int
    matched: int
    substituted: int
    site_delta: int

    @property
    def survival_rate(self) -> Optional[float]:
        """Fraction of expected sites recovered exactly, or None if untested."""
        if self.expected_sites == 0:
            return None
        return self.matched / self.expected_sites

    @property
    def label(self) -> SurvivalLabel:
        return label_for(self.survival_rate)


@dataclass(frozen=True)
class ProbeReport:
    """The per-channel outcome of a round trip."""

    per_channel: Tuple[ChannelSurvival, ...]
    overall_survival: float

    def summary(self) -> str:
        parts = [f"overall {self.overall_survival * 100:.0f}% survived"]
        for channel in self.per_channel:
            rate = channel.survival_rate
            shown = "n/a" if rate is None else f"{rate * 100:.0f}%"
            parts.append(f"{channel.channel_id}: {shown} [{channel.label.value}]")
        return "; ".join(parts)
