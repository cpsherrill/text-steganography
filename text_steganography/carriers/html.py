"""HTML text-node spans, using the standard library's quote-aware tokenizer.

Tags, attributes, references, comments, declarations, and script/style content
are excluded. Unfinished markup is excluded rather than reinterpreted as prose.
This is not a browser DOM parser and makes no rendering-equivalence promise.
"""
from __future__ import annotations

from html.parser import HTMLParser
from typing import List

from .base import CarrierAdapter, Span, register_carrier
from ..errors import ConfigError


class _TextSpans(HTMLParser):
    def __init__(self, document: str):
        super().__init__(convert_charrefs=False)
        self.lines = [0] + [i + 1 for i, char in enumerate(document) if char == '\n']
        self.spans: List[Span] = []
        self.raw_tag = None
        self.uncertain = False

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}:
            self.raw_tag = tag

    def handle_startendtag(self, tag, attrs):
        # HTML does not treat a self-closing script/style start tag as an end.
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == self.raw_tag:
            self.raw_tag = None

    def handle_data(self, data):
        if self.raw_tag or self.uncertain:
            return
        # HTMLParser can emit unfinished markup as data on close(). Retain
        # only the known prose preceding it, and quarantine the remaining text.
        safe = data.split('<', 1)[0]
        if '<' in data:
            self.uncertain = True
        if safe:
            line, column = self.getpos()
            start = self.lines[line - 1] + column
            self.spans.append((start, start + len(safe)))


@register_carrier
class HtmlCarrier(CarrierAdapter):
    id = 'carrier.html'
    version = '2'

    def safe_spans(self, document: str) -> List[Span]:
        parser = _TextSpans(document)
        try:
            parser.feed(document)
            parser.close()
        except (ValueError, AssertionError) as error:
            raise ConfigError('unsupported or malformed HTML markup') from error
        return parser.spans
