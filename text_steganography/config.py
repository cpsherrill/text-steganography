"""Versioned codec configuration.

The configuration is the complete, portable definition both the encoder and
the decoder need in order to agree about where the entropy lives and how to
interpret it. It serializes to a canonical JSON form and hashes to a stable
``codec_id`` that can be stored alongside a recipient database.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from .carriers import CarrierAdapter, PlainTextCarrier, build_carrier
from .carriers.plain_text import PLAIN_TEXT_ID
from .channels.base import BaseChannel, build_channel
from .ecc import ErrorCorrectingCodec, NoErrorCorrection, build_ecc
from .errors import ConfigError

SCHEMA_VERSION = 1


class PackingMode(str, Enum):
    """How framed bits are mapped onto sites of varying radix."""

    POWER_OF_TWO = "power_of_two"


@dataclass(frozen=True)
class RepertoirePolicy:
    """Which code points a configuration permits.

    Cross-script substitutions, bidirectional controls, and joiners require
    explicit permission. ``scripts`` describes the expected cover scripts;
    it is metadata, not a Unicode Script-property validator or input filter.
    """

    scripts: tuple[str, ...] = ("Latin",)
    allow_cross_script: bool = False
    allow_bidi_controls: bool = False
    allow_joiners: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scripts": list(self.scripts),
            "allow_cross_script": self.allow_cross_script,
            "allow_bidi_controls": self.allow_bidi_controls,
            "allow_joiners": self.allow_joiners,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepertoirePolicy":
        return cls(
            scripts=tuple(data.get("scripts", ("Latin",))),
            allow_cross_script=data.get("allow_cross_script", False),
            allow_bidi_controls=data.get("allow_bidi_controls", False),
            allow_joiners=data.get("allow_joiners", False),
        )


@dataclass(frozen=True)
class FramingConfig:
    """Which payload framing format to use."""

    format: str = "length_crc_v1"

    def to_dict(self) -> Dict[str, Any]:
        return {"format": self.format}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FramingConfig":
        return cls(format=str(data.get("format", "length_crc_v1")))


@dataclass
class CodecConfig:
    """The full, versioned codec definition shared by encode and decode."""

    channels: List[BaseChannel]
    repertoire: RepertoirePolicy = field(default_factory=RepertoirePolicy)
    packing: PackingMode = PackingMode.POWER_OF_TWO
    framing: FramingConfig = field(default_factory=FramingConfig)
    error_correction: ErrorCorrectingCodec = field(default_factory=NoErrorCorrection)
    carrier: CarrierAdapter = field(default_factory=PlainTextCarrier)
    schema_version: int = SCHEMA_VERSION

    def validate(self) -> None:
        """Reject declarations the installed implementation cannot honor."""
        if type(self.schema_version) is not int or self.schema_version != SCHEMA_VERSION:
            raise ConfigError(f"unsupported schema version: {self.schema_version!r}")
        if self.framing.format != "length_crc_v1":
            raise ConfigError(f"unsupported framing format: {self.framing.format!r}")
        if self.packing is not PackingMode.POWER_OF_TWO:
            raise ConfigError(f"unsupported packing mode: {self.packing!r}")
        self.error_correction.validate()
        if not self.channels:
            raise ConfigError("at least one channel is required")
        ids = [channel.id for channel in self.channels]
        if len(ids) != len(set(ids)):
            raise ConfigError("duplicate channels are not supported")
        for permission in ("allow_cross_script", "allow_joiners", "allow_bidi_controls"):
            if type(getattr(self.repertoire, permission)) is not bool:
                raise ConfigError(f"{permission} must be a boolean")
        for channel in self.channels:
            for permission in channel.required_permissions:
                if not getattr(self.repertoire, permission, False):
                    raise ConfigError(f"channel {channel.id!r} requires repertoire.{permission}=True")
        # Canonical decomposition changes letter identity and neighboring
        # character classes even when edit spans do not overlap.
        incompatible = {"punctuation.apostrophe", "homoglyph.cyrillic", "invisible.zero_width"}
        if "unicode.canonical" in ids and incompatible.intersection(ids):
            raise ConfigError("unicode.canonical cannot be combined with apostrophe, "
                              "homoglyph, or zero-width channels; site discovery is not stable")

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "channels": [
                {"id": channel.id, "version": channel.version, "params": channel.params()}
                for channel in self.channels
            ],
            "repertoire": self.repertoire.to_dict(),
            "packing": self.packing.value,
            "framing": self.framing.to_dict(),
        }
        # The identity codec is the default. Omitting it keeps a config that
        # uses no error correction serializing exactly as it did before the
        # ECC layer existed, so its codec_id and golden vectors stay stable.
        if self.error_correction.id != "ecc.none":
            data["error_correction"] = {
                "id": self.error_correction.id,
                "version": self.error_correction.version,
                "params": self.error_correction.params(),
            }
        # Multi-bit adapters explicitly freeze padding and block geometry.
        # Existing one-bit configurations retain their original codec ids.
        if self.error_correction.message_block_bits > 1:
            data["error_correction"]["block_layout"] = self.error_correction.block_layout()
        # The plain-text carrier is the default. Omitting it keeps a
        # configuration serializing exactly as it did before carriers existed.
        if self.carrier.id != PLAIN_TEXT_ID:
            data["carrier"] = {
                "id": self.carrier.id,
                "version": self.carrier.version,
                "params": self.carrier.params(),
            }
        return data

    def canonical_json(self) -> str:
        """A deterministic JSON serialization used for hashing and storage."""
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )

    @property
    def codec_id(self) -> str:
        """A stable 16-hex-character digest of the canonical configuration."""
        digest = hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
        return digest[:16]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodecConfig":
        packing = data.get("packing", PackingMode.POWER_OF_TWO.value)
        if packing != PackingMode.POWER_OF_TWO.value:
            raise ConfigError(f"unsupported packing mode: {packing!r}")
        channels = [
            build_channel(entry["id"], entry.get("version", ""), entry.get("params", {}))
            for entry in data["channels"]
        ]
        ecc_data = data.get("error_correction")
        if ecc_data:
            error_correction: ErrorCorrectingCodec = build_ecc(
                ecc_data["id"], ecc_data.get("version", ""), ecc_data.get("params", {})
            )
            layout = ecc_data.get("block_layout")
            if error_correction.message_block_bits > 1 and layout is None:
                raise ConfigError("multi-bit ECC configurations require an explicit block_layout")
            if layout is not None and layout != error_correction.block_layout():
                raise ConfigError("ECC block_layout does not match the installed adapter")
        else:
            error_correction = NoErrorCorrection()
        carrier_data = data.get("carrier")
        if carrier_data:
            carrier: CarrierAdapter = build_carrier(
                carrier_data["id"], carrier_data.get("version", ""), carrier_data.get("params", {})
            )
        else:
            carrier = PlainTextCarrier()
        config = cls(
            channels=channels,
            repertoire=RepertoirePolicy.from_dict(data.get("repertoire", {})),
            packing=PackingMode(packing),
            framing=FramingConfig.from_dict(data.get("framing", {})),
            error_correction=error_correction,
            carrier=carrier,
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )
        config.validate()
        return config
