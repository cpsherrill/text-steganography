"""The comparison engine for candidate identification.

These functions are pure: they operate on bit vectors, not text. The observed
vector is one bit per site position, where ``None`` marks a site whose value
did not survive (an erasure). Each candidate is compared position by position
over the surviving evidence.

A candidate is *consistent* when it contradicts nothing observed. It is *ranked*
by how many observed positions it does contradict. Identification is not the
same problem as error correction: it can narrow a leaked copy to a few sources
even when no single payload can be decoded, because it only asks which known
payloads the evidence still permits.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .models import CandidateMatch, IdentificationResult


def evaluate_candidate(
    slots: Sequence[Optional[int]], expected: Sequence[int], capacity: int
) -> Tuple[bool, int, int, int]:
    """Compare one candidate's expected bits against the observation.

    Returns (feasible, contradictions, matches, compared). Positions beyond the
    candidate's own length are treated as expected-zero padding, matching how
    unused sites are encoded. A candidate whose codeword is longer than the
    available capacity is infeasible: it could not have produced this text.
    """
    feasible = len(expected) <= capacity
    contradictions = 0
    matches = 0
    compared = 0
    for i in range(capacity):
        observed = slots[i]
        if observed is None:
            continue
        expected_bit = expected[i] if i < len(expected) else 0
        compared += 1
        if observed == expected_bit:
            matches += 1
        else:
            contradictions += 1
    return feasible, contradictions, matches, compared


def identify_bits(
    slots: Sequence[Optional[int]],
    candidates: Sequence[Tuple[bytes, Sequence[int]]],
) -> IdentificationResult:
    """Rank ``candidates`` (payload, expected-bits) against ``slots``."""
    capacity = len(slots)
    erased = sum(1 for slot in slots if slot is None)
    known = capacity - erased

    matches: List[CandidateMatch] = []
    for index, (payload, expected) in enumerate(candidates):
        feasible, contradictions, matched, compared = evaluate_candidate(
            slots, expected, capacity
        )
        matches.append(
            CandidateMatch(
                index=index,
                payload=payload,
                consistent=feasible and contradictions == 0,
                contradictions=contradictions,
                matches=matched,
                erasures=erased,
                compared=compared,
                feasible=feasible,
            )
        )

    consistent = tuple(sorted((m for m in matches if m.consistent), key=lambda m: -m.matches))
    ranked = tuple(
        sorted(matches, key=lambda m: (0 if m.feasible else 1, m.contradictions, -m.matches))
    )
    return IdentificationResult(
        ranking="distance",
        observed_bits=capacity,
        known_bits=known,
        erased_bits=erased,
        candidates_total=len(candidates),
        consistent=consistent,
        ranked=ranked,
    )


def hamming(a: Sequence[int], b: Sequence[int]) -> int:
    """Hamming distance between two equal-length bit vectors."""
    if len(a) != len(b):
        raise ValueError("vectors must be the same length")
    return sum(1 for x, y in zip(a, b) if x != y)


def min_pairwise_distance(vectors: Sequence[Sequence[int]]) -> Optional[int]:
    """Smallest Hamming distance between any two of ``vectors``.

    Returns ``None`` when there are fewer than two vectors to compare.
    """
    if len(vectors) < 2:
        return None
    best: Optional[int] = None
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            distance = hamming(vectors[i], vectors[j])
            if best is None or distance < best:
                best = distance
    return best
