"""A small registry of built-in profiles.

These are honestly labeled. ``lossless`` and ``unicode_nfkc`` describe
deterministic, verifiable behavior; ``plain_text_conservative`` is a cautious
default rather than a measurement, and its evidence string says so. Real
transports (a named email client, a specific CMS) should be captured with
``profile_from_probe`` against an actual round trip, not guessed here.
"""

from __future__ import annotations

from typing import Dict, List

from ..probe.model import SurvivalLabel
from .model import Profile

_SPACE = "whitespace.unicode_space"
_APOSTROPHE = "punctuation.apostrophe"


_BUILTIN: Dict[str, Profile] = {
    "lossless": Profile(
        name="lossless",
        description="No transformation: in-memory strings, or a byte-exact file round trip.",
        recommendations={
            _SPACE: SurvivalLabel.RECOMMENDED,
            _APOSTROPHE: SurvivalLabel.RECOMMENDED,
        },
        evidence="identity transform; nothing is altered",
    ),
    "unicode_nfkc": Profile(
        name="unicode_nfkc",
        description="Any path that applies Unicode NFKC (compatibility) normalization.",
        recommendations={
            # NFKC maps a no-break space to a plain space, flattening the channel.
            _SPACE: SurvivalLabel.UNSUPPORTED,
            # The right single quote is not touched by NFKC.
            _APOSTROPHE: SurvivalLabel.RECOMMENDED,
        },
        evidence="derived from deterministic NFKC normalization behavior",
    ),
    "plain_text_conservative": Profile(
        name="plain_text_conservative",
        description="Generic plain text with unknown downstream handling.",
        recommendations={
            _SPACE: SurvivalLabel.CONDITIONAL,
            _APOSTROPHE: SurvivalLabel.CONDITIONAL,
        },
        evidence="conservative default, not measured against a specific transport",
    ),
}


def list_profiles() -> List[str]:
    return sorted(_BUILTIN)


def get_profile(name: str) -> Profile:
    try:
        return _BUILTIN[name]
    except KeyError:
        raise KeyError(f"unknown profile {name!r}; known: {', '.join(sorted(_BUILTIN))}") from None
