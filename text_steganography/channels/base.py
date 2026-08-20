"""The channel interface and a small registry.

A channel is an independent, plugin-like component. Encoding and decoding both
enumerate a channel's sites in the same deterministic scan order, and the k-th
site found while encoding corresponds to the k-th site found while decoding.
Because of that ordinal correspondence a channel does not need to preserve
absolute character offsets between cover text and stegotext, which is what lets
variable-length variants work.

The registry lets a serialized configuration be reconstructed: each channel is
stored as its ``id``, ``version``, and parameter dict, and rebuilt through
:func:`build_channel`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Type

from ..errors import ConfigError
from ..models import ChannelMetadata, EmbeddingSite, Observation


@dataclass(frozen=True)
class ChannelContext:
    """Context passed to a channel during discovery and observation.

    A placeholder today. Carrier and repertoire information will hang off this
    as parser-aware carriers arrive, without changing the channel signature.
    """


class BaseChannel(ABC):
    """Abstract base every channel implements.

    Subclasses set the class attributes ``id`` and ``version`` and implement
    the four methods below. ``id`` must be stable across releases because it is
    part of the serialized configuration.
    """

    id: str = ""
    version: str = ""
    # Whether encoding preserves character offsets (variant lengths are equal).
    # False for channels that insert or change the length of a site, which the
    # offset-based excerpt alignment cannot follow.
    length_preserving: bool = True

    @abstractmethod
    def discover_sites(
        self, text: str, context: Optional[ChannelContext] = None
    ) -> List[EmbeddingSite]:
        """Return this channel's eligible sites in deterministic scan order."""

    @abstractmethod
    def observe(
        self, text: str, context: Optional[ChannelContext] = None
    ) -> List[Observation]:
        """Read the symbol at each site of ``text`` in the same scan order."""

    @abstractmethod
    def canonicalize(self, text: str) -> str:
        """Map every variant this channel emits back to its neutral form."""

    @abstractmethod
    def metadata(self) -> ChannelMetadata:
        """Return this channel's self-description."""

    def params(self) -> Dict[str, object]:
        """Serializable constructor parameters. Default: none."""
        return {}

    @classmethod
    def from_params(cls, params: Dict[str, object]) -> "BaseChannel":
        """Rebuild an instance from :meth:`params` output."""
        return cls(**params)  # type: ignore[arg-type]


_REGISTRY: Dict[str, Type[BaseChannel]] = {}


def register_channel(cls: Type[BaseChannel]) -> Type[BaseChannel]:
    """Class decorator that registers a channel by its ``id``."""
    if not cls.id:
        raise ConfigError(f"channel {cls.__name__} must define a non-empty id")
    existing = _REGISTRY.get(cls.id)
    if existing is not None and existing is not cls:
        raise ConfigError(f"channel id {cls.id!r} is already registered to {existing.__name__}")
    _REGISTRY[cls.id] = cls
    return cls


def get_channel_class(channel_id: str) -> Type[BaseChannel]:
    """Look up a registered channel class by id."""
    try:
        return _REGISTRY[channel_id]
    except KeyError:
        raise ConfigError(f"unknown channel id {channel_id!r}") from None


def build_channel(channel_id: str, version: str, params: Dict[str, object]) -> BaseChannel:
    """Reconstruct a channel from its serialized form."""
    cls = get_channel_class(channel_id)
    if version and cls.version and version != cls.version:
        raise ConfigError(
            f"channel {channel_id!r} version mismatch: config wants {version!r}, "
            f"installed is {cls.version!r}"
        )
    return cls.from_params(params)
