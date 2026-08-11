"""Report unusual code points and normalization differences in text.

``inspect_text`` is a debugging and transport-diagnosis aid. It does not decode
anything; it points out the characters a person would want to look at when
asking "what did this transport do?" or "does this text carry a watermark?":
non-ASCII characters, invisible format controls, unusual spaces, mixed scripts,
and whether the text changes under Unicode normalization.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Coarse script ranges, enough to flag cross-script confusables in prose.
_SCRIPT_RANGES = (
    ("Latin", 0x0041, 0x024F),
    ("Greek", 0x0370, 0x03FF),
    ("Cyrillic", 0x0400, 0x04FF),
    ("Armenian", 0x0530, 0x058F),
    ("Hebrew", 0x0590, 0x05FF),
    ("Arabic", 0x0600, 0x06FF),
)


def _script_of(char: str) -> Optional[str]:
    code = ord(char)
    if code < 0x80 and char.isalpha():
        return "Latin"
    for name, low, high in _SCRIPT_RANGES:
        if low <= code <= high:
            return name
    return None


@dataclass(frozen=True)
class CodePointNote:
    """One notable character and why it was flagged."""

    index: int
    char: str
    codepoint: str
    name: str
    category: str
    note: str


@dataclass(frozen=True)
class InspectionReport:
    """The result of :func:`inspect_text`."""

    length: int
    notable: Tuple[CodePointNote, ...]
    scripts: Tuple[str, ...]
    nfc_differs: bool
    nfkc_differs: bool

    @property
    def mixed_scripts(self) -> bool:
        return len(self.scripts) > 1

    def summary(self) -> str:
        parts = [f"{self.length} chars"]
        if self.scripts:
            parts.append("scripts: " + ", ".join(self.scripts))
        if self.mixed_scripts:
            parts.append("MIXED SCRIPTS")
        if self.notable:
            parts.append(f"{len(self.notable)} notable code point(s)")
        if self.nfc_differs:
            parts.append("changes under NFC")
        if self.nfkc_differs:
            parts.append("changes under NFKC")
        return "; ".join(parts)


def _note_for(index: int, char: str) -> Optional[CodePointNote]:
    code = ord(char)
    category = unicodedata.category(char)
    name = unicodedata.name(char, "<unnamed>")
    codepoint = f"U+{code:04X}"

    reason: Optional[str] = None
    if category in {"Cf", "Cc", "Co", "Cn"}:
        reason = "invisible or control character"
    elif category == "Zs" and char != " ":
        reason = "non-standard space"
    elif code > 0x7F:
        reason = "non-ASCII character"

    if reason is None:
        return None
    return CodePointNote(
        index=index,
        char=char,
        codepoint=codepoint,
        name=name,
        category=category,
        note=reason,
    )


def inspect_text(text: str) -> InspectionReport:
    """Inspect ``text`` for notable code points and normalization differences."""
    notable: List[CodePointNote] = []
    scripts: List[str] = []
    seen_scripts = set()

    for index, char in enumerate(text):
        note = _note_for(index, char)
        if note is not None:
            notable.append(note)
        script = _script_of(char)
        if script is not None and script not in seen_scripts:
            seen_scripts.add(script)
            scripts.append(script)

    return InspectionReport(
        length=len(text),
        notable=tuple(notable),
        scripts=tuple(scripts),
        nfc_differs=unicodedata.normalize("NFC", text) != text,
        nfkc_differs=unicodedata.normalize("NFKC", text) != text,
    )
