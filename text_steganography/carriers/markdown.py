"""A Markdown carrier.

Safe regions are the prose. Excluded, because a substitution there would change
structure or meaning:

- fenced code blocks (``` and ~~~), whole block;
- inline code spans (backtick runs);
- link and image destinations and titles, the ``(...)`` after a ``]``;
- autolinks and raw HTML tags, anything in ``<...>``;
- reference link definitions (``[label]: url``);
- the block prefix of each line (indentation, heading ``#`` markers, list
  bullets, blockquote ``>``) and its trailing space, since turning that space
  into a no-break space would stop it from being a heading or a list;
- lines indented four or more spaces, which Markdown reads as code.

This is a conservative scanner, not a CommonMark parser. When unsure it marks a
region unsafe, which costs capacity but never corrupts the document. Embedding
is length-preserving, so the same scan yields the same spans for cover and
stegotext.
"""

from __future__ import annotations

import re
from typing import List, Set, Tuple

from .base import CarrierAdapter, Span, register_carrier
from .spans import invert_spans

_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_REFDEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:")
_INDENT_CODE_RE = re.compile(r"^\s{4,}\S")
_BLOCK_PREFIX_RE = re.compile(r"^\s*(?:(?:#{1,6}|>|[-+*]|\d{1,9}[.)])\s+)*")


@register_carrier
class MarkdownCarrier(CarrierAdapter):
    id = "carrier.markdown"
    version = "1"

    def safe_spans(self, document: str) -> List[Span]:
        n = len(document)
        lines = self._line_ranges(document)
        fenced_lines, fenced_ranges = self._fenced(document, lines)

        unsafe: List[Span] = list(fenced_ranges)
        for index, (line_start, line_end) in enumerate(lines):
            if index in fenced_lines:
                continue
            line = document[line_start:line_end]
            if _REFDEF_RE.match(line) or _INDENT_CODE_RE.match(line):
                unsafe.append((line_start, line_end))
                continue
            prefix = _BLOCK_PREFIX_RE.match(line)
            if prefix and prefix.end() > 0:
                unsafe.append((line_start, line_start + prefix.end()))

        unsafe.extend(self._inline_unsafe(document, fenced_ranges))
        return invert_spans(unsafe, n)

    @staticmethod
    def _line_ranges(document: str) -> List[Span]:
        ranges: List[Span] = []
        start = 0
        for i, char in enumerate(document):
            if char == "\n":
                ranges.append((start, i + 1))
                start = i + 1
        if start < len(document):
            ranges.append((start, len(document)))
        return ranges

    def _fenced(self, document: str, lines: List[Span]) -> Tuple[Set[int], List[Span]]:
        inside: Set[int] = set()
        ranges: List[Span] = []
        open_fence = None  # (char, length)
        for index, (line_start, line_end) in enumerate(lines):
            line = document[line_start:line_end]
            match = _FENCE_RE.match(line)
            if open_fence is None:
                if match:
                    marker = match.group(1)
                    open_fence = (marker[0], len(marker))
                    inside.add(index)
                    ranges.append((line_start, line_end))
            else:
                inside.add(index)
                ranges.append((line_start, line_end))
                char, length = open_fence
                if re.match(r"^\s{0,3}" + re.escape(char) + "{" + str(length) + r",}\s*$", line):
                    open_fence = None
        return inside, ranges

    @staticmethod
    def _inline_unsafe(document: str, fenced_ranges: List[Span]) -> List[Span]:
        n = len(document)
        out: List[Span] = []

        def fence_end(position: int):
            for start, end in fenced_ranges:
                if start <= position < end:
                    return end
            return None

        i = 0
        while i < n:
            skip = fence_end(i)
            if skip is not None:
                i = skip
                continue
            char = document[i]
            if char == "`":
                run = 1
                while i + run < n and document[i + run] == "`":
                    run += 1
                marker = "`" * run
                close = document.find(marker, i + run)
                if close != -1:
                    out.append((i, close + run))
                    i = close + run
                    continue
                i += run
                continue
            if char == "<":
                close = document.find(">", i + 1)
                if close != -1:
                    out.append((i, close + 1))
                    i = close + 1
                    continue
                i += 1
                continue
            if char == "]" and i + 1 < n and document[i + 1] == "(":
                close = document.find(")", i + 2)
                if close != -1:
                    out.append((i + 1, close + 1))
                    i = close + 1
                    continue
                i += 1
                continue
            i += 1
        return out
