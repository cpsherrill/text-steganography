"""Build a transport probe and evaluate what came back.

The workflow has three steps that usually happen on different machines:

1. ``build_probe(config)`` produces a :class:`Probe`. Send ``probe.stego``
   through the transport under test.
2. The transport returns some text.
3. ``probe.evaluate(returned_text)`` reports what survived, per channel.

A probe serializes to and from a dict, so step 1 and step 3 can be separated in
time: save the probe, send the sample, come back later with the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..config import CodecConfig
from ..core.planner import build_plan
from .model import ChannelSurvival, ProbeReport

# A diagnostic cover with plenty of single spaces and several contractions, so
# both shipped channels have sites to exercise.
DEFAULT_DIAGNOSTIC = (
    "Here's a diagnostic paragraph for the transport probe. It's plain prose, "
    "but it's built to give the channels something to bite on: lots of single "
    "spaces between ordinary words, and a scatter of contractions like don't, "
    "can't, won't, and it's again. "
) * 3


@dataclass
class Probe:
    """A diagnostic sample plus the symbols it was built to carry."""

    config: CodecConfig
    cover: str
    stego: str
    expected: Dict[str, List[Optional[int]]]

    def evaluate(self, returned_text: str) -> ProbeReport:
        """Compare returned text against what was sent, site by site."""
        survivals: List[ChannelSurvival] = []
        total_expected = 0
        total_matched = 0
        for channel in self.config.channels:
            expected = self.expected.get(channel.id, [])
            observed = [obs.symbol for obs in channel.observe(returned_text)]
            matched = 0
            substituted = 0
            for i in range(min(len(expected), len(observed))):
                seen = observed[i]
                if seen is None:
                    continue
                if seen == expected[i]:
                    matched += 1
                else:
                    substituted += 1
            survivals.append(
                ChannelSurvival(
                    channel_id=channel.id,
                    expected_sites=len(expected),
                    observed_sites=len(observed),
                    matched=matched,
                    substituted=substituted,
                    site_delta=len(observed) - len(expected),
                )
            )
            total_expected += len(expected)
            total_matched += matched
        overall = (total_matched / total_expected) if total_expected else 0.0
        return ProbeReport(per_channel=tuple(survivals), overall_survival=overall)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "cover": self.cover,
            "stego": self.stego,
            "expected": {key: list(value) for key, value in self.expected.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Probe":
        return cls(
            config=CodecConfig.from_dict(data["config"]),
            cover=data["cover"],
            stego=data["stego"],
            expected={key: list(value) for key, value in data["expected"].items()},
        )


def build_probe(config: CodecConfig, cover: Optional[str] = None) -> Probe:
    """Build a probe whose every site carries its most unusual variant.

    Setting each site to its highest-index variant (a no-break space rather
    than a space, a right single quote rather than a straight one) means any
    transport that normalizes toward the plain form shows up as a substitution,
    which is exactly the failure a probe should surface.
    """
    cover = DEFAULT_DIAGNOSTIC if cover is None else cover
    plan = build_plan(config, cover)

    edits = []
    for planned in plan.planned_sites:
        site = planned.site
        symbol = site.radix - 1  # the most unusual variant available
        variant = site.variants[symbol]
        if variant != cover[site.start : site.end]:
            edits.append((site.start, site.end, variant))

    edits.sort(key=lambda edit: edit[0], reverse=True)
    stego = cover
    for start, end, replacement in edits:
        stego = stego[:start] + replacement + stego[end:]

    expected = {
        channel.id: [obs.symbol for obs in channel.observe(stego)]
        for channel in config.channels
    }
    return Probe(config=config, cover=cover, stego=stego, expected=expected)
