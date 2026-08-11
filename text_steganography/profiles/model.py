"""Compatibility profiles: advisory, not binding.

A profile records, for one carrier/transport, how each channel is expected to
fare, using the same Recommended / Conditional / Fragile / Unsupported labels
the probe produces. Profiles are recommendations, never restrictions: they can
warn, but the configuration stays entirely under the caller's control. Keeping
capabilities (what the software can encode), recommendations (this), and
configuration (what the caller chooses) as three separate layers is deliberate.

A profile carries an ``evidence`` string on purpose. "Works in email" is too
broad to be honest; "measured 2026-08-11 through a specific client path" or
"conservative default, not measured" is the kind of claim a profile should
make, per the design's note on versioned evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List

from ..probe.model import SurvivalLabel

if TYPE_CHECKING:
    from ..config import CodecConfig


@dataclass(frozen=True)
class Profile:
    """A named set of per-channel recommendations for one environment."""

    name: str
    description: str
    recommendations: Dict[str, SurvivalLabel]
    evidence: str = "unspecified"

    def recommendation_for(self, channel_id: str) -> SurvivalLabel:
        return self.recommendations.get(channel_id, SurvivalLabel.UNTESTED)

    def warnings_for(self, config: "CodecConfig") -> List[str]:
        """Advisory warnings for the channels a config uses under this profile."""
        messages: List[str] = []
        for channel in config.channels:
            label = self.recommendation_for(channel.id)
            if label is SurvivalLabel.UNSUPPORTED:
                messages.append(
                    f"channel {channel.id!r} is unsupported under profile {self.name!r}; "
                    f"expect the signal to be destroyed"
                )
            elif label is SurvivalLabel.FRAGILE:
                messages.append(
                    f"channel {channel.id!r} is fragile under profile {self.name!r}; "
                    f"add redundancy or expect losses"
                )
            elif label is SurvivalLabel.UNTESTED:
                messages.append(
                    f"channel {channel.id!r} is untested under profile {self.name!r}"
                )
        return messages

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "evidence": self.evidence,
            "recommendations": {
                channel_id: label.value for channel_id, label in self.recommendations.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profile":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            recommendations={
                channel_id: SurvivalLabel(value)
                for channel_id, value in data.get("recommendations", {}).items()
            },
            evidence=data.get("evidence", "unspecified"),
        )
