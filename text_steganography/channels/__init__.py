"""Steganographic channels.

A channel is one hiding mechanism. It finds its own eligible sites, offers the
literal variants available at each, recognizes those variants when decoding,
and canonicalizes them back to a neutral form. The core owns everything else:
payload bits, packing, framing, and identification.
"""

from __future__ import annotations

from .base import (
    BaseChannel,
    ChannelContext,
    build_channel,
    get_channel_class,
    register_channel,
)

__all__ = [
    "BaseChannel",
    "ChannelContext",
    "build_channel",
    "get_channel_class",
    "register_channel",
]
