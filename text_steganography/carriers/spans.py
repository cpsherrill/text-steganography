"""Span arithmetic shared by carrier adapters.

A carrier reports the character ranges of a document where embedding is safe.
These helpers merge and invert ranges and test membership. Spans are
half-open ``(start, end)`` pairs.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

Span = Tuple[int, int]


def merge_spans(spans: Sequence[Span]) -> List[Span]:
    """Sort and coalesce overlapping or touching spans."""
    cleaned = sorted((max(0, s), e) for s, e in spans if e > s)
    merged: List[Span] = []
    for start, end in cleaned:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def invert_spans(unsafe: Sequence[Span], total: int) -> List[Span]:
    """Return the complement of ``unsafe`` within ``[0, total)``."""
    if total <= 0:
        return []
    safe: List[Span] = []
    cursor = 0
    for start, end in merge_spans(unsafe):
        start = max(0, min(start, total))
        end = max(0, min(end, total))
        if start > cursor:
            safe.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < total:
        safe.append((cursor, total))
    return safe


def position_in_spans(position: int, spans: Sequence[Span]) -> bool:
    """Whether a single character offset falls inside any span."""
    return any(start <= position < end for start, end in spans)


def site_in_spans(start: int, end: int, spans: Sequence[Span]) -> bool:
    """Whether the whole half-open range ``[start, end)`` fits inside a span."""
    return any(span_start <= start and end <= span_end for span_start, span_end in spans)
