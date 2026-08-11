"""Turn a probe measurement into a reusable profile.

This is the empirical path: run a probe through a real transport, feed the
returned text here, and get a :class:`Profile` labeled from what actually
survived. Save it, and later configurations can consult it as advisory
defaults.
"""

from __future__ import annotations

from ..probe.harness import Probe
from .model import Profile


def profile_from_probe(
    name: str,
    description: str,
    probe: Probe,
    returned_text: str,
    *,
    evidence: str,
) -> Profile:
    """Build a profile from a probe and the text a transport returned."""
    report = probe.evaluate(returned_text)
    recommendations = {survival.channel_id: survival.label for survival in report.per_channel}
    return Profile(
        name=name,
        description=description,
        recommendations=recommendations,
        evidence=evidence,
    )
