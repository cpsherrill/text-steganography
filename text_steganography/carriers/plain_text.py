"""The plain-text carrier: the whole document is safe.

This is the default. It treats the entire document as embeddable, which is the
Phase 1 behavior. Because it is the default, a configuration that uses it
serializes without a carrier entry at all, so earlier configurations and golden
vectors keep their exact codec_id.
"""

from __future__ import annotations

from typing import List

from .base import CarrierAdapter, Span, register_carrier

PLAIN_TEXT_ID = "carrier.plain_text"


@register_carrier
class PlainTextCarrier(CarrierAdapter):
    id = PLAIN_TEXT_ID
    version = "1"

    def safe_spans(self, document: str) -> List[Span]:
        return [(0, len(document))] if document else []
