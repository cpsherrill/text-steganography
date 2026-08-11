"""Punctuation-variant channels.

These select among visually or typographically similar punctuation characters.
The first is the contraction apostrophe: a straight apostrophe (U+0027) or a
right single quotation mark (U+2019), chosen only when the apostrophe sits
between two letters, as in "it's" or "don't". Restricting to letter-flanked
apostrophes keeps the site rediscoverable and stays clear of opening and
closing quotation marks, which are a different typographic decision.

Unlike the space channel, this one is mildly perceptible: a careful reader may
notice a straight versus a curly apostrophe. It is included because it is
deterministic, rediscoverable, and useful for demonstrating multi-channel
composition, but its metadata says plainly that it is not invisible.
"""

from __future__ import annotations

from ..models import ChannelMetadata, Invariant, Risk
from ._single_char import SingleCharSubstitutionChannel
from .base import register_channel

_STRAIGHT = "\u0027"
_CURLY = "\u2019"


@register_channel
class ApostropheChannel(SingleCharSubstitutionChannel):
    id = "punctuation.apostrophe"
    version = "1"
    variants = (_STRAIGHT, _CURLY)
    canonical = _STRAIGHT

    def _eligible(self, text: str, i: int) -> bool:
        return text[i - 1].isalpha() and text[i + 1].isalpha()

    def metadata(self) -> ChannelMetadata:
        return ChannelMetadata(
            channel_id=self.id,
            version=self.version,
            invariant=Invariant.RENDERED_TEXT,
            risk=Risk.MEDIUM,
            description=(
                "Encodes one bit at each contraction apostrophe by choosing between a "
                "straight apostrophe and a right single quotation mark."
            ),
            warnings=(
                "The two forms are visually distinguishable to an attentive reader; "
                "this channel is not invisible.",
                "Smart-quote and autocorrect features routinely rewrite one form to "
                "the other, which erases the encoded bit.",
            ),
        )
