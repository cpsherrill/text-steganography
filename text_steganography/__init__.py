"""text-steganography.

A modular Python library for lossless text steganography and fingerprinting.

The library embeds small hidden payloads into text by changing the text's
literal representation without intentionally changing what a human reader
understands. Hidden information lives in concrete representational choices:
one apostrophe code point rather than another, one Unicode space rather than
another, one canonical-equivalent Unicode sequence rather than another, and
so on.

Steganography is not encryption. This library hides the presence or
provenance of a payload. It does not make that payload confidential.
"""

from __future__ import annotations

from .channels import (
    ApostropheChannel,
    BaseChannel,
    ChannelContext,
    UnicodeSpaceChannel,
    register_channel,
)
from .codec import TextSteganographyCodec
from .inspect import InspectionReport, inspect_text
from .config import CodecConfig, FramingConfig, PackingMode, RepertoirePolicy
from .errors import (
    CapacityError,
    ConfigError,
    ConflictError,
    DecodeError,
    FramingError,
    TextSteganographyError,
)
from .models import (
    CapacityReport,
    ChannelCapacity,
    ChannelMetadata,
    DecodeResult,
    DecodeStatus,
    EmbeddingSite,
    EncodeResult,
    Invariant,
    Observation,
    ObservationState,
    Risk,
)

__version__ = "0.0.0"

__all__ = [
    "__version__",
    # codec
    "TextSteganographyCodec",
    # configuration
    "CodecConfig",
    "RepertoirePolicy",
    "PackingMode",
    "FramingConfig",
    # channels
    "BaseChannel",
    "ChannelContext",
    "register_channel",
    "UnicodeSpaceChannel",
    "ApostropheChannel",
    # inspection
    "inspect_text",
    "InspectionReport",
    # models
    "EmbeddingSite",
    "Observation",
    "ObservationState",
    "ChannelMetadata",
    "ChannelCapacity",
    "CapacityReport",
    "EncodeResult",
    "DecodeResult",
    "DecodeStatus",
    "Invariant",
    "Risk",
    # errors
    "TextSteganographyError",
    "ConfigError",
    "CapacityError",
    "ConflictError",
    "FramingError",
    "DecodeError",
]
