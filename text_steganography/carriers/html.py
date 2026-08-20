"""An HTML carrier.

Safe regions are the text nodes: the characters that sit between tags and are
not part of a character entity. Everything structural is off limits: tags
themselves (so attributes, tag names, and URLs in ``href``/``src`` are never
touched), the contents of ``<script>`` and ``<style>`` elements, and entity
references such as ``&amp;`` (embedding inside one would change the character
it stands for).

This is a conservative scanner, not a full HTML5 parser. When it cannot be sure
a region is plain text it leaves the region alone, which costs capacity but
never corrupts the document. Because encoding here is length-preserving, the
same scan yields the same safe spans for the cover and the stegotext.
"""

from __future__ import annotations

from typing import List

from .base import CarrierAdapter, Span, register_carrier
from .spans import invert_spans

_RAW_TEXT_ELEMENTS = {"script", "style"}


def _tag_name(tag: str) -> str:
    body = tag[1:-1].strip()
    if body.startswith("/"):
        body = body[1:].strip()
    end = 0
    while end < len(body) and (body[end].isalnum() or body[end] == "-"):
        end += 1
    return body[:end].lower()


def _looks_like_entity(text: str) -> bool:
    # &name; or &#123; or &#x1F;  (short and well-formed)
    if len(text) < 3 or text[0] != "&" or text[-1] != ";":
        return False
    inner = text[1:-1]
    if inner.startswith("#"):
        inner = inner[1:]
        if inner[:1] in ("x", "X"):
            inner = inner[1:]
        return inner.isalnum() and len(inner) > 0
    return inner.isalnum()


@register_carrier
class HtmlCarrier(CarrierAdapter):
    id = "carrier.html"
    version = "1"

    def safe_spans(self, document: str) -> List[Span]:
        unsafe: List[Span] = []
        n = len(document)
        i = 0
        while i < n:
            char = document[i]
            if char == "<":
                close = document.find(">", i + 1)
                if close == -1:
                    unsafe.append((i, n))  # an unterminated tag; treat the rest as unsafe
                    break
                tag = document[i : close + 1]
                name = _tag_name(tag)
                if name in _RAW_TEXT_ELEMENTS and not tag.startswith("</"):
                    end = self._raw_element_end(document, close + 1, name)
                    unsafe.append((i, end))
                    i = end
                else:
                    unsafe.append((i, close + 1))
                    i = close + 1
            elif char == "&":
                semicolon = document.find(";", i + 1)
                if semicolon != -1 and _looks_like_entity(document[i : semicolon + 1]):
                    unsafe.append((i, semicolon + 1))
                    i = semicolon + 1
                else:
                    i += 1
            else:
                i += 1
        return invert_spans(unsafe, n)

    @staticmethod
    def _raw_element_end(document: str, start: int, name: str) -> int:
        lowered = document.lower()
        closing = lowered.find("</" + name, start)
        if closing == -1:
            return len(document)
        gt = document.find(">", closing)
        return gt + 1 if gt != -1 else len(document)
