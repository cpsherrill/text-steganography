"""The carrier-adapter interface and registry.

A carrier adapter answers one question about a document: which character ranges
are safe to embed in. It parses the carrier's structure and returns the spans
of ordinary text, keeping channels out of tags, attributes, URLs, code, and
other places where a substitution would change meaning or break parsing.

Adapters and channels stay separate on purpose. The adapter says *where* text
may be touched; the channel says *how* a site there encodes a symbol. Because
the safe spans shipped so far are literal substrings of the document, no
coordinate translation is needed: an edit inside a safe span is just an edit to
the document.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Type

from ..errors import ConfigError

Span = Tuple[int, int]


class CarrierAdapter(ABC):
    """Base class for carrier adapters."""

    id: str = ""
    version: str = ""

    @abstractmethod
    def safe_spans(self, document: str) -> List[Span]:
        """Return the character ranges of ``document`` safe to embed in."""

    def params(self) -> Dict[str, object]:
        return {}

    @classmethod
    def from_params(cls, params: Dict[str, object]) -> "CarrierAdapter":
        return cls(**params)  # type: ignore[arg-type]


_REGISTRY: Dict[str, Type[CarrierAdapter]] = {}


def register_carrier(cls: Type[CarrierAdapter]) -> Type[CarrierAdapter]:
    if not cls.id:
        raise ConfigError(f"carrier {cls.__name__} must define a non-empty id")
    existing = _REGISTRY.get(cls.id)
    if existing is not None and existing is not cls:
        raise ConfigError(f"carrier id {cls.id!r} is already registered to {existing.__name__}")
    _REGISTRY[cls.id] = cls
    return cls


def get_carrier_class(carrier_id: str) -> Type[CarrierAdapter]:
    try:
        return _REGISTRY[carrier_id]
    except KeyError:
        raise ConfigError(f"unknown carrier id {carrier_id!r}") from None


def build_carrier(carrier_id: str, version: str, params: Dict[str, object]) -> CarrierAdapter:
    cls = get_carrier_class(carrier_id)
    if version and cls.version and version != cls.version:
        raise ConfigError(
            f"carrier {carrier_id!r} version mismatch: config wants {version!r}, "
            f"installed is {cls.version!r}"
        )
    return cls.from_params(params)
