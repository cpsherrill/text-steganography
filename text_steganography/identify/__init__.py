"""Candidate identification and fingerprint preflight.

Given a leaked copy and the set of payloads that were distributed, decide which
of them could have produced the copy. This works on a full-length text whose
sites may have been normalized or flipped; arbitrary excerpts need the fragment
alignment planned for a later phase.
"""

from __future__ import annotations

from .matcher import evaluate_candidate, hamming, identify_bits, min_pairwise_distance
from .models import CandidateMatch, FingerprintPreflight, IdentificationResult

__all__ = [
    "CandidateMatch",
    "IdentificationResult",
    "FingerprintPreflight",
    "identify_bits",
    "evaluate_candidate",
    "hamming",
    "min_pairwise_distance",
]
