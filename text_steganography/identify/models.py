"""Result types for candidate identification and fingerprint preflight."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class CandidateMatch:
    """How one candidate payload compares against the surviving evidence."""

    index: int
    payload: bytes
    consistent: bool
    contradictions: int
    matches: int
    erasures: int
    compared: int
    feasible: bool


@dataclass(frozen=True)
class IdentificationResult:
    """The outcome of comparing observed text against a candidate set.

    ``ranking`` is always ``"distance"``: candidates are ordered by how many
    observed positions contradict them. It is a Hamming distance over the
    surviving evidence, not a calibrated probability, and the field name says
    so on purpose.
    """

    ranking: str
    observed_bits: int
    known_bits: int
    erased_bits: int
    candidates_total: int
    consistent: Tuple[CandidateMatch, ...]
    ranked: Tuple[CandidateMatch, ...]

    @property
    def ambiguity(self) -> int:
        """How many candidates remain fully consistent with the evidence."""
        return len(self.consistent)

    @property
    def unique(self) -> bool:
        """True when exactly one candidate is consistent."""
        return len(self.consistent) == 1

    def best(self) -> Optional[CandidateMatch]:
        """The closest candidate by distance, or None if there were none."""
        return self.ranked[0] if self.ranked else None


@dataclass(frozen=True)
class FingerprintPreflight:
    """A check over a whole set of fingerprints before distribution."""

    count: int
    capacity_bits: int
    usable_payload_bytes: int
    all_fit: bool
    all_distinct: bool
    min_pairwise_distance: Optional[int]

    @property
    def ok(self) -> bool:
        """True when every fingerprint fits and they are all distinct."""
        return self.all_fit and self.all_distinct
