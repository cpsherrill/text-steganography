"""Exception hierarchy for the library.

Every error raised on purpose by this package derives from
:class:`TextSteganographyError`, so callers can catch the whole family with a
single ``except``.
"""

from __future__ import annotations


class TextSteganographyError(Exception):
    """Base class for every error this library raises deliberately."""


class ConfigError(TextSteganographyError):
    """The codec configuration is invalid or cannot be reconstructed."""


class CapacityError(TextSteganographyError):
    """A payload does not fit in the capacity a text offers under a config."""


class ConflictError(TextSteganographyError):
    """Two channels claim overlapping spans in the same text."""


class FramingError(TextSteganographyError):
    """A byte buffer is not a valid payload frame."""


class DecodeError(TextSteganographyError):
    """Decoding failed in a way the caller asked to be treated as fatal."""
