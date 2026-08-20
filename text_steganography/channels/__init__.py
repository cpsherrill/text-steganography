"""Steganographic channels.

A channel is one hiding mechanism. It finds its own eligible sites, offers the
literal variants available at each, recognizes those variants when decoding,
and canonicalizes them back to a neutral form. The core owns everything else:
payload bits, packing, framing, and identification.

Importing this package registers the built-in channels so a serialized
configuration can be reconstructed by id.
"""

from __future__ import annotations

from .base import (
    BaseChannel,
    ChannelContext,
    build_channel,
    get_channel_class,
    register_channel,
)
from .homoglyphs import CyrillicHomoglyphChannel
from .invisible import ZeroWidthChannel
from .punctuation import ApostropheChannel
from .unicode_normalization import CanonicalUnicodeChannel
from .whitespace import UnicodeSpaceChannel

__all__ = [
    "BaseChannel",
    "ChannelContext",
    "build_channel",
    "get_channel_class",
    "register_channel",
    "UnicodeSpaceChannel",
    "ApostropheChannel",
    "CyrillicHomoglyphChannel",
    "ZeroWidthChannel",
    "CanonicalUnicodeChannel",
]
