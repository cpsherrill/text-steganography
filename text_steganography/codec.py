"""The public codec: analyze, encode, decode, canonicalize.

A :class:`TextSteganographyCodec` wraps a configuration and exposes the whole
Phase 1 workflow. Encoding never silently truncates: a payload that does not
fit raises :class:`CapacityError`. Decoding never silently lies: a frame whose
checksum fails comes back as ``INVALID`` with no payload rather than as bytes.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence

from .config import CodecConfig
from .core.bits import bits_to_bytes, bytes_to_bits, int_to_bits
from .core.planner import build_plan
from .core.symbol_packing import pack_bits_into_symbols, site_bit_width, sites_consumed
from .errors import CapacityError
from .identify.matcher import identify_bits, min_pairwise_distance
from .identify.models import FingerprintPreflight, IdentificationResult
from .models import (
    CapacityReport,
    ChannelCapacity,
    DecodeResult,
    DecodeStatus,
    EncodeResult,
    Observation,
    ObservationState,
)
from .payload.framing import (
    FRAME_VERSION,
    HEADER_LEN,
    MAGIC,
    OVERHEAD_BYTES,
    frame,
    unframe,
)

_HEADER_BITS = HEADER_LEN * 8  # magic + version + length
_CRC_BITS = 32
_FRAMING_OVERHEAD_BITS = _HEADER_BITS
_INTEGRITY_OVERHEAD_BITS = _CRC_BITS
_TOTAL_OVERHEAD_BITS = _FRAMING_OVERHEAD_BITS + _INTEGRITY_OVERHEAD_BITS  # 72


class TextSteganographyCodec:
    """Compiles a configuration and runs the analyze/encode/decode workflow."""

    def __init__(self, config: CodecConfig) -> None:
        self.config = config

    @property
    def codec_id(self) -> str:
        return self.config.codec_id

    def analyze(self, text: str) -> CapacityReport:
        """Report how much information ``text`` can carry under this config."""
        plan = build_plan(self.config, text)

        groups: dict[int, List] = {}
        for planned in plan.planned_sites:
            groups.setdefault(planned.channel_index, []).append(planned)

        per_channel: List[ChannelCapacity] = []
        for channel_index, channel in enumerate(self.config.channels):
            channel_sites = groups.get(channel_index, [])
            raw_bits = sum(
                math.log2(planned.site.radix)
                for planned in channel_sites
                if planned.site.radix > 1
            )
            packed_bits = sum(planned.width for planned in channel_sites)
            per_channel.append(
                ChannelCapacity(
                    channel_id=channel.id,
                    sites=len(channel_sites),
                    raw_bits=raw_bits,
                    packed_bits=packed_bits,
                )
            )

        realizable = sum(capacity.packed_bits for capacity in per_channel)
        raw_total = sum(capacity.raw_bits for capacity in per_channel)

        # Error correction spends part of the realizable capacity on redundancy.
        # message_len is the whole message bits that survive after that spend.
        ecc = self.config.error_correction
        message_capacity_bits = ecc.message_len(realizable)
        ecc_overhead_bits = ecc.codeword_len(message_capacity_bits) - message_capacity_bits

        if message_capacity_bits < _TOTAL_OVERHEAD_BITS:
            usable_bytes = 0
            usable_bits = 0
            max_payloads = 0
        else:
            usable_bytes = (message_capacity_bits - _TOTAL_OVERHEAD_BITS) // 8
            usable_bits = usable_bytes * 8
            max_payloads = 1 << usable_bits

        return CapacityReport(
            total_sites=len(plan.planned_sites),
            per_channel=tuple(per_channel),
            raw_theoretical_bits=raw_total,
            realizable_packed_bits=realizable,
            framing_overhead_bits=_FRAMING_OVERHEAD_BITS,
            integrity_overhead_bits=_INTEGRITY_OVERHEAD_BITS,
            ecc_overhead_bits=ecc_overhead_bits,
            usable_payload_bits=usable_bits,
            usable_payload_bytes=usable_bytes,
            max_distinct_payloads=max_payloads,
            warnings=tuple(plan.warnings),
        )

    def encode(self, text: str, payload: bytes) -> EncodeResult:
        """Embed ``payload`` into ``text`` and return the stegotext."""
        plan = build_plan(self.config, text)
        widths = [planned.width for planned in plan.planned_sites]
        capacity = sum(widths)

        framed_bits = bytes_to_bits(frame(payload))
        codeword_bits = self.config.error_correction.encode_bits(framed_bits)
        need = len(codeword_bits)
        if need > capacity:
            raise CapacityError(
                f"payload of {len(payload)} bytes needs {need} bits once framed and "
                f"error-corrected, but this text offers {capacity} bits under codec "
                f"{self.codec_id}"
            )

        symbols = pack_bits_into_symbols(codeword_bits, widths)

        edits = []
        for planned, symbol in zip(plan.planned_sites, symbols):
            site = planned.site
            variant = site.variants[symbol] if symbol < site.radix else site.canonical
            if variant != text[site.start : site.end]:
                edits.append((site.start, site.end, variant))

        edits.sort(key=lambda edit: edit[0], reverse=True)
        out = text
        for start, end, replacement in edits:
            out = out[:start] + replacement + out[end:]

        return EncodeResult(
            text=out,
            codec_id=self.codec_id,
            payload_size=len(payload),
            sites_total=len(plan.planned_sites),
            sites_used=sites_consumed(widths, need),
            unused_capacity_bits=capacity - need,
            frame_version=FRAME_VERSION,
            warnings=tuple(plan.warnings),
        )

    def _observe_slots(self, text: str):
        """Read ``text`` into a codeword-bit observation vector.

        Returns (slots, observations, known_symbols, erased_symbols). Each slot
        is a bit (0/1) or ``None`` for an erased position. This is the common
        front end for both decoding and candidate identification.
        """
        slots: List[Optional[int]] = []
        observations: List[Observation] = []
        known = 0
        erasures = 0
        for channel in self.config.channels:
            for observation in channel.observe(text):
                observations.append(observation)
                width = site_bit_width(observation.radix)
                if width == 0:
                    continue
                if (
                    observation.state is ObservationState.KNOWN
                    and observation.symbol is not None
                    and observation.symbol < (1 << width)
                ):
                    slots.extend(int_to_bits(observation.symbol, width))
                    known += 1
                else:
                    slots.extend([None] * width)
                    erasures += 1
        return slots, observations, known, erasures

    def _expected_codeword_bits(self, payload: bytes) -> List[int]:
        """The codeword bits a given payload would encode to under this config."""
        return self.config.error_correction.encode_bits(bytes_to_bits(frame(payload)))

    def decode(self, text: str) -> DecodeResult:
        """Recover a payload from ``text``, or report why it could not."""
        slots, observations, known, erasures = self._observe_slots(text)

        common = dict(
            codec_id=self.codec_id,
            observed_sites=len(observations),
            known_symbols=known,
            erasures=erasures,
            observations=tuple(observations),
        )

        ecc = self.config.error_correction
        block = ecc.codeword_block_bits
        message_block = ecc.message_block_bits

        def decode_message_prefix(message_bits_wanted: int):
            """Decode the first ``message_bits_wanted`` message bits.

            Returns (bits, corrected, status) where status is one of "ok",
            "insufficient" (not enough observed codeword), or "uncorrectable"
            (a block could not be resolved).
            """
            num_blocks = message_bits_wanted // message_block
            codeword_needed = num_blocks * block
            if len(slots) < codeword_needed:
                return None, 0, "insufficient"
            bits: List[int] = []
            corrected_total = 0
            for index in range(num_blocks):
                block_obs = slots[index * block : (index + 1) * block]
                result = ecc.decode_block(block_obs)
                if result.bits is None:
                    return None, corrected_total, "uncorrectable"
                bits.extend(result.bits)
                corrected_total += result.corrected
            return bits, corrected_total, "ok"

        header_bits, _, header_status = decode_message_prefix(_HEADER_BITS)
        if header_status == "insufficient":
            return DecodeResult(
                status=DecodeStatus.INSUFFICIENT_EVIDENCE, payload=None, **common
            )
        if header_status == "uncorrectable":
            return DecodeResult(status=DecodeStatus.PARTIAL, payload=None, **common)

        header_bytes = bits_to_bytes(header_bits)
        if header_bytes[0:2] != MAGIC:
            return DecodeResult(status=DecodeStatus.INVALID, payload=None, **common)

        version = header_bytes[2]
        length = int.from_bytes(header_bytes[3:5], "big")
        total_message_bits = (OVERHEAD_BYTES + length) * 8

        frame_bits, corrected, frame_status = decode_message_prefix(total_message_bits)
        if frame_status == "insufficient":
            return DecodeResult(
                status=DecodeStatus.INSUFFICIENT_EVIDENCE,
                payload=None,
                frame_version=version,
                **common,
            )
        if frame_status == "uncorrectable":
            return DecodeResult(
                status=DecodeStatus.PARTIAL, payload=None, frame_version=version, **common
            )

        parsed = unframe(bits_to_bytes(frame_bits))
        if not parsed.integrity_valid:
            return DecodeResult(
                status=DecodeStatus.INVALID,
                payload=None,
                frame_version=parsed.version,
                integrity_valid=False,
                corrected_errors=corrected,
                **common,
            )

        return DecodeResult(
            status=DecodeStatus.SUCCESS,
            payload=parsed.payload,
            frame_version=parsed.version,
            integrity_valid=True,
            corrected_errors=corrected,
            **common,
        )

    def canonicalize(self, text: str) -> str:
        """Map every channel's variants back to their neutral form."""
        for channel in self.config.channels:
            text = channel.canonicalize(text)
        return text

    def identify(
        self, observed_text: str, candidates: Sequence[bytes]
    ) -> IdentificationResult:
        """Rank candidate payloads by consistency with a leaked copy.

        This compares the surviving evidence in ``observed_text`` against the
        codeword each candidate would have produced, and reports which remain
        consistent. It assumes a full-length text whose sites may have been
        normalized or flipped; it does not align arbitrary excerpts. It can
        narrow the source even when ``decode`` cannot recover a payload.
        """
        slots, _, _, _ = self._observe_slots(observed_text)
        candidate_bits = [
            (payload, self._expected_codeword_bits(payload)) for payload in candidates
        ]
        return identify_bits(slots, candidate_bits)

    def preflight(self, cover_text: str, payloads: Sequence[bytes]) -> FingerprintPreflight:
        """Check a set of fingerprints against one cover before distribution.

        Reports whether every payload fits, whether the resulting codewords are
        all distinct, and the smallest Hamming distance between any two of them
        (a rough measure of how much damage a copy can take before two sources
        become confusable).
        """
        capacity = sum(planned.width for planned in build_plan(self.config, cover_text).planned_sites)
        report = self.analyze(cover_text)

        expected = [self._expected_codeword_bits(payload) for payload in payloads]
        all_fit = all(len(bits) <= capacity for bits in expected)

        padded = [
            list(bits) + [0] * (capacity - len(bits))
            for bits in expected
            if len(bits) <= capacity
        ]
        all_distinct = all_fit and len({tuple(vector) for vector in padded}) == len(padded)

        return FingerprintPreflight(
            count=len(payloads),
            capacity_bits=capacity,
            usable_payload_bytes=report.usable_payload_bytes,
            all_fit=all_fit,
            all_distinct=all_distinct,
            min_pairwise_distance=min_pairwise_distance(padded),
        )

    def encode_many(self, cover_text: str, payloads: Sequence[bytes]) -> List[EncodeResult]:
        """Encode one stegotext per payload from the same cover.

        Consider calling :meth:`preflight` first to confirm the whole set fits
        and stays distinguishable. Each payload is encoded independently, so a
        payload that does not fit raises :class:`CapacityError`.
        """
        return [self.encode(cover_text, payload) for payload in payloads]
