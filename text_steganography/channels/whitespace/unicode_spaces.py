"""The Unicode-space channel.

At each single inter-word space, this channel chooses between an ordinary space
(U+0020) and a no-break space (U+00A0). The two render at the same width in
almost every font, so the choice is invisible to a reader, and it carries one
bit per eligible space.

A site is a space variant with a non-whitespace character on each side. Runs of
two or more spaces and leading or trailing spaces are skipped, because they are
ambiguous under collapsing transports.

This is the conservative starter channel. It is not robust: many editors and
platforms normalize a no-break space back to a plain space, which silently
erases the bit. That is a property of the transport, not a defect here, and the
compatibility work in a later phase is where it gets measured.
"""

from __future__ import annotations

from ...models import ChannelMetadata, Invariant, Risk
from .._single_char import SingleCharSubstitutionChannel
from ..base import register_channel

_SPACE = "\u0020"
_NBSP = "\u00a0"


@register_channel
class UnicodeSpaceChannel(SingleCharSubstitutionChannel):
    id = "whitespace.unicode_space"
    version = "1"
    variants = (_SPACE, _NBSP)
    canonical = _SPACE

    def _eligible(self, text: str, i: int) -> bool:
        return not text[i - 1].isspace() and not text[i + 1].isspace()

    def metadata(self) -> ChannelMetadata:
        return ChannelMetadata(
            channel_id=self.id,
            version=self.version,
            invariant=Invariant.RENDERED_TEXT,
            risk=Risk.MEDIUM,
            description=(
                "Encodes one bit at each single inter-word space by choosing between "
                "a regular space and a no-break space."
            ),
            warnings=(
                "A no-break space prevents line wrapping at that position, which can "
                "change how a paragraph lays out.",
                "Many editors, chat platforms, and normalizers convert no-break spaces "
                "back to regular spaces, which erases the encoded bit.",
            ),
        )
