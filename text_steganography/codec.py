"""The public codec: analyze, encode, decode, canonicalize.

A :class:`TextSteganographyCodec` wraps a configuration and exposes the whole
Phase 1 workflow. Encoding never silently truncates: a payload that does not
fit raises :class:`CapacityError`. Decoding never silently lies: a frame whose
checksum fails comes back as ``INVALID`` with no payload rather than as bytes.
"""

from __future__ import annotations

import math
from typing import List, Optional

from .config import CodecConfig
from .core.bits import bits_to_bytes, bytes_to_bits, int_to_bits
from .core.planner import build_plan
from .core.symbol_packing import pack_bits_into_symbols, site_bit_width, sites_consumed
from .errors import CapacityError
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

        if realizable < _TOTAL_OVERHEAD_BITS:
            usable_bytes = 0
            usable_bits = 0
            max_payloads = 0
        else:
            usable_bytes = (realizable - _TOTAL_OVERHEAD_BITS) // 8
            usable_bits = usable_bytes * 8
            max_payloads = 1 << usable_bits

        return CapacityReport(
            total_sites=len(plan.planned_sites),
            per_channel=tuple(per_channel),
            raw_theoretical_bits=raw_total,
            realizable_packed_bits=realizable,
            framing_overhead_bits=_FRAMING_OVERHEAD_BITS,
            integrity_overhead_bits=_INTEGRITY_OVERHEAD_BITS,
            ecc_overhead_bits=0,
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
        need = len(framed_bits)
        if need > capacity:
            raise CapacityError(
                f"payload of {len(payload)} bytes needs {need} bits once framed, but "
                f"this text offers {capacity} bits under codec {self.codec_id}"
            )

        symbols = pack_bits_into_symbols(framed_bits, widths)

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

    def decode(self, text: str) -> DecodeResult:
        """Recover a payload from ``text``, or report why it could not."""
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

        common = dict(
            codec_id=self.codec_id,
            observed_sites=len(observations),
            known_symbols=known,
            erasures=erasures,
            observations=tuple(observations),
        )

        if len(slots) < _HEADER_BITS:
            return DecodeResult(
                status=DecodeStatus.INSUFFICIENT_EVIDENCE, payload=None, **common
            )

        header_slots = slots[:_HEADER_BITS]
        if any(slot is None for slot in header_slots):
            return DecodeResult(status=DecodeStatus.PARTIAL, payload=None, **common)

        header_bytes = bits_to_bytes([int(slot) for slot in header_slots])
        if header_bytes[0:2] != MAGIC:
            return DecodeResult(status=DecodeStatus.INVALID, payload=None, **common)

        version = header_bytes[2]
        length = int.from_bytes(header_bytes[3:5], "big")
        total_bits = (OVERHEAD_BYTES + length) * 8

        if len(slots) < total_bits:
            return DecodeResult(
                status=DecodeStatus.INSUFFICIENT_EVIDENCE,
                payload=None,
                frame_version=version,
                **common,
            )

        frame_slots = slots[:total_bits]
        if any(slot is None for slot in frame_slots):
            return DecodeResult(
                status=DecodeStatus.PARTIAL, payload=None, frame_version=version, **common
            )

        parsed = unframe(bits_to_bytes([int(slot) for slot in frame_slots]))
        if not parsed.integrity_valid:
            return DecodeResult(
                status=DecodeStatus.INVALID,
                payload=None,
                frame_version=parsed.version,
                integrity_valid=False,
                **common,
            )

        return DecodeResult(
            status=DecodeStatus.SUCCESS,
            payload=parsed.payload,
            frame_version=parsed.version,
            integrity_valid=True,
            **common,
        )

    def canonicalize(self, text: str) -> str:
        """Map every channel's variants back to their neutral form."""
        for channel in self.config.channels:
            text = channel.canonicalize(text)
        return text
