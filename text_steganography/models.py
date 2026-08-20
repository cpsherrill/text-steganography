"""Immutable data model shared across the library.

These types are the vocabulary from the design document turned into code:
sites, observations, capacity reports, and the results returned by encode and
decode. They are frozen dataclasses so they can be logged, hashed, compared,
and safely passed between components without defensive copying.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Invariant(str, Enum):
    """What a channel promises to preserve.

    Changing characters necessarily changes the byte sequence, so "lossless"
    is defined against one of these invariants rather than byte identity.
    """

    CANONICAL_TEXT = "canonical_text"
    RENDERED_TEXT = "rendered_text"
    SEMANTIC = "semantic"
    STRUCTURAL = "structural"


class Risk(str, Enum):
    """Coarse risk rating for a channel, used in warnings and profiles."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ChannelMetadata:
    """Self-description a channel returns for diagnostics and safety."""

    channel_id: str
    version: str
    invariant: Invariant
    risk: Risk
    description: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class EmbeddingSite:
    """One location where a channel can make a representational choice.

    A site is identified by its channel and its ``ordinal`` (the k-th site the
    channel finds, in scan order). The ``variants`` are concrete literal
    strings; the index of a variant is the symbol value it encodes, so
    ``variants[0]`` is the canonical form by convention. ``start`` and ``end``
    locate the span in the text the site was discovered in; they are advisory
    for decoding, which relies on ordinal correspondence rather than absolute
    offsets.
    """

    channel_id: str
    ordinal: int
    start: int
    end: int
    variants: tuple[str, ...]
    canonical: str

    @property
    def radix(self) -> int:
        return len(self.variants)


class ObservationState(str, Enum):
    """The state of a single decoded site."""

    KNOWN = "known"
    ERASED = "erased"
    AMBIGUOUS = "ambiguous"
    INVALID = "invalid"


@dataclass(frozen=True)
class Observation:
    """What decoding saw at one site.

    A rich observation is kept on purpose: reducing everything immediately to a
    guessed bit throws away the erasure and ambiguity information that later
    error correction and candidate identification need.
    """

    channel_id: str
    ordinal: int
    state: ObservationState
    symbol: Optional[int] = None
    possible_symbols: tuple[int, ...] = ()
    radix: int = 0
    raw: str = ""
    start: int = -1
    end: int = -1


@dataclass(frozen=True)
class ChannelCapacity:
    """Capacity contributed by one channel for a specific text."""

    channel_id: str
    sites: int
    raw_bits: float
    packed_bits: int


@dataclass(frozen=True)
class CapacityReport:
    """The result of ``analyze``: how much a text can carry under a config.

    Theoretical, realizable, overhead, and usable figures are reported
    separately so the numbers never quietly conflate raw entropy with what a
    robust payload can actually use.
    """

    total_sites: int
    per_channel: tuple[ChannelCapacity, ...]
    raw_theoretical_bits: float
    realizable_packed_bits: int
    framing_overhead_bits: int
    integrity_overhead_bits: int
    ecc_overhead_bits: int
    usable_payload_bits: int
    usable_payload_bytes: int
    max_distinct_payloads: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class EncodeResult:
    """The result of ``encode``."""

    text: str
    codec_id: str
    payload_size: int
    sites_total: int
    sites_used: int
    unused_capacity_bits: int
    frame_version: int
    warnings: tuple[str, ...] = ()


class DecodeStatus(str, Enum):
    """Outcome category for a decode attempt."""

    SUCCESS = "success"
    PARTIAL = "partial"
    AMBIGUOUS = "ambiguous"
    INVALID = "invalid"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class DecodeResult:
    """The structured result of ``decode``.

    On success ``payload`` holds the recovered bytes. When decoding does not
    fully succeed, ``payload`` is ``None`` and the counts and ``observations``
    remain usable by later analysis.
    """

    status: DecodeStatus
    payload: Optional[bytes]
    codec_id: str
    frame_version: Optional[int] = None
    integrity_valid: Optional[bool] = None
    observed_sites: int = 0
    known_symbols: int = 0
    erasures: int = 0
    corrected_errors: int = 0
    observations: tuple[Observation, ...] = ()
    warnings: tuple[str, ...] = ()
