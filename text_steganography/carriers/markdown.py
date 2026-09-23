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

This is a conservative subset scanner, not a full CommonMark renderer. HTML
regions and character references use the shared HTML tokenizer. Supported
fixtures are tested for protected-region preservation; arbitrary Markdown
extensions are not supported.
"""

from __future__ import annotations

import re
from typing import List, Set, Tuple

from .base import CarrierAdapter, Span, register_carrier
from .spans import invert_spans
from .html import HtmlCarrier

_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_REFDEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:")
_INDENT_CODE_RE = re.compile(r"^\s{4,}\S")
_BLOCK_PREFIX_RE = re.compile(r"^\s*(?:(?:#{1,6}|>|[-+*]|\d{1,9}[.)])\s+)*")


@register_carrier
class MarkdownCarrier(CarrierAdapter):
    id = "carrier.markdown"
    version = "2"

    def safe_spans(self, document: str) -> List[Span]:
        n = len(document)
        lines = self._line_ranges(document)
        fenced_lines, fenced_ranges = self._fenced(document, lines)

        unsafe: List[Span] = list(fenced_ranges)
        # Reuse HTML's tokenizer to protect entities, quoted attributes,
        # comments, declarations, and raw script/style content in Markdown.
        unsafe.extend(invert_spans(HtmlCarrier().safe_spans(document), n))
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
            if char == "\\":
                out.append((i, min(i + 2, n)))
                i += 2
                continue
            if char == "[":
                # Protect labels too: shortcut/collapsed/reference links use
                # their spelling to select a destination in another line.
                j, depth = i + 1, 1
                while j < n and depth:
                    if document[j] == "\\":
                        j += 2
                        continue
                    if document[j] == "[":
                        depth += 1
                    elif document[j] == "]":
                        depth -= 1
                    j += 1
                out.append((i, j))
                i = j - 1 if depth == 0 else j
                continue
            if char == "`":
                run = 1
                while i + run < n and document[i + run] == "`":
                    run += 1
                marker = "`" * run
                closing = re.search(r"(?<!`)`{" + str(run) + r"}(?!`)", document[i + run:])
                end = i + run + closing.end() if closing else n
                out.append((i, end))
                i = end
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
                j, depth, quote = i + 2, 1, None
                while j < n and depth:
                    token = document[j]
                    if token == "\\":
                        j += 2
                        continue
                    if quote:
                        if token == quote:
                            quote = None
                    elif token in ("'", '"'):
                        quote = token
                    elif token == "(":
                        depth += 1
                    elif token == ")":
                        depth -= 1
                    j += 1
                out.append((i + 1, j))
                i = j
                continue
            i += 1
        return out
