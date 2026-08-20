"""Carrier adapters: where in a document it is safe to embed.

Importing this package registers the built-in carriers so a serialized
configuration can be rebuilt by id.
"""

from __future__ import annotations

from .base import (
    CarrierAdapter,
    build_carrier,
    get_carrier_class,
    register_carrier,
)
from .html import HtmlCarrier
from .markdown import MarkdownCarrier
from .plain_text import PLAIN_TEXT_ID, PlainTextCarrier
from .source_code import SourceCodeCarrier
from .spans import invert_spans, merge_spans, position_in_spans, site_in_spans

__all__ = [
    "CarrierAdapter",
    "register_carrier",
    "get_carrier_class",
    "build_carrier",
    "PlainTextCarrier",
    "PLAIN_TEXT_ID",
    "HtmlCarrier",
    "MarkdownCarrier",
    "SourceCodeCarrier",
    "invert_spans",
    "merge_spans",
    "position_in_spans",
    "site_in_spans",
]
