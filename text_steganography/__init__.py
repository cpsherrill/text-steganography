"""text-steganography.

A modular Python library for lossless text steganography and fingerprinting.

The library embeds small hidden payloads into text by changing the text's
literal representation without intentionally changing what a human reader
understands. Hidden information lives in concrete representational choices:
one apostrophe code point rather than another, one Unicode space rather than
another, one canonical-equivalent Unicode sequence rather than another, and
so on.

This is a scaffold. The design is complete and lives in ``docs/DESIGN.md``;
implementation has not started. See the README for the planned phases.

Steganography is not encryption. This library hides the presence or
provenance of a payload. It does not make that payload confidential.
"""

__version__ = "0.0.0"

__all__ = ["__version__"]
